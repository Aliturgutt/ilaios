"""Authenticated Desktop upload boundary for Video Factory reference images."""

from __future__ import annotations

import secrets
from datetime import datetime, timezone
from http import HTTPStatus
from urllib.parse import urlparse

from services.desktop_identity_server import (
    DesktopIdentityHTTPServer,
    DesktopIdentityRequestHandler,
)
from services.video_reference_store import (
    DesktopVideoReferenceStore,
    VideoReferenceStoreError,
)
from src.video_automation.reference_images import (
    MAX_REFERENCE_IMAGE_BYTES,
    ReferenceImageRole,
)


class ReferenceAwareDesktopIdentityHTTPServer(DesktopIdentityHTTPServer):
    """Desktop identity server with a bounded private reference-image ingress."""

    def __init__(
        self,
        server_address: tuple[str, int],
        *,
        bearer_token: str,
        identity,
        coordinator,
        video_references: DesktopVideoReferenceStore,
    ) -> None:
        super().__init__(
            server_address,
            bearer_token=bearer_token,
            identity=identity,
            coordinator=coordinator,
        )
        self.video_references = video_references
        # Base construction happens before any request can be served. Replacing
        # the handler class here preserves the canonical server lifecycle while
        # keeping the generic identity implementation unchanged.
        self.RequestHandlerClass = ReferenceAwareDesktopIdentityRequestHandler


class ReferenceAwareDesktopIdentityRequestHandler(DesktopIdentityRequestHandler):
    server: ReferenceAwareDesktopIdentityHTTPServer

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path != "/v1/desktop/video-reference":
            super().do_POST()
            return
        try:
            self._authenticate_transport()
            session = self._authenticated_session()
            draft_id = self.headers.get("X-ILAIOS-Video-Draft", "").strip()
            role_value = self.headers.get("X-ILAIOS-Reference-Role", "").strip()
            if not draft_id:
                raise ValueError("X-ILAIOS-Video-Draft is required")
            try:
                role = ReferenceImageRole(role_value)
            except ValueError as exc:
                raise ValueError("unknown video reference role") from exc
            media_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip()
            raw_length = self.headers.get("Content-Length")
            if raw_length is None:
                raise ValueError("Content-Length is required")
            length = int(raw_length)
            if length < 1 or length > MAX_REFERENCE_IMAGE_BYTES:
                raise ValueError("reference image body length is outside allowed bounds")
            content = self.rfile.read(length)
            if len(content) != length:
                raise ValueError("reference image upload was truncated")
            stored = self.server.video_references.add_upload(
                draft_id=draft_id,
                principal_id=session.principal_id,
                tenant_id=session.tenant_id,
                content=content,
                media_type=media_type,
                role=role,
            )
            self._send_json(HTTPStatus.CREATED, stored.to_json())
        except VideoReferenceStoreError as error:
            self._send_error(HTTPStatus.BAD_REQUEST, str(error))
        except ValueError as error:
            self._send_error(HTTPStatus.BAD_REQUEST, str(error))
        except Exception as error:
            # Parent handler maps DesktopIdentityError to 401. Avoid importing a
            # second identity type here; preserve the public failure text while
            # never exposing stack/secret data.
            if error.__class__.__name__ == "DesktopIdentityError":
                self._send_error(HTTPStatus.UNAUTHORIZED, str(error))
                return
            raise

    def _submit_authenticated_intent(self, body: dict[str, object]) -> None:
        session = self._authenticated_session()
        objective_value = body.get("objective")
        if not isinstance(objective_value, str) or not objective_value.strip():
            raise TypeError("objective must be a non-empty string")
        objective = objective_value.strip()
        if len(objective) > 20_000:
            raise ValueError("objective exceeds Desktop input limit")
        draft_value = body.get("video_reference_draft_id")
        if draft_value is not None and (
            not isinstance(draft_value, str) or not draft_value.strip()
        ):
            raise TypeError("video_reference_draft_id must be non-empty when provided")
        draft_id = None if draft_value is None else draft_value.strip()

        request_id = f"exec-{secrets.token_hex(16)}"
        if draft_id is not None:
            # Binding precedes coordinator preparation so the provider runtime
            # can resolve the same durable context even when execution begins
            # immediately after admission.
            self.server.video_references.bind_draft(
                draft_id=draft_id,
                request_id=request_id,
                principal_id=session.principal_id,
                tenant_id=session.tenant_id,
            )
        execution = self.server.coordinator.prepare(
            request_id,
            objective,
            token=self.server.bearer_token,
            principal_id=session.principal_id,
            tenant_id=session.tenant_id,
            now=datetime.now(timezone.utc),
        )
        if execution.get("execution_status") == "ADMITTED":
            self._start_execution(request_id)
        self._send_json(HTTPStatus.CREATED, execution)
