"""Loopback HTTP boundary for ILAIOS Desktop human identity and execution sessions."""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import secrets
import threading
import time
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, cast
from urllib.parse import parse_qs, urlparse

from services.desktop_oidc import (
    DesktopAuthStatus,
    DesktopIdentityError,
    DesktopOIDCService,
)
from services.execution_cancellation import cancel_execution
from services.execution_coordinator import (
    ExecutionCoordinator,
    ExecutionCoordinatorError,
)
from services.identity import Session
from services.reference_assets import (
    MAX_REFERENCE_ASSETS,
    ReferenceAssetError,
    ReferenceAssetRole,
    ReferenceAssetStore,
)

_RECOVERY_SWEEP_SECONDS = 60.0
_REFERENCE_UPLOAD_BODY_BYTES = 15 * 1024 * 1024


class DesktopIdentityHTTPServer(ThreadingHTTPServer):
    """Human identity adapter; execution authority remains in canonical services."""

    daemon_threads = True

    def __init__(
        self,
        server_address: tuple[str, int],
        *,
        bearer_token: str,
        identity: DesktopOIDCService | None,
        coordinator: ExecutionCoordinator,
        reference_assets: ReferenceAssetStore | None = None,
    ) -> None:
        if not bearer_token:
            raise DesktopIdentityError("Desktop identity transport token is required")
        super().__init__(server_address, DesktopIdentityRequestHandler)
        self.bearer_token = bearer_token
        self.identity = identity
        self.coordinator = coordinator
        self.reference_assets = reference_assets or _reference_store_for(coordinator)
        self._next_recovery_sweep = time.monotonic()

    def service_actions(self) -> None:
        """Run bounded crash/orphan reconciliation from the trusted server lifecycle."""
        monotonic_now = time.monotonic()
        if monotonic_now < self._next_recovery_sweep:
            return
        self._next_recovery_sweep = monotonic_now + _RECOVERY_SWEEP_SECONDS
        try:
            reconciled = self.coordinator.recover_stale(
                token=self.bearer_token,
                now=datetime.now(timezone.utc),
            )
        except Exception as error:
            print(
                json.dumps(
                    {
                        "component": "desktop_identity",
                        "event": "execution_recovery_sweep_failed",
                        "error_type": type(error).__name__,
                    },
                    sort_keys=True,
                ),
                flush=True,
            )
            return
        if reconciled:
            print(
                json.dumps(
                    {
                        "component": "desktop_identity",
                        "event": "execution_recovery_sweep",
                        "reconciled_count": len(reconciled),
                    },
                    sort_keys=True,
                ),
                flush=True,
            )


class DesktopIdentityRequestHandler(BaseHTTPRequestHandler):
    server: DesktopIdentityHTTPServer

    def do_GET(self) -> None:
        try:
            parsed = urlparse(self.path)
            if parsed.path == "/health/ready":
                self._send_json(
                    HTTPStatus.OK,
                    {
                        "status": "ready",
                        "providers_configured": self.server.identity is not None,
                        "governed_execution": self.server.identity is not None,
                        "reference_assets": self.server.reference_assets is not None,
                        "reference_asset_limit": MAX_REFERENCE_ASSETS,
                    },
                )
                return
            if parsed.path == "/oauth/callback":
                self._complete_browser_callback(parse_qs(parsed.query))
                return

            self._authenticate_transport()
            if parsed.path == "/v1/auth/providers":
                providers = (
                    self.server.identity.providers()
                    if self.server.identity is not None
                    else ()
                )
                self._send_json(HTTPStatus.OK, {"providers": providers})
                return
            if parsed.path == "/v1/auth/status":
                identity = self._require_identity()
                state = _single_query(parse_qs(parsed.query), "state")
                self._send_json(HTTPStatus.OK, _status_json(identity.status(state)))
                return
            if parsed.path == "/v1/li/state":
                session = self._authenticated_session()
                identity = self._require_identity()
                if not identity.is_li_founder_session(session.session_id):
                    self._send_error(HTTPStatus.FORBIDDEN, "request denied")
                    return
                self._send_json(
                    HTTPStatus.OK,
                    {
                        "name": "Li",
                        "founder_operator": True,
                        "user_id": session.principal_id,
                        "tenant_id": session.tenant_id,
                        "source": "canonical_desktop_session",
                    },
                )
                return
            if parsed.path == "/v1/li/memories":
                session = self._authenticated_session()
                identity = self._require_identity()
                if not identity.is_li_founder_session(session.session_id):
                    self._send_error(HTTPStatus.FORBIDDEN, "request denied")
                    return
                memories = identity.list_li_memories(session.session_id)
                self._send_json(HTTPStatus.OK, {"memories": memories})
                return
            if parsed.path == "/v1/execution/status":
                session = self._authenticated_session()
                request_id = _single_query(parse_qs(parsed.query), "request_id")
                execution = self.server.coordinator.get(
                    request_id,
                    principal_id=session.principal_id,
                    tenant_id=session.tenant_id,
                )
                self._send_json(HTTPStatus.OK, execution)
                return
            if parsed.path == "/v1/web/deployments":
                session = self._authenticated_session()
                request_id = _single_query(parse_qs(parsed.query), "request_id")
                self._send_json(
                    HTTPStatus.OK,
                    {
                        "request_id": request_id,
                        "deployments": self.server.coordinator.web_deployment_history(
                            request_id,
                            principal_id=session.principal_id,
                            tenant_id=session.tenant_id,
                        ),
                    },
                )
                return
            self._send_error(HTTPStatus.NOT_FOUND, "unknown endpoint")
        except DesktopIdentityError as error:
            self._send_error(HTTPStatus.UNAUTHORIZED, str(error))
        except ExecutionCoordinatorError as error:
            self._send_error(HTTPStatus.CONFLICT, str(error))
        except ValueError as error:
            self._send_error(HTTPStatus.BAD_REQUEST, str(error))

    def do_POST(self) -> None:
        try:
            self._authenticate_transport()
            path = urlparse(self.path).path
            body = self._read_json(
                max_bytes=(
                    _REFERENCE_UPLOAD_BODY_BYTES
                    if path == "/v1/reference-assets"
                    else 1_048_576
                )
            )
            if path == "/v1/runtime/shutdown":
                self._send_json(HTTPStatus.ACCEPTED, {"shutdown": True})
                threading.Thread(
                    target=self.server.shutdown,
                    name="ilaios-desktop-shutdown",
                    daemon=True,
                ).start()
                return
            if path == "/v1/auth/start":
                identity = self._require_identity()
                provider_id = _required_string(body, "provider_id")
                host, port = _server_endpoint(self.server.server_address)
                redirect_uri = f"http://{host}:{port}/oauth/callback"
                started = identity.start(provider_id, redirect_uri)
                self._send_json(
                    HTTPStatus.CREATED,
                    {
                        "provider_id": started.provider_id,
                        "state": started.state,
                        "authorization_url": started.authorization_url,
                        "expires_at": started.expires_at.isoformat(),
                    },
                )
                return
            if path == "/v1/auth/logout":
                identity = self._require_identity()
                identity.logout(_required_string(body, "session_id"))
                self._send_json(HTTPStatus.OK, {"logged_out": True})
                return
            if path == "/v1/li/memories":
                session = self._authenticated_session()
                identity = self._require_identity()
                if not identity.is_li_founder_session(session.session_id):
                    self._send_error(HTTPStatus.FORBIDDEN, "request denied")
                    return
                kind = _required_string(body, "kind")
                content = _required_string(body, "content")
                if set(body) != {"kind", "content"}:
                    raise ValueError("Li memory request contains unexpected fields")
                record = identity.remember_li_memory(
                    session.session_id,
                    kind=kind,
                    content=content,
                )
                self._send_json(HTTPStatus.CREATED, record)
                return
            if path == "/v1/reference-assets":
                self._upload_reference_asset(body)
                return
            if path == "/v1/desktop/intent":
                self._submit_authenticated_intent(body)
                return
            if path == "/v1/web/preview":
                self._preview_web(body)
                return
            if path == "/v1/web/publish":
                self._publish_web(body)
                return
            if path == "/v1/execution/decision":
                self._decide_authenticated_execution(body)
                return
            if path == "/v1/execution/resume":
                self._resume_authenticated_execution(body)
                return
            if path == "/v1/execution/cancel":
                self._cancel_authenticated_execution(body)
                return
            self._send_error(HTTPStatus.NOT_FOUND, "unknown endpoint")
        except DesktopIdentityError as error:
            self._send_error(HTTPStatus.UNAUTHORIZED, str(error))
        except ExecutionCoordinatorError as error:
            self._send_error(HTTPStatus.CONFLICT, str(error))
        except (ValueError, TypeError, json.JSONDecodeError) as error:
            self._send_error(HTTPStatus.BAD_REQUEST, str(error))

    def log_message(self, message_format: str, *args: object) -> None:
        print(
            json.dumps(
                {
                    "component": "desktop_identity",
                    "client": self.client_address[0],
                    "message": message_format % args,
                },
                sort_keys=True,
            ),
            flush=True,
        )

    def _complete_browser_callback(self, query: dict[str, list[str]]) -> None:
        identity = self._require_identity()
        state = _single_query(query, "state")
        error = query.get("error", [""])[0]
        if error:
            identity.reject(state, error)
            self._send_html(
                HTTPStatus.OK,
                "ILAIOS sign-in was not completed. You can close this tab.",
            )
            return
        code = _single_query(query, "code")
        identity.complete(state, code)
        self._send_html(
            HTTPStatus.OK,
            "ILAIOS sign-in completed. You can close this tab and return to ILAIOS Desktop.",
        )

    def _upload_reference_asset(self, body: dict[str, Any]) -> None:
        session = self._authenticated_session()
        store = _require_reference_store(self.server.reference_assets)
        filename = _required_string(body, "filename")
        mime_type = _required_string(body, "mime_type")
        role_value = _required_string(body, "role")
        supplied_sha256 = _required_string(body, "sha256").lower()
        instruction_value = body.get("instruction")
        if instruction_value is not None and not isinstance(instruction_value, str):
            raise TypeError("instruction must be text when provided")
        if len(supplied_sha256) != 64 or any(
            character not in "0123456789abcdef" for character in supplied_sha256
        ):
            raise ValueError("reference image sha256 is invalid")
        try:
            role = ReferenceAssetRole(role_value)
        except ValueError as error:
            raise ValueError("reference image role is invalid") from error
        if role in {ReferenceAssetRole.FIRST_FRAME, ReferenceAssetRole.LAST_FRAME}:
            raise ValueError(
                "exact first/last frame references require a separately verified provider relay"
            )
        encoded = _required_string(body, "content_base64")
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
            },
        )

    def _submit_authenticated_intent(self, body: dict[str, Any]) -> None:
        session = self._authenticated_session()
        objective = _required_string(body, "objective")
        if len(objective) > 20_000:
            raise ValueError("objective exceeds Desktop input limit")
        asset_ids = _reference_asset_ids(body.get("reference_asset_ids", []))
        if asset_ids and not _is_video_objective(objective):
            raise ValueError("reference images may only be attached to Video Factory requests")

        store = _require_reference_store(self.server.reference_assets) if asset_ids else None
        owned_records = (
            tuple(
                store.get_owned(
                    asset_id,
                    principal_id=session.principal_id,
                    tenant_id=session.tenant_id,
                )
                for asset_id in asset_ids
            )
            if store is not None
            else ()
        )
        digests = tuple(record.sha256 for record in owned_records)
        if len(set(digests)) != len(digests):
            raise ValueError("duplicate reference image content is not allowed")

        request_id = f"exec-{secrets.token_hex(16)}"
        execution = self.server.coordinator.prepare(
            request_id,
            objective,
            token=self.server.bearer_token,
            principal_id=session.principal_id,
            tenant_id=session.tenant_id,
            now=datetime.now(timezone.utc),
        )
        if store is not None:
            store.bind_request(
                request_id,
                asset_ids,
                principal_id=session.principal_id,
                tenant_id=session.tenant_id,
            )
        if execution.get("execution_status") == "ADMITTED":
            self._start_execution(request_id)
        response = dict(execution)
        response["reference_asset_count"] = len(asset_ids)
        self._send_json(HTTPStatus.CREATED, response)

    def _decide_authenticated_execution(self, body: dict[str, Any]) -> None:
        session = self._authenticated_session()
        request_id = _required_string(body, "request_id")
        decision = _required_string(body, "decision")
        status = self.server.coordinator.decide(
            request_id,
            approver_id=session.principal_id,
            tenant_id=session.tenant_id,
            decision=decision,
            now=datetime.now(timezone.utc),
        )
        if status == "DENIED":
            self._send_json(
                HTTPStatus.OK,
                {"request_id": request_id, "execution_status": "DENIED"},
            )
            return
        self._start_execution(request_id)
        self._send_json(
            HTTPStatus.ACCEPTED,
            {"request_id": request_id, "execution_status": "EXECUTION_STARTED"},
        )

    def _preview_web(self, body: dict[str, Any]) -> None:
        session = self._authenticated_session()
        request_id = _required_string(body, "request_id")
        receipt = self.server.coordinator.preview_web(
            request_id,
            principal_id=session.principal_id,
            tenant_id=session.tenant_id,
            now=datetime.now(timezone.utc),
        )
        self._send_json(HTTPStatus.CREATED, receipt)

    def _publish_web(self, body: dict[str, Any]) -> None:
        session = self._authenticated_session()
        request_id = _required_string(body, "request_id")
        now = datetime.now(timezone.utc)
        request = self.server.coordinator.request_web_publish(
            request_id,
            principal_id=session.principal_id,
            tenant_id=session.tenant_id,
            now=now,
        )
        if request["status"] != "approved":
            self._send_json(HTTPStatus.ACCEPTED, request)
            return
        receipt = self.server.coordinator.publish_web(
            request_id,
            principal_id=session.principal_id,
            tenant_id=session.tenant_id,
            now=now,
        )
        self._send_json(HTTPStatus.CREATED, receipt)

    def _resume_authenticated_execution(self, body: dict[str, Any]) -> None:
        session = self._authenticated_session()
        request_id = _required_string(body, "request_id")
        execution = self.server.coordinator.get(
            request_id,
            principal_id=session.principal_id,
            tenant_id=session.tenant_id,
        )
        if execution.get("terminal") is True:
            self._send_json(HTTPStatus.OK, execution)
            return
        self._start_execution(request_id)
        self._send_json(
            HTTPStatus.ACCEPTED,
            {"request_id": request_id, "execution_status": "RESUME_REQUESTED"},
        )

    def _cancel_authenticated_execution(self, body: dict[str, Any]) -> None:
        session = self._authenticated_session()
        request_id = _required_string(body, "request_id")
        reason_value = body.get("reason", "user requested cancellation")
        if not isinstance(reason_value, str) or not reason_value.strip():
            raise TypeError("reason must be a non-empty string")
        execution = cancel_execution(
            self.server.coordinator,
            request_id,
            token=self.server.bearer_token,
            principal_id=session.principal_id,
            tenant_id=session.tenant_id,
            reason=reason_value.strip(),
            now=datetime.now(timezone.utc),
        )
        self._send_json(HTTPStatus.OK, execution)

    def _start_execution(self, request_id: str) -> None:
        thread = threading.Thread(
            target=self._run_execution,
            args=(request_id,),
            name=f"ilaios-execution-{request_id}",
            daemon=True,
        )
        thread.start()

    def _run_execution(self, request_id: str) -> None:
        try:
            self.server.coordinator.resume(
                request_id,
                token=self.server.bearer_token,
                now=datetime.now(timezone.utc),
            )
        except Exception as error:
            print(
                json.dumps(
                    {
                        "component": "desktop_identity",
                        "event": "execution_resume_failed",
                        "request_id": request_id,
                        "error_type": type(error).__name__,
                    },
                    sort_keys=True,
                ),
                flush=True,
            )

    def _authenticated_session(self) -> Session:
        identity = self._require_identity()
        session_id = self.headers.get("X-ILAIOS-Session", "").strip()
        if not session_id:
            raise DesktopIdentityError("Desktop session is required")
        return identity.validate_session(session_id)

    def _authenticate_transport(self) -> None:
        header = self.headers.get("Authorization", "")
        prefix = "Bearer "
        supplied = header[len(prefix) :] if header.startswith(prefix) else ""
        if not supplied or not hmac.compare_digest(
            supplied, self.server.bearer_token
        ):
            raise DesktopIdentityError(
                "Desktop identity transport authentication failed"
            )

    def _require_identity(self) -> DesktopOIDCService:
        identity = self.server.identity
        if identity is None:
            raise DesktopIdentityError("Desktop account sign-in is not configured")
        return identity

    def _read_json(self, *, max_bytes: int = 1_048_576) -> dict[str, Any]:
        raw_length = self.headers.get("Content-Length")
        if raw_length is None:
            raise ValueError("Content-Length is required")
        length = int(raw_length)
        if length < 1 or length > max_bytes:
            raise ValueError("request body length is outside allowed bounds")
        value = json.loads(self.rfile.read(length).decode("utf-8"))
        if not isinstance(value, dict):
            raise TypeError("request body must be a JSON object")
        return cast(dict[str, Any], value)

    def _send_error(self, status: HTTPStatus, message: str) -> None:
        self._send_json(status, {"error": message})

    def _send_json(self, status: HTTPStatus, payload: object) -> None:
        body = json.dumps(payload, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, status: HTTPStatus, message: str) -> None:
        escaped = (
            message.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )
        body = (
            "<!doctype html><html><head><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width,initial-scale=1'>"
            "<title>ILAIOS</title></head><body><main><h1>ILAIOS</h1>"
            f"<p>{escaped}</p></main></body></html>"
        ).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Security-Policy", "default-src 'none'; style-src 'none'")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def _reference_store_for(
    coordinator: ExecutionCoordinator,
) -> ReferenceAssetStore | None:
    database_path = getattr(coordinator, "_database_path", None)
    if not isinstance(database_path, Path):
        return None
    root = database_path.parent
    return ReferenceAssetStore(
        root / "reference-assets.sqlite3",
        root / "reference-assets" / "blobs",
    )


def _require_reference_store(
    store: ReferenceAssetStore | None,
) -> ReferenceAssetStore:
    if store is None:
        raise ReferenceAssetError("reference image storage is unavailable")
    return store


def _reference_asset_ids(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise TypeError("reference_asset_ids must be a list")
    if len(value) > MAX_REFERENCE_ASSETS:
        raise ValueError(
            f"at most {MAX_REFERENCE_ASSETS} reference images are allowed per request"
        )
    normalized: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.startswith("ref-"):
            raise TypeError("reference_asset_ids contains an invalid id")
        normalized.append(item)
    if len(set(normalized)) != len(normalized):
        raise ValueError("duplicate reference asset ids are not allowed")
    return tuple(normalized)


def _is_video_objective(objective: str) -> bool:
    normalized = objective.strip().lower()
    return normalized.startswith("video creation task:") or normalized.startswith(
        "video oluşturma görevi:"
    )


def _server_endpoint(address: tuple[str | bytes, int]) -> tuple[str, int]:
    host, port = address
    if not isinstance(host, str):
        raise DesktopIdentityError("Desktop identity callback host must be text")
    if host not in {"127.0.0.1", "localhost", "::1"}:
        raise DesktopIdentityError("Desktop identity callback must remain loopback")
    if not isinstance(port, int) or isinstance(port, bool) or not 1 <= port <= 65535:
        raise DesktopIdentityError("Desktop identity callback port is invalid")
    return host, port


def _status_json(status: DesktopAuthStatus) -> dict[str, str | bool | None]:
    return {
        "state": status.state,
        "status": status.status,
        "provider_id": status.provider_id,
        "session_id": status.session_id,
        "principal_id": status.principal_id,
        "tenant_id": status.tenant_id,
        "display_identity": status.display_identity,
        "li_founder": status.li_founder,
    }


def _required_string(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise TypeError(f"{key} must be a non-empty string")
    return value.strip()


def _single_query(query: dict[str, list[str]], key: str) -> str:
    values = query.get(key, [])
    if len(values) != 1 or not values[0]:
        raise ValueError(f"{key} query parameter is required exactly once")
    return values[0]
