"""Authenticated Desktop adapter for tenant-bound company Knowledge ingestion.

This module extends the existing Desktop identity/source-media HTTP boundary; it does
not create another identity, execution, or memory authority. Uploaded document bytes
are validated and extracted by ``company_knowledge_ingestion`` and persisted through
the canonical ``DurableKnowledgeRuntime``. Raw source-byte retention is intentionally
not claimed here; that remains the responsibility of the canonical governed Files /
object-storage integration.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import threading
from http import HTTPStatus
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from services import desktop_identity_server_core as _identity_core
from services.company_knowledge_ingestion import (
    CompanyKnowledgeIngestionError,
    DurableCompanyKnowledgeIngestor,
)
from services.desktop_oidc import DesktopIdentityError, DesktopOIDCService
from services.execution_coordinator import ExecutionCoordinator, ExecutionCoordinatorError
from services.knowledge_rag import KnowledgeRAGError
from services.knowledge_runtime import (
    DurableKnowledgeRuntime,
    KnowledgeRuntimeConfig,
    KnowledgeRuntimeError,
    KnowledgeRuntimePolicy,
)
from services.reference_assets import ReferenceAssetStore
from services.source_media import SourceMediaStore
from services.source_media_desktop import (
    SourceMediaDesktopIdentityHTTPServer,
    SourceMediaDesktopIdentityRequestHandler,
)

_COMPANY_UPLOAD_MAX_BYTES = 25 * 1024 * 1024
# Base64 expands by roughly 4/3. Keep a bounded JSON envelope margin.
_COMPANY_UPLOAD_BODY_BYTES = ((_COMPANY_UPLOAD_MAX_BYTES + 2) // 3) * 4 + 1_048_576
_COMPANY_PROJECT_ID = "company-profile"
_COMPANY_SERVICE_PRINCIPAL_ID = "ilaios.service.company-knowledge.v1"
_COMPANY_CLASSIFICATIONS = frozenset({"internal"})
_COMPANY_PURPOSES = frozenset({"company-context"})
_COMPANY_RESIDENCIES = frozenset({"global"})
_COMPANY_MIME_TYPES = frozenset(
    {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }
)


class TenantCompanyKnowledgeRegistry:
    """Routes authenticated tenant scope into canonical durable Knowledge runtimes.

    The registry owns no semantic memory state. Each runtime retains the existing
    immutable server-side tenant/project binding and integrity-chained event log.
    The company project namespace is server-owned so callers cannot select another
    project boundary through the upload API.
    """

    def __init__(self, root: Path) -> None:
        self._root = root
        self._lock = threading.RLock()
        self._runtimes: dict[str, DurableKnowledgeRuntime] = {}
        root.mkdir(parents=True, exist_ok=True)

    def runtime_for(self, tenant_id: str) -> DurableKnowledgeRuntime:
        if not tenant_id or tenant_id != tenant_id.strip():
            raise KnowledgeRuntimeError("authenticated tenant_id is invalid")
        with self._lock:
            existing = self._runtimes.get(tenant_id)
            if existing is not None:
                return existing
            tenant_key = hashlib.sha256(tenant_id.encode("utf-8")).hexdigest()
            tenant_root = self._root / tenant_key
            runtime = DurableKnowledgeRuntime(
                KnowledgeRuntimeConfig(
                    metadata_database=tenant_root / "knowledge.sqlite3",
                    vector_database=tenant_root / "vectors.sqlite3",
                    policy=KnowledgeRuntimePolicy(
                        principal_id=_COMPANY_SERVICE_PRINCIPAL_ID,
                        tenant_id=tenant_id,
                        project_id=_COMPANY_PROJECT_ID,
                        allowed_classifications=_COMPANY_CLASSIFICATIONS,
                        allowed_purposes=_COMPANY_PURPOSES,
                        allowed_residencies=_COMPANY_RESIDENCIES,
                    ),
                )
            )
            self._runtimes[tenant_id] = runtime
            return runtime

    def ingest(
        self,
        *,
        tenant_id: str,
        filename: str,
        mime_type: str,
        content: bytes,
        content_sha256: str,
    ) -> dict[str, object]:
        if mime_type not in _COMPANY_MIME_TYPES:
            raise CompanyKnowledgeIngestionError("unsupported company-document MIME type")
        runtime = self.runtime_for(tenant_id)
        source_id = _source_id(filename)
        locator = f"desktop-company-upload://sha256/{content_sha256}/{filename}"
        ingestor = DurableCompanyKnowledgeIngestor(runtime)
        try:
            return ingestor.ingest(
                source_id,
                filename=filename,
                mime_type=mime_type,
                content=content,
                locator=locator,
                trusted=False,
                classifications=_COMPANY_CLASSIFICATIONS,
                purposes=_COMPANY_PURPOSES,
                residency="global",
            )
        except KnowledgeRAGError as error:
            if str(error) != "source_id already exists":
                raise
            extracted = ingestor.extract(
                filename=filename,
                mime_type=mime_type,
                content=content,
            )
            return runtime.update_source(source_id=source_id, content=extracted.text)


class CompanyKnowledgeDesktopIdentityHTTPServer(SourceMediaDesktopIdentityHTTPServer):
    """Existing Desktop server plus bounded company-document Knowledge ingestion."""

    def __init__(
        self,
        server_address: tuple[str, int],
        *,
        bearer_token: str,
        identity: DesktopOIDCService | None,
        coordinator: ExecutionCoordinator,
        reference_assets: ReferenceAssetStore | None = None,
        source_media: SourceMediaStore,
        company_knowledge: TenantCompanyKnowledgeRegistry,
    ) -> None:
        super().__init__(
            server_address,
            bearer_token=bearer_token,
            identity=identity,
            coordinator=coordinator,
            reference_assets=reference_assets,
            source_media=source_media,
        )
        self.company_knowledge = company_knowledge
        self.RequestHandlerClass = CompanyKnowledgeDesktopIdentityRequestHandler


class CompanyKnowledgeDesktopIdentityRequestHandler(
    SourceMediaDesktopIdentityRequestHandler
):
    server: CompanyKnowledgeDesktopIdentityHTTPServer

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path != "/v1/company-knowledge":
            super().do_POST()
            return
        try:
            self._authenticate_transport()
            body = self._read_json(max_bytes=_COMPANY_UPLOAD_BODY_BYTES)
            self._upload_company_knowledge(body)
        except DesktopIdentityError as error:
            self._send_error(HTTPStatus.UNAUTHORIZED, str(error))
        except ExecutionCoordinatorError as error:
            self._send_error(HTTPStatus.CONFLICT, str(error))
        except (
            CompanyKnowledgeIngestionError,
            KnowledgeRAGError,
            KnowledgeRuntimeError,
            ValueError,
            TypeError,
            json.JSONDecodeError,
        ) as error:
            self._send_error(HTTPStatus.BAD_REQUEST, str(error))

    def _upload_company_knowledge(self, body: dict[str, Any]) -> None:
        session = self._authenticated_session()
        filename = _identity_core._required_string(body, "filename")
        mime_type = _identity_core._required_string(body, "mime_type")
        supplied_sha256 = _identity_core._required_string(body, "sha256").lower()
        if len(supplied_sha256) != 64 or any(
            character not in "0123456789abcdef" for character in supplied_sha256
        ):
            raise ValueError("company document sha256 is invalid")
        encoded = _identity_core._required_string(body, "content_base64")
        try:
            content = base64.b64decode(encoded, validate=True)
        except (binascii.Error, ValueError) as error:
            raise ValueError("company document base64 payload is invalid") from error
        if not content or len(content) > _COMPANY_UPLOAD_MAX_BYTES:
            raise ValueError("company document is empty or exceeds the 25 MiB limit")
        digest = hashlib.sha256(content).hexdigest()
        if not hmac.compare_digest(digest, supplied_sha256):
            raise ValueError("company document sha256 does not match uploaded bytes")
        source = self.server.company_knowledge.ingest(
            tenant_id=session.tenant_id,
            filename=filename,
            mime_type=mime_type,
            content=content,
            content_sha256=digest,
        )
        self._send_json(
            HTTPStatus.CREATED,
            {
                "source_id": source["source_id"],
                "latest_version": source["latest_version"],
                "state": source["state"],
                "filename": filename,
                "mime_type": mime_type,
                "sha256": digest,
                "knowledge_scope": "company",
            },
        )


def _source_id(filename: str) -> str:
    normalized = filename.strip().casefold()
    if not normalized or len(filename) > 180 or "/" in filename or "\\" in filename:
        raise CompanyKnowledgeIngestionError("unsafe filename")
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:32]
    return f"company-file-{digest}"


__all__ = [
    "CompanyKnowledgeDesktopIdentityHTTPServer",
    "CompanyKnowledgeDesktopIdentityRequestHandler",
    "TenantCompanyKnowledgeRegistry",
]
