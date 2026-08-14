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

    def get(self, request_id: str) -> dict[str, object]:
        assert request_id == "exec-1"
        return {
            "request_id": request_id,
            "principal_id": self._session.principal_id,
            "tenant_id": self._session.tenant_id,
            "execution_status": "PENDING_APPROVAL",
        }

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


def test_execution_resume_returns_202_and_runs_after_session_ownership_check() -> None:
    now = datetime.now(timezone.utc)
    session = Session(
        "session-1",
        "principal-1",
        "tenant-1",
        now + timedelta(minutes=10),
    )
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
    try:
        response = requests.post(
            f"http://{host}:{port}/v1/execution/resume",
            headers={
                "Authorization": "Bearer transport-token",
                "X-ILAIOS-Session": session.session_id,
            },
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
