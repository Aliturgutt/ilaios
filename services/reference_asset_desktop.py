"""Authenticated Desktop HTTP boundary for governed reference image ingest."""

from __future__ import annotations

import base64
import binascii
import json
import secrets
from datetime import datetime, timezone
from http import HTTPStatus
from typing import Any
from urllib.parse import urlparse

from services.desktop_identity_server import (
    DesktopIdentityHTTPServer,
    DesktopIdentityRequestHandler,
    _required_string,
)
from services.desktop_oidc import DesktopIdentityError, DesktopOIDCService
from services.execution_coordinator import (
    ExecutionCoordinator,
    ExecutionCoordinatorError,
    classify_execution_plan,
)
from services.reference_assets import (
    MAX_REFERENCE_ASSETS,
    ReferenceAssetError,
    get_reference_asset_store,
)

_MAX_REFERENCE_UPLOAD_JSON_BYTES = 12 * 1024 * 1024
_REFERENCE_CAPABILITIES = frozenset(
    {"ilaios.capability.web-factory", "ilaios.capability.video-factory"}
)


class ReferenceAwareDesktopIdentityHTTPServer(DesktopIdentityHTTPServer):
    """Drop-in Desktop identity server that adds the reference-asset endpoint."""

    def __init__(
        self,
        server_address: tuple[str, int],
        *,
        bearer_token: str,
        identity: DesktopOIDCService | None,
        coordinator: ExecutionCoordinator,
    ) -> None:
        super().__init__(
            server_address,
            bearer_token=bearer_token,
            identity=identity,
            coordinator=coordinator,
        )
        self.RequestHandlerClass = ReferenceAwareDesktopIdentityRequestHandler


class ReferenceAwareDesktopIdentityRequestHandler(DesktopIdentityRequestHandler):
    """Adds upload/binding while preserving all existing identity endpoints."""

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/v1/desktop/reference-assets":
            super().do_POST()
            return
        try:
            self._authenticate_transport()
            session = self._authenticated_session()
            body = self._read_reference_json()
            filename = _required_string(body, "filename")
            media_type = _required_string(body, "media_type")
            encoded = _required_string(body, "content_base64")
            claimed_sha256_value = body.get("sha256")
            if claimed_sha256_value is not None and not isinstance(
                claimed_sha256_value, str
            ):
                raise TypeError("sha256 must be a string when supplied")
            try:
                content = base64.b64decode(encoded, validate=True)
            except (binascii.Error, ValueError) as error:
                raise ValueError("reference image base64 payload is invalid") from error
            record = get_reference_asset_store().ingest(
                principal_id=session.principal_id,
                tenant_id=session.tenant_id,
                original_name=filename,
                media_type=media_type,
                content=content,
                claimed_sha256=claimed_sha256_value,
            )
            self._send_json(HTTPStatus.CREATED, record.public_metadata())
        except DesktopIdentityError as error:
            self._send_error(HTTPStatus.UNAUTHORIZED, str(error))
        except ExecutionCoordinatorError as error:
            self._send_error(HTTPStatus.CONFLICT, str(error))
        except ReferenceAssetError as error:
            self._send_error(HTTPStatus.BAD_REQUEST, str(error))
        except (ValueError, TypeError, json.JSONDecodeError) as error:
            self._send_error(HTTPStatus.BAD_REQUEST, str(error))

    def _submit_authenticated_intent(self, body: dict[str, Any]) -> None:
        raw_ids = body.get("reference_asset_ids")
        if raw_ids is None or raw_ids == []:
            super()._submit_authenticated_intent(body)
            return
        if not isinstance(raw_ids, list):
            raise TypeError("reference_asset_ids must be a list")
        if len(raw_ids) > MAX_REFERENCE_ASSETS:
            raise ValueError("too many reference images")
        asset_ids: list[str] = []
        for value in raw_ids:
            if not isinstance(value, str) or not value.strip():
                raise TypeError("reference_asset_ids must contain non-empty strings")
            asset_ids.append(value.strip())
        if len(set(asset_ids)) != len(asset_ids):
            raise ValueError("reference_asset_ids must be unique")

        session = self._authenticated_session()
        objective = _required_string(body, "objective")
        if len(objective) > 20_000:
            raise ValueError("objective exceeds Desktop input limit")
        plan = classify_execution_plan(objective)
        if not _REFERENCE_CAPABILITIES.intersection(plan.capability_ids):
            raise ValueError(
                "reference images are supported only for Web Factory or Video Factory"
            )

        request_id = f"exec-{secrets.token_hex(16)}"
        store = get_reference_asset_store()
        store.bind_request(
            request_id,
            asset_ids,
            principal_id=session.principal_id,
            tenant_id=session.tenant_id,
        )
        try:
            execution = self.server.coordinator.prepare(
                request_id,
                objective,
                token=self.server.bearer_token,
                principal_id=session.principal_id,
                tenant_id=session.tenant_id,
                now=datetime.now(timezone.utc),
            )
            job_id = execution.get("job_id")
            if not isinstance(job_id, str) or not job_id:
                raise ExecutionCoordinatorError(
                    "prepared execution did not return a valid job identity"
                )
            store.attach_job(request_id, job_id)
        except Exception:
            store.unbind_request(request_id)
            raise
        if execution.get("execution_status") == "ADMITTED":
            self._start_execution(request_id)
        execution = dict(execution)
        execution["reference_asset_count"] = len(asset_ids)
        execution["reference_asset_ids"] = asset_ids
        self._send_json(HTTPStatus.CREATED, execution)

    def _read_reference_json(self) -> dict[str, Any]:
        raw_length = self.headers.get("Content-Length")
        if raw_length is None:
            raise ValueError("Content-Length is required")
        length = int(raw_length)
        if length < 1 or length > _MAX_REFERENCE_UPLOAD_JSON_BYTES:
            raise ValueError("reference upload body length is outside allowed bounds")
        value = json.loads(self.rfile.read(length).decode("utf-8"))
        if not isinstance(value, dict):
            raise TypeError("request body must be a JSON object")
        return value
