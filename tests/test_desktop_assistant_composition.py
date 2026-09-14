from __future__ import annotations

import http.client
import json
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, cast

from services.assistant_conversation_runtime import (
    AssistantConversationError,
    AssistantConversationResult,
    AssistantConversationRuntime,
)
from services.company_knowledge_desktop import TenantCompanyKnowledgeRegistry
from services.desktop_assistant_composition import (
    AssistantRuntimeCompanyKnowledgeDesktopIdentityHTTPServer,
)
from services.desktop_oidc import DesktopIdentityError, DesktopOIDCService
from services.execution_coordinator import ExecutionCoordinator
from services.identity import Session
from services.source_media import SourceMediaStore


class _Identity:
    def validate_session(self, session_id: str) -> Session:
        if session_id != "user":
            raise DesktopIdentityError("Session denied")
        return Session(
            session_id="user",
            principal_id="usr_user",
            tenant_id="tnt_user",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )

    def is_li_founder_session(self, session_id: str) -> bool:
        return False


class _Coordinator:
    def __init__(self, root: Path) -> None:
        self._database_path = root / "execution-coordinator.sqlite3"


class _Runtime:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.calls: list[dict[str, object]] = []

    def complete(self, **kwargs: object) -> AssistantConversationResult:
        self.calls.append(dict(kwargs))
        if self.fail:
            raise AssistantConversationError("provider failed")
        assert kwargs["tenant_id"] == "tnt_user"
        assert kwargs["text"] == "Hello governed Assistant"
        assert kwargs["locale"] == "en"
        request_id = kwargs["request_id"]
        assert isinstance(request_id, str)
        assert request_id.startswith("desktop-assistant:")
        return AssistantConversationResult(
            text="Governed response",
            model_id="free/model",
            provider_id="openrouter",
            actual_cost_usd="0",
            evidence_digest="a" * 64,
        )


class _Client:
    def __init__(self, root: Path, runtime: _Runtime) -> None:
        source_media = SourceMediaStore(
            root / "source-media.sqlite3",
            root / "source-media" / "blobs",
        )
        company_knowledge = TenantCompanyKnowledgeRegistry(root / "company-knowledge")
        self.server = AssistantRuntimeCompanyKnowledgeDesktopIdentityHTTPServer(
            ("127.0.0.1", 0),
            bearer_token="transport",
            identity=cast(DesktopOIDCService, _Identity()),
            coordinator=cast(ExecutionCoordinator, _Coordinator(root)),
            source_media=source_media,
            company_knowledge=company_knowledge,
            assistant_runtime=cast(AssistantConversationRuntime, runtime),
        )
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def close(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def call(self, body: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        connection = http.client.HTTPConnection(
            str(self.server.server_address[0]),
            self.server.server_address[1],
            timeout=5,
        )
        connection.request(
            "POST",
            "/v1/assistant",
            json.dumps(body),
            {
                "Authorization": "Bearer transport",
                "X-ILAIOS-Session": "user",
                "Content-Type": "application/json",
            },
        )
        response = connection.getresponse()
        payload = json.loads(response.read())
        connection.close()
        return response.status, payload


def _create(client: _Client) -> str:
    status, payload = client.call({"operation": "create"})
    assert status == 200
    return cast(str, payload["conversation"]["conversation_id"])


def _message(conversation_id: str) -> dict[str, Any]:
    return {
        "operation": "send",
        "conversation_id": conversation_id,
        "text": "Hello governed Assistant",
        "locale": "en",
        "version": 0,
        "message_id": "message-1",
    }


def test_composed_runtime_serves_authenticated_desktop_send(tmp_path: Path) -> None:
    runtime = _Runtime()
    client = _Client(tmp_path, runtime)
    try:
        conversation_id = _create(client)
        status, payload = client.call(_message(conversation_id))
        assert status == 200
        answer = payload["conversation"]["messages"][1]
        assert answer["text"] == "Governed response"
        assert answer["response_class"] == "MODEL_RESPONSE"
        assert answer["model_status"] == "GOVERNED_ZERO_COST"
        assert answer["cost_state"] == "ZERO_VERIFIED"
        assert answer["live"] is True
        assert answer["provenance"][0]["evidence_id"] == "a" * 64
        assert len(runtime.calls) == 1
    finally:
        client.close()


def test_provider_failure_is_503_and_does_not_commit_conversation(tmp_path: Path) -> None:
    runtime = _Runtime(fail=True)
    client = _Client(tmp_path, runtime)
    try:
        conversation_id = _create(client)
        status, payload = client.call(_message(conversation_id))
        assert status == 503
        assert payload == {"error": "Assistant governed model unavailable"}
        status, loaded = client.call(
            {"operation": "get", "conversation_id": conversation_id}
        )
        assert status == 200
        assert loaded["conversation"]["version"] == 0
        assert loaded["conversation"]["messages"] == []
        assert len(runtime.calls) == 1
    finally:
        client.close()


def test_unconfigured_runtime_preserves_fail_closed_fallback(tmp_path: Path) -> None:
    source_media = SourceMediaStore(
        tmp_path / "source-media.sqlite3",
        tmp_path / "source-media" / "blobs",
    )
    server = AssistantRuntimeCompanyKnowledgeDesktopIdentityHTTPServer(
        ("127.0.0.1", 0),
        bearer_token="transport",
        identity=cast(DesktopOIDCService, _Identity()),
        coordinator=cast(ExecutionCoordinator, _Coordinator(tmp_path)),
        source_media=source_media,
        company_knowledge=TenantCompanyKnowledgeRegistry(tmp_path / "company-knowledge"),
        assistant_runtime=None,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    client = _Client.__new__(_Client)
    client.server = server
    client.thread = thread
    try:
        conversation_id = _create(client)
        status, payload = client.call(_message(conversation_id))
        assert status == 200
        answer = payload["conversation"]["messages"][1]
        assert answer["model_status"] == "ASSISTANT_UNAVAILABLE"
        assert answer["live"] is False
    finally:
        client.close()
