"""Loopback Desktop identity broker contract tests."""

from __future__ import annotations

import threading
from datetime import datetime, timedelta, timezone
from typing import cast

import requests

from services.desktop_identity_server import DesktopIdentityHTTPServer
from services.desktop_oidc import DesktopOIDCService
from services.execution_coordinator import ExecutionCoordinator
from services.identity import Session


class _FakeIdentity:
    def __init__(self, session: Session) -> None:
        self._session = session

    def validate_session(self, session_id: str) -> Session:
        if session_id != self._session.session_id:
            raise AssertionError("unexpected session")
        return self._session


class _FakeCoordinator:
    def __init__(self, session: Session) -> None:
        self._session = session
        self.resumed = threading.Event()
        self.decisions: list[tuple[str, str, str, str]] = []

    def get(self, request_id: str) -> dict[str, object]:
        assert request_id == "exec-1"
        return {
            "request_id": request_id,
            "principal_id": self._session.principal_id,
            "tenant_id": self._session.tenant_id,
            "execution_status": "PENDING_APPROVAL",
        }

    def decide(
        self,
        request_id: str,
        *,
        approver_id: str,
        tenant_id: str,
        decision: str,
        now: datetime,
    ) -> str:
        assert now.tzinfo is not None
        self.decisions.append((request_id, approver_id, tenant_id, decision))
        return "DENIED" if decision == "denied" else "APPROVED"

    def resume(
        self,
        request_id: str,
        *,
        token: str,
        now: datetime,
    ) -> dict[str, object]:
        assert request_id == "exec-1"
        assert token == "transport-token"
        assert now.tzinfo is not None
        self.resumed.set()
        return {"accepted": True}


def _serve(
    session: Session,
) -> tuple[DesktopIdentityHTTPServer, _FakeCoordinator, threading.Thread, str]:
    identity = _FakeIdentity(session)
    coordinator = _FakeCoordinator(session)
    server = DesktopIdentityHTTPServer(
        ("127.0.0.1", 0),
        bearer_token="transport-token",
        identity=cast(DesktopOIDCService, identity),
        coordinator=cast(ExecutionCoordinator, coordinator),
    )
    host, port = server.server_address[:2]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, coordinator, thread, f"http://{host}:{port}"


def _headers(session: Session) -> dict[str, str]:
    return {
        "Authorization": "Bearer transport-token",
        "X-ILAIOS-Session": session.session_id,
    }


def test_execution_resume_returns_202_and_runs_after_session_ownership_check() -> None:
    now = datetime.now(timezone.utc)
    session = Session(
        "session-1",
        "principal-1",
        "tenant-1",
        now + timedelta(minutes=10),
    )
    server, coordinator, thread, base_url = _serve(session)
    try:
        response = requests.post(
            f"{base_url}/v1/execution/resume",
            headers=_headers(session),
            json={"request_id": "exec-1"},
            timeout=2,
        )
        assert response.status_code == 202
        assert response.json() == {
            "execution_status": "RESUME_REQUESTED",
            "request_id": "exec-1",
        }
        assert coordinator.resumed.wait(timeout=2)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_execution_approval_ignores_spoofed_approver_and_uses_session_principal() -> None:
    now = datetime.now(timezone.utc)
    session = Session(
        "approver-session",
        "verified-approver",
        "tenant-1",
        now + timedelta(minutes=10),
    )
    server, coordinator, thread, base_url = _serve(session)
    try:
        response = requests.post(
            f"{base_url}/v1/execution/decision",
            headers=_headers(session),
            json={
                "request_id": "exec-1",
                "decision": "approved",
                "approver_id": "spoofed-client-approver",
                "tenant_id": "spoofed-client-tenant",
            },
            timeout=2,
        )
        assert response.status_code == 202
        assert response.json() == {
            "execution_status": "EXECUTION_STARTED",
            "request_id": "exec-1",
        }
        assert coordinator.decisions == [
            ("exec-1", "verified-approver", "tenant-1", "approved")
        ]
        assert coordinator.resumed.wait(timeout=2)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_execution_denial_is_terminal_and_does_not_start_background_execution() -> None:
    now = datetime.now(timezone.utc)
    session = Session(
        "approver-session",
        "verified-approver",
        "tenant-1",
        now + timedelta(minutes=10),
    )
    server, coordinator, thread, base_url = _serve(session)
    try:
        response = requests.post(
            f"{base_url}/v1/execution/decision",
            headers=_headers(session),
            json={"request_id": "exec-1", "decision": "denied"},
            timeout=2,
        )
        assert response.status_code == 200
        assert response.json() == {
            "execution_status": "DENIED",
            "request_id": "exec-1",
        }
        assert coordinator.decisions == [
            ("exec-1", "verified-approver", "tenant-1", "denied")
        ]
        assert not coordinator.resumed.wait(timeout=0.1)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
