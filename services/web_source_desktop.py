"""Authenticated Desktop boundary for existing Web source ZIP admission.

The existing source-media Desktop server remains the composition root for auth,
reference images, source video and governed execution. This adapter adds one
Web-source input surface and delegates every unrelated request unchanged.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import secrets
from datetime import datetime, timezone
from http import HTTPStatus
from typing import Any
from urllib.parse import urlparse

from services import desktop_identity_server_core as _identity_core
from services.desktop_identity_server import _reference_factory_count
from services.desktop_oidc import DesktopIdentityError, DesktopOIDCService
from services.execution_coordinator import ExecutionCoordinator, ExecutionCoordinatorError
from services.reference_assets import ReferenceAssetStore
from services.source_media import SourceMediaStore
from services.source_media_desktop import (
    SourceMediaDesktopIdentityHTTPServer,
    SourceMediaDesktopIdentityRequestHandler,
)
from services.web_source_admission import (
    WebSourceAdmissionError,
    WebSourceAdmissionStore,
)
from services.web_source_ingestion import MAX_ARCHIVE_BYTES

_WEB_SOURCE_UPLOAD_BODY_BYTES = ((MAX_ARCHIVE_BYTES + 2) // 3) * 4 + 1_048_576
_MAX_WEB_SOURCE_FILENAME_CHARS = 180


class WebSourceDesktopIdentityHTTPServer(SourceMediaDesktopIdentityHTTPServer):
    """Canonical Desktop identity/source server plus existing Web source input."""

    def __init__(
        self,
        server_address: tuple[str, int],
        *,
        bearer_token: str,
        identity: DesktopOIDCService | None,
        coordinator: ExecutionCoordinator,
        reference_assets: ReferenceAssetStore | None = None,
        source_media: SourceMediaStore,
        web_source: WebSourceAdmissionStore,
    ) -> None:
        super().__init__(
            server_address,
            bearer_token=bearer_token,
            identity=identity,
            coordinator=coordinator,
            reference_assets=reference_assets,
            source_media=source_media,
        )
        self.web_source = web_source
        self.RequestHandlerClass = WebSourceDesktopIdentityRequestHandler


class WebSourceDesktopIdentityRequestHandler(SourceMediaDesktopIdentityRequestHandler):
    server: WebSourceDesktopIdentityHTTPServer

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path not in {"/v1/web-source", "/v1/web-source/discard"}:
            super().do_POST()
            return
        try:
            self._authenticate_transport()
            body = self._read_json(
                max_bytes=(
                    _WEB_SOURCE_UPLOAD_BODY_BYTES
                    if path == "/v1/web-source"
                    else 1_048_576
                )
            )
            if path == "/v1/web-source":
                self._upload_web_source(body)
            else:
                self._discard_web_source(body)
        except DesktopIdentityError as error:
            self._send_error(HTTPStatus.UNAUTHORIZED, str(error))
        except ExecutionCoordinatorError as error:
            self._send_error(HTTPStatus.CONFLICT, str(error))
        except (WebSourceAdmissionError, ValueError, TypeError, json.JSONDecodeError) as error:
            self._send_error(HTTPStatus.BAD_REQUEST, str(error))

    def _upload_web_source(self, body: dict[str, Any]) -> None:
        session = self._authenticated_session()
        filename = _identity_core._required_string(body, "filename")
        if (
            len(filename) > _MAX_WEB_SOURCE_FILENAME_CHARS
            or not filename.casefold().endswith(".zip")
        ):
            raise ValueError("existing Web source filename must be a bounded ZIP name")
        supplied_sha256 = _identity_core._required_string(body, "sha256").lower()
        if len(supplied_sha256) != 64 or any(
            character not in "0123456789abcdef" for character in supplied_sha256
        ):
            raise ValueError("Web source archive sha256 is invalid")
        encoded = _identity_core._required_string(body, "content_base64")
        try:
            archive = base64.b64decode(encoded, validate=True)
        except (binascii.Error, ValueError) as error:
            raise ValueError("Web source archive base64 payload is invalid") from error
        if len(archive) > MAX_ARCHIVE_BYTES:
            raise ValueError("Web source archive exceeds the upload limit")
        digest = hashlib.sha256(archive).hexdigest()
        if not hmac.compare_digest(digest, supplied_sha256):
            raise ValueError("Web source archive sha256 does not match uploaded bytes")
        record = self.server.web_source.put(
            archive=archive,
            principal_id=session.principal_id,
            tenant_id=session.tenant_id,
        )
        self._send_json(HTTPStatus.CREATED, record.public_metadata())

    def _discard_web_source(self, body: dict[str, Any]) -> None:
        session = self._authenticated_session()
        asset_id = _identity_core._required_string(body, "asset_id")
        self.server.web_source.discard_unbound(
            asset_id,
            principal_id=session.principal_id,
            tenant_id=session.tenant_id,
        )
        self._send_json(HTTPStatus.OK, {"discarded": True, "asset_id": asset_id})

    def _submit_authenticated_intent(self, body: dict[str, Any]) -> None:
        web_source_value = body.get("web_source_asset_id")
        if web_source_value is None:
            super()._submit_authenticated_intent(body)
            return
        if not isinstance(web_source_value, str) or not web_source_value.strip():
            raise ValueError("web_source_asset_id must be non-blank text")
        if body.get("source_media_asset_id") is not None:
            raise ValueError("Web source and source video cannot share one execution request")
        web_source_asset_id = web_source_value.strip()

        session = self._authenticated_session()
        objective = _identity_core._required_string(body, "objective")
        if len(objective) > 20_000:
            raise ValueError("objective exceeds Desktop input limit")
        if _identity_core._is_video_objective(objective) or _reference_factory_count(objective) != 1:
            raise ValueError("existing Web source may only be attached to one Web Factory request")

        asset_ids = _identity_core._reference_asset_ids(
            body.get("reference_asset_ids", [])
        )
        reference_store = (
            _identity_core._require_reference_store(self.server.reference_assets)
            if asset_ids
            else None
        )
        owned_references = (
            tuple(
                reference_store.get_owned(
                    asset_id,
                    principal_id=session.principal_id,
                    tenant_id=session.tenant_id,
                )
                for asset_id in asset_ids
            )
            if reference_store is not None
            else ()
        )
        digests = tuple(record.sha256 for record in owned_references)
        if len(set(digests)) != len(digests):
            raise ValueError("duplicate reference image content is not allowed")

        source_record = self.server.web_source.get_owned(
            web_source_asset_id,
            principal_id=session.principal_id,
            tenant_id=session.tenant_id,
        )
        request_id = f"exec-{secrets.token_hex(16)}"
        execution = self.server.coordinator.prepare(
            request_id,
            objective,
            token=self.server.bearer_token,
            principal_id=session.principal_id,
            tenant_id=session.tenant_id,
            now=datetime.now(timezone.utc),
        )
        self.server.web_source.bind_request(
            request_id,
            source_record.asset_id,
            principal_id=session.principal_id,
            tenant_id=session.tenant_id,
        )
        if reference_store is not None:
            reference_store.bind_request(
                request_id,
                asset_ids,
                principal_id=session.principal_id,
                tenant_id=session.tenant_id,
            )
        if execution.get("execution_status") == "ADMITTED":
            self._start_execution(request_id)
        response = dict(execution)
        response["reference_asset_count"] = len(asset_ids)
        response["web_source_asset_id"] = source_record.asset_id
        response["web_source_tree_sha256"] = source_record.snapshot.tree_sha256
        self._send_json(HTTPStatus.CREATED, response)


__all__ = [
    "WebSourceDesktopIdentityHTTPServer",
    "WebSourceDesktopIdentityRequestHandler",
]
