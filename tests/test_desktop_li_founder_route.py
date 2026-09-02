from __future__ import annotations

import http.client
import json
import threading
from datetime import UTC, datetime, timedelta
from typing import cast

from services.desktop_identity_server_core import DesktopIdentityHTTPServer
from services.desktop_oidc import DesktopOIDCService
from services.execution_coordinator import ExecutionCoordinator
from services.identity import Session

_NOW = datetime(2026, 9, 2, 0, 0, tzinfo=UTC)


class _Identity:
    def __init__(self, *, founder: bool) -> None:
        self.founder = founder
        self.session = Session(
            session_id="desktop-session",
            principal_id="usr_founder",
            tenant_id="tnt_founder",
            expires_at=_NOW + timedelta(hours=1),
        )

    def validate_session(self, session_id: str) -> Session:
        assert session_id == self.session.session_id
        return self.session

    def is_li_founder_session(self, session_id: str) -> bool:
        assert session_id == self.session.session_id
        return self.founder


class _Coordinator:
    def recover_stale(self, **_kwargs: object) -> tuple[object, ...]:
        return ()


def _request(founder: bool) -> tuple[int, dict[str, object]]:
    identity = cast(DesktopOIDCService, _Identity(founder=founder))
    server = DesktopIdentityHTTPServer(
        ("127.0.0.1", 0),
        bearer_token="transport-token",
        identity=identity,
        coordinator=cast(ExecutionCoordinator, _Coordinator()),
    )
    host, port = server.server_address[:2]
    assert isinstance(host, str)
    worker = threading.Thread(target=server.handle_request, daemon=True)
    worker.start()
    try:
        connection = http.client.HTTPConnection(host, port, timeout=5)
        connection.request(
            "GET",
            "/v1/li/state",
            headers={
                "Authorization": "Bearer transport-token",
                "X-ILAIOS-Session": "desktop-session",
            },
        )
        response = connection.getresponse()
        body = response.read()
        connection.close()
        worker.join(timeout=5)
        return response.status, json.loads(body)
    finally:
        server.server_close()


def test_desktop_li_state_is_available_only_for_bound_founder_session() -> None:
    status, payload = _request(True)

    assert status == 200
    assert payload == {
        "founder_operator": True,
        "name": "Li",
        "source": "canonical_desktop_session",
        "tenant_id": "tnt_founder",
        "user_id": "usr_founder",
    }


def test_desktop_li_state_fails_closed_for_nonfounder_session() -> None:
    status, payload = _request(False)

    assert status == 403
    assert payload == {"error": "request denied"}
