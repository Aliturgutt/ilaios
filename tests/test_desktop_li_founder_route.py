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
        self.memories: list[dict[str, object]] = [
            {
                "memory_id": "li_mem_existing",
                "kind": "semantic",
                "content": "Founder memory",
                "source": "desktop",
                "confidence": 1.0,
                "sensitivity": "private",
                "created_at": "2026-09-02T00:00:00+00:00",
            }
        ]

    def validate_session(self, session_id: str) -> Session:
        assert session_id == self.session.session_id
        return self.session

    def is_li_founder_session(self, session_id: str) -> bool:
        assert session_id == self.session.session_id
        return self.founder

    def list_li_memories(
        self,
        session_id: str,
        now: datetime | None = None,
    ) -> tuple[dict[str, object], ...]:
        assert session_id == self.session.session_id
        assert now is None
        return tuple(self.memories)

    def remember_li_memory(
        self,
        session_id: str,
        *,
        kind: str,
        content: str,
        now: datetime | None = None,
    ) -> dict[str, object]:
        assert session_id == self.session.session_id
        assert now is None
        record: dict[str, object] = {
            "memory_id": "li_mem_new",
            "kind": kind,
            "content": content,
            "source": "desktop",
            "confidence": 1.0,
            "sensitivity": "private",
            "created_at": "2026-09-02T00:01:00+00:00",
        }
        self.memories.insert(0, record)
        return record


class _Coordinator:
    def recover_stale(self, **_kwargs: object) -> tuple[object, ...]:
        return ()


def _request(
    founder: bool,
    *,
    method: str = "GET",
    path: str = "/v1/li/state",
    document: dict[str, object] | None = None,
) -> tuple[int, dict[str, object]]:
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
        body = None if document is None else json.dumps(document)
        headers = {
            "Authorization": "Bearer transport-token",
            "X-ILAIOS-Session": "desktop-session",
        }
        if body is not None:
            headers["Content-Type"] = "application/json"
        connection.request(method, path, body=body, headers=headers)
        response = connection.getresponse()
        response_body = response.read()
        connection.close()
        worker.join(timeout=5)
        return response.status, json.loads(response_body)
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


def test_desktop_li_memory_routes_are_founder_only_and_persistent_proxy() -> None:
    list_status, listed = _request(True, path="/v1/li/memories")
    write_status, stored = _request(
        True,
        method="POST",
        path="/v1/li/memories",
        document={"kind": "working", "content": "Remember this"},
    )
    denied_status, denied = _request(False, path="/v1/li/memories")

    assert list_status == 200
    raw_memories = listed["memories"]
    assert isinstance(raw_memories, list)
    first_memory = raw_memories[0]
    assert isinstance(first_memory, dict)
    assert first_memory["content"] == "Founder memory"
    assert write_status == 201
    assert stored["content"] == "Remember this"
    assert denied_status == 403
    assert denied == {"error": "request denied"}
