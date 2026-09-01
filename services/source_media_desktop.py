"""Authenticated Desktop boundary for governed source-video uploads and binding.

The base Desktop identity server remains the authority for sessions, execution
admission, approvals and cancellation. This adapter adds only source-media input
handling and preserves the existing shared Web/Video reference flow for requests
that do not carry source media. Exact first/last-frame uploads are accepted only
when the separately configured provider reference relay is fail-closed ready.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import os
import secrets
from datetime import datetime, timezone
from http import HTTPStatus
from typing import Any
from urllib.parse import urlparse

from services import desktop_identity_server_core as _identity_core
from services.desktop_identity_server import (
    DesktopIdentityHTTPServer,
    DesktopIdentityRequestHandler,
)
from services.desktop_oidc import DesktopIdentityError, DesktopOIDCService
from services.execution_coordinator import ExecutionCoordinator, ExecutionCoordinatorError
from services.reference_assets import ReferenceAssetRole, ReferenceAssetStore
from services.source_media import (
    MAX_SOURCE_MEDIA_BYTES,
    SourceMediaError,
    SourceMediaStore,
)

# Base64 expands bytes by roughly 4/3. Keep a small bounded JSON envelope margin.
_SOURCE_MEDIA_UPLOAD_BODY_BYTES = ((MAX_SOURCE_MEDIA_BYTES + 2) // 3) * 4 + 1_048_576


class SourceMediaDesktopIdentityHTTPServer(DesktopIdentityHTTPServer):
    """Existing Desktop identity server plus private source/reference inputs."""

    def __init__(
        self,
        server_address: tuple[str, int],
        *,
        bearer_token: str,
        identity: DesktopOIDCService | None,
        coordinator: ExecutionCoordinator,
        reference_assets: ReferenceAssetStore | None = None,
        source_media: SourceMediaStore,
    ) -> None:
        super().__init__(
            server_address,
            bearer_token=bearer_token,
            identity=identity,
            coordinator=coordinator,
            reference_assets=reference_assets,
        )
        self.source_media = source_media
        self.native_frame_relay_configured = _native_frame_relay_configured()
        # The server has not started serving yet. Replacing only the request
        # handler preserves the canonical lifecycle, recovery and auth boundary.
        self.RequestHandlerClass = SourceMediaDesktopIdentityRequestHandler


class SourceMediaDesktopIdentityRequestHandler(DesktopIdentityRequestHandler):
    server: SourceMediaDesktopIdentityHTTPServer

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path not in {"/v1/source-media", "/v1/source-media/discard"}:
            super().do_POST()
            return
        try:
            self._authenticate_transport()
            body = self._read_json(
                max_bytes=(
                    _SOURCE_MEDIA_UPLOAD_BODY_BYTES
                    if path == "/v1/source-media"
                    else 1_048_576
                )
            )
            if path == "/v1/source-media":
                self._upload_source_media(body)
            else:
                self._discard_source_media(body)
        except DesktopIdentityError as error:
            self._send_error(HTTPStatus.UNAUTHORIZED, str(error))
        except ExecutionCoordinatorError as error:
            self._send_error(HTTPStatus.CONFLICT, str(error))
        except (SourceMediaError, ValueError, TypeError, json.JSONDecodeError) as error:
            self._send_error(HTTPStatus.BAD_REQUEST, str(error))

    def _upload_reference_asset(self, body: dict[str, Any]) -> None:
        role_value = body.get("role")
        if role_value not in {
            ReferenceAssetRole.FIRST_FRAME.value,
            ReferenceAssetRole.LAST_FRAME.value,
        }:
            super()._upload_reference_asset(body)
            return
        if not self.server.native_frame_relay_configured:
            # Preserve the canonical fail-closed error wording for unverified
            # exact-frame uploads.
            super()._upload_reference_asset(body)
            return

        session = self._authenticated_session()
        store = _identity_core._require_reference_store(self.server.reference_assets)
        filename = _identity_core._required_string(body, "filename")
        mime_type = _identity_core._required_string(body, "mime_type")
        supplied_sha256 = _identity_core._required_string(body, "sha256").lower()
        instruction_value = body.get("instruction")
        if instruction_value is not None and not isinstance(instruction_value, str):
            raise TypeError("instruction must be text when provided")
        if len(supplied_sha256) != 64 or any(
            character not in "0123456789abcdef" for character in supplied_sha256
        ):
            raise ValueError("reference image sha256 is invalid")
        role = ReferenceAssetRole(role_value)
        encoded = _identity_core._required_string(body, "content_base64")
        try:
            content = base64.b64decode(encoded, validate=True)
        except (binascii.Error, ValueError) as error:
            raise ValueError("reference image base64 payload is invalid") from error
        digest = hashlib.sha256(content).hexdigest()
        if not hmac.compare_digest(digest, supplied_sha256):
            raise ValueError("reference image sha256 does not match uploaded bytes")
        record = store.put(
            content=content,
            claimed_mime_type=mime_type,
            original_filename=filename,
            role=role,
            instruction=instruction_value,
            principal_id=session.principal_id,
            tenant_id=session.tenant_id,
        )
        self._send_json(
            HTTPStatus.CREATED,
            {
                "asset_id": record.asset_id,
                "sha256": record.sha256,
                "mime_type": record.mime_type,
                "width": record.width,
                "height": record.height,
                "size_bytes": record.size_bytes,
                "role": record.role.value,
                "native_frame_relay_configured": True,
            },
        )

    def _upload_source_media(self, body: dict[str, Any]) -> None:
        session = self._authenticated_session()
        filename = _identity_core._required_string(body, "filename")
        mime_type = _identity_core._required_string(body, "mime_type")
        supplied_sha256 = _identity_core._required_string(body, "sha256").lower()
        if len(supplied_sha256) != 64 or any(
            character not in "0123456789abcdef" for character in supplied_sha256
        ):
            raise ValueError("source video sha256 is invalid")
        encoded = _identity_core._required_string(body, "content_base64")
        try:
            content = base64.b64decode(encoded, validate=True)
        except (binascii.Error, ValueError) as error:
            raise ValueError("source video base64 payload is invalid") from error
        digest = hashlib.sha256(content).hexdigest()
        if not hmac.compare_digest(digest, supplied_sha256):
            raise ValueError("source video sha256 does not match uploaded bytes")
        record = self.server.source_media.put(
            content=content,
            claimed_mime_type=mime_type,
            original_filename=filename,
            principal_id=session.principal_id,
            tenant_id=session.tenant_id,
        )
        self._send_json(HTTPStatus.CREATED, record.public_metadata())

    def _discard_source_media(self, body: dict[str, Any]) -> None:
        session = self._authenticated_session()
        asset_id = _identity_core._required_string(body, "asset_id")
        self.server.source_media.discard_unbound(
            asset_id,
            principal_id=session.principal_id,
            tenant_id=session.tenant_id,
        )
        self._send_json(HTTPStatus.OK, {"discarded": True, "asset_id": asset_id})

    def _submit_authenticated_intent(self, body: dict[str, Any]) -> None:
        source_value = body.get("source_media_asset_id")
        if source_value is None:
            super()._submit_authenticated_intent(body)
            return
        if not isinstance(source_value, str) or not source_value.strip():
            raise ValueError("source_media_asset_id must be non-blank text")
        source_asset_id = source_value.strip()

        session = self._authenticated_session()
        objective = _identity_core._required_string(body, "objective")
        if len(objective) > 20_000:
            raise ValueError("objective exceeds Desktop input limit")
        if not _identity_core._is_video_objective(objective):
            raise ValueError("source video may only be attached to Video Factory requests")

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

        # Ownership and byte integrity are checked before any execution record is
        # prepared, so cross-tenant or stale source assets cannot create work.
        source_record = self.server.source_media.get_owned(
            source_asset_id,
            principal_id=session.principal_id,
            tenant_id=session.tenant_id,
        )
        self.server.source_media.require_registered_path(source_record.asset_id)

        request_id = f"exec-{secrets.token_hex(16)}"
        execution = self.server.coordinator.prepare(
            request_id,
            objective,
            token=self.server.bearer_token,
            principal_id=session.principal_id,
            tenant_id=session.tenant_id,
            now=datetime.now(timezone.utc),
        )
        self.server.source_media.bind_request(
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
        response["source_media_asset_id"] = source_record.asset_id
        response["source_media_sha256"] = source_record.sha256
        self._send_json(HTTPStatus.CREATED, response)


def _native_frame_relay_configured() -> bool:
    mode = os.environ.get("ILAIOS_VIDEO_PROVIDER_MODE", "verified-free").strip()
    upload_url = os.environ.get("ILAIOS_REFERENCE_RELAY_UPLOAD_URL", "").strip()
    upload_token = os.environ.get("ILAIOS_REFERENCE_RELAY_UPLOAD_TOKEN", "").strip()
    return (
        mode == "managed-bounded"
        and upload_url.startswith("https://")
        and bool(upload_token)
    )


__all__ = [
    "SourceMediaDesktopIdentityHTTPServer",
    "SourceMediaDesktopIdentityRequestHandler",
]
