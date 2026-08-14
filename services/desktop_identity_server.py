"""Loopback HTTP boundary for ILAIOS Desktop human identity and sessions."""

from __future__ import annotations

import hmac
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, cast
from urllib.parse import parse_qs, urlparse

import requests

from services.desktop_oidc import (
    DesktopAuthStatus,
    DesktopIdentityError,
    DesktopOIDCService,
)


class DesktopIdentityHTTPServer(ThreadingHTTPServer):
    """Human identity adapter; execution authority remains in the control plane."""

    daemon_threads = True

    def __init__(
        self,
        server_address: tuple[str, int],
        *,
        bearer_token: str,
        control_plane_base_url: str,
        identity: DesktopOIDCService | None,
    ) -> None:
        if not bearer_token:
            raise DesktopIdentityError("Desktop identity transport token is required")
        super().__init__(server_address, DesktopIdentityRequestHandler)
        self.bearer_token = bearer_token
        self.control_plane_base_url = control_plane_base_url.rstrip("/")
        self.identity = identity
        self.http = requests.Session()


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
            self._send_error(HTTPStatus.NOT_FOUND, "unknown endpoint")
        except DesktopIdentityError as error:
            self._send_error(HTTPStatus.UNAUTHORIZED, str(error))
        except ValueError as error:
            self._send_error(HTTPStatus.BAD_REQUEST, str(error))

    def do_POST(self) -> None:
        try:
            self._authenticate_transport()
            body = self._read_json()
            path = urlparse(self.path).path
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
            if path == "/v1/desktop/intent":
                self._submit_authenticated_intent(body)
                return
            self._send_error(HTTPStatus.NOT_FOUND, "unknown endpoint")
        except DesktopIdentityError as error:
            self._send_error(HTTPStatus.UNAUTHORIZED, str(error))
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

    def _submit_authenticated_intent(self, body: dict[str, Any]) -> None:
        identity = self._require_identity()
        session_id = self.headers.get("X-ILAIOS-Session", "").strip()
        if not session_id:
            raise DesktopIdentityError("Desktop session is required")
        session = identity.validate_session(session_id)
        objective = _required_string(body, "objective")
        if len(objective) > 20_000:
            raise ValueError("objective exceeds Desktop input limit")
        headers = {
            "Authorization": f"Bearer {self.server.bearer_token}",
            "Accept": "application/json",
        }
        try:
            goal_response = self.server.http.post(
                f"{self.server.control_plane_base_url}/v1/goals",
                json={"objective": objective},
                headers=headers,
                timeout=5,
            )
            goal_response.raise_for_status()
            goal = goal_response.json()
            if not isinstance(goal, dict) or not isinstance(goal.get("goal_id"), str):
                raise DesktopIdentityError("control plane returned malformed goal")
            job_response = self.server.http.post(
                f"{self.server.control_plane_base_url}/v1/jobs",
                json={"goal_id": goal["goal_id"]},
                headers=headers,
                timeout=5,
            )
            job_response.raise_for_status()
            job = job_response.json()
        except (requests.RequestException, ValueError) as error:
            raise DesktopIdentityError(
                "authoritative control-plane intent submission failed"
            ) from error
        if (
            not isinstance(job, dict)
            or not isinstance(job.get("job_id"), str)
            or not isinstance(job.get("state"), str)
        ):
            raise DesktopIdentityError("control plane returned malformed job")
        self._send_json(
            HTTPStatus.CREATED,
            {
                "goal_id": goal["goal_id"],
                "job_id": job["job_id"],
                "state": job["state"],
                "principal_id": session.principal_id,
                "tenant_id": session.tenant_id,
            },
        )

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

    def _read_json(self) -> dict[str, Any]:
        raw_length = self.headers.get("Content-Length")
        if raw_length is None:
            raise ValueError("Content-Length is required")
        length = int(raw_length)
        if length < 1 or length > 1_048_576:
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


def _server_endpoint(address: tuple[str | bytes, int]) -> tuple[str, int]:
    host, port = address
    if not isinstance(host, str):
        raise DesktopIdentityError("Desktop identity callback host must be text")
    if host not in {"127.0.0.1", "localhost", "::1"}:
        raise DesktopIdentityError("Desktop identity callback must remain loopback")
    if not isinstance(port, int) or isinstance(port, bool) or not 1 <= port <= 65535:
        raise DesktopIdentityError("Desktop identity callback port is invalid")
    return host, port


def _status_json(status: DesktopAuthStatus) -> dict[str, str | None]:
    return {
        "state": status.state,
        "status": status.status,
        "provider_id": status.provider_id,
        "session_id": status.session_id,
        "principal_id": status.principal_id,
        "tenant_id": status.tenant_id,
        "display_identity": status.display_identity,
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