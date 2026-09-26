"""Loopback HTTP admission contract for nine explicit Desktop factory selections."""
from __future__ import annotations

from contextlib import contextmanager
from collections.abc import Iterator
from pathlib import Path
from threading import Thread
from types import SimpleNamespace
from typing import Any, Callable, TypeVar, cast
from unittest.mock import Mock

import pytest
import requests

from services.capability_registry import CAPABILITIES, CapabilityDefinition
from services.desktop_identity_server import DesktopIdentityHTTPServer
from services.desktop_oidc import DesktopIdentityError

FACTORIES = tuple(item for item in CAPABILITIES if item.domain == "factory")
F = TypeVar("F", bound=Callable[..., Any])


def factory_cases(function: F) -> F:
    return cast(F, pytest.mark.parametrize("factory", FACTORIES, ids=lambda x: x.capability_id)(function))


@contextmanager
def _server(*, actual_id: str | None = None, status: str = "BLOCKED") -> Iterator[tuple[str, Mock, Mock, Mock]]:
    identity = Mock()
    identity.validate_session.return_value = SimpleNamespace(principal_id="user-1", tenant_id="tenant-1")
    coordinator = Mock()
    coordinator.prepare.return_value = {
        "execution_status": status,
        "plan": {"capabilities": [actual_id] if actual_id else []},
        "blocker_code": "ADAPTER_NOT_AVAILABLE",
    }
    server = DesktopIdentityHTTPServer(
        ("127.0.0.1", 0), bearer_token="transport-secret", identity=identity,
        coordinator=coordinator,
    )
    start_spy = Mock()
    setattr(server.RequestHandlerClass, "_start_execution", start_spy)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}/v1/desktop/intent", identity, coordinator, start_spy
    finally:
        server.shutdown()
        thread.join(timeout=3)
        server.server_close()


def _post(url: str, factory: CapabilityDefinition, *, bearer: str = "transport-secret", session: str = "valid", objective: str | None = None) -> requests.Response:
    return requests.post(url, json={"objective": objective or factory.display_name, "selected_factory_id": factory.capability_id}, headers={"Authorization": f"Bearer {bearer}", "X-ILAIOS-Session": session}, timeout=3)


@factory_cases
def test_http_each_factory_returns_actual_blocked_route(factory: CapabilityDefinition) -> None:
    with _server(actual_id=factory.capability_id) as (url, identity, coordinator, start):
        response = _post(url, factory)
        assert response.status_code == 201, response.text
        payload = response.json()
        assert payload["selected_factory_id"] == payload["resolved_factory_id"] == factory.capability_id
        assert payload["execution_status"] == "BLOCKED"
        assert payload["blocker_code"] == "ADAPTER_NOT_AVAILABLE"
        identity.validate_session.assert_called_once_with("valid")
        coordinator.prepare.assert_called_once()
        start.assert_not_called()


@factory_cases
def test_http_each_factory_rejects_conflicting_text_without_prepare(factory: CapabilityDefinition) -> None:
    other = next(x for x in FACTORIES if x.capability_id != factory.capability_id)
    with _server(actual_id=factory.capability_id) as (url, _identity, coordinator, start):
        response = _post(url, factory, objective=other.display_name)
        assert response.status_code == 400
        coordinator.prepare.assert_not_called()
        start.assert_not_called()


@factory_cases
def test_http_each_factory_rejects_wrong_actual_route_before_execution(factory: CapabilityDefinition) -> None:
    other = next(x for x in FACTORIES if x.capability_id != factory.capability_id)
    with _server(actual_id=other.capability_id, status="ADMITTED") as (url, _identity, coordinator, start):
        response = _post(url, factory)
        assert response.status_code == 409
        coordinator.prepare.assert_called_once()
        start.assert_not_called()


@factory_cases
def test_http_each_factory_requires_transport_auth(factory: CapabilityDefinition) -> None:
    with _server(actual_id=factory.capability_id) as (url, identity, coordinator, start):
        response = _post(url, factory, bearer="wrong")
        assert response.status_code == 401
        identity.validate_session.assert_not_called()
        coordinator.prepare.assert_not_called()
        start.assert_not_called()


@factory_cases
def test_http_each_factory_rejects_invalid_session(factory: CapabilityDefinition) -> None:
    with _server(actual_id=factory.capability_id) as (url, identity, coordinator, start):
        identity.validate_session.side_effect = DesktopIdentityError("invalid session")
        response = _post(url, factory, session="expired")
        assert response.status_code == 401
        coordinator.prepare.assert_not_called()
        start.assert_not_called()


def test_real_coordinator_blocks_unavailable_web_adapter_over_http(tmp_path: Path) -> None:
    from tests.test_execution_coordinator import _coordinator

    coordinator, governance, _, _, _ = _coordinator(tmp_path)
    web = next(x for x in FACTORIES if x.capability_id == "ilaios.capability.web-factory")
    identity = Mock()
    identity.validate_session.return_value = SimpleNamespace(principal_id="user-1", tenant_id="tenant-1")
    real_server = DesktopIdentityHTTPServer(
        ("127.0.0.1", 0), bearer_token="token", identity=identity,
        coordinator=coordinator,
    )
    real_start_spy = Mock()
    setattr(real_server.RequestHandlerClass, "_start_execution", real_start_spy)
    thread = Thread(target=real_server.serve_forever, daemon=True)
    thread.start()
    try:
        real_url = f"http://127.0.0.1:{real_server.server_address[1]}/v1/desktop/intent"
        response = _post(real_url, web, objective="Build a premium website for a furniture company", bearer="token")
        assert response.status_code == 201, response.text
        payload = response.json()
        assert payload["execution_status"] == "BLOCKED"
        assert payload["blocker_code"] == "GENERAL_PURPOSE_WEB_ADAPTER_UNAVAILABLE"
        assert payload["resolved_factory_id"] == web.capability_id
        assert governance.state()["work"] == []
        real_start_spy.assert_not_called()
    finally:
        real_server.shutdown()
        thread.join(timeout=3)
        real_server.server_close()
