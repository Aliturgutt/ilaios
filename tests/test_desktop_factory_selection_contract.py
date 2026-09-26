"""Selected factory admission regression tests: no implicit reroute or side effects."""
from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Callable, TypeVar, cast
from unittest.mock import Mock

import pytest

from services.capability_registry import CAPABILITIES, CapabilityDefinition
from services.desktop_identity_server import DesktopIdentityRequestHandler
from services.execution_coordinator import ExecutionCoordinatorError, _ADAPTER_DESCRIPTORS

FACTORIES = tuple(item for item in CAPABILITIES if item.domain == "factory")
F = TypeVar("F", bound=Callable[..., Any])


def factory_cases(function: F) -> F:
    return cast(F, pytest.mark.parametrize("factory", FACTORIES, ids=lambda x: x.capability_id)(function))


def _handler(*, actual_id: str | None = None, status: str = "BLOCKED") -> tuple[DesktopIdentityRequestHandler, Mock]:
    handler = object.__new__(DesktopIdentityRequestHandler)
    coordinator = Mock()
    coordinator.prepare.return_value = {
        "execution_status": status,
        "plan": {"capabilities": [actual_id] if actual_id else []},
        "blocker_code": "ADAPTER_UNAVAILABLE" if status == "BLOCKED" else None,
    }
    object.__setattr__(handler, "server", SimpleNamespace(coordinator=coordinator, bearer_token="test"))
    object.__setattr__(handler, "_authenticated_session", Mock(return_value=SimpleNamespace(principal_id="owner", tenant_id="tenant")))
    object.__setattr__(handler, "_start_execution", Mock())
    object.__setattr__(handler, "_send_json", Mock())
    return handler, coordinator


@factory_cases
def test_each_canonical_factory_returns_actual_route_and_does_not_start_blocked_work(factory: CapabilityDefinition) -> None:
    handler, coordinator = _handler(actual_id=factory.capability_id)
    handler._submit_authenticated_intent({"objective": factory.display_name, "selected_factory_id": factory.capability_id})
    response = cast(Mock, handler._send_json).call_args.args[1]
    assert response["selected_factory_id"] == factory.capability_id
    assert response["resolved_factory_id"] == factory.capability_id
    assert response["execution_status"] == "BLOCKED"
    cast(Mock, handler._start_execution).assert_not_called()
    coordinator.prepare.assert_called_once()


@factory_cases
def test_each_factory_rejects_conflicting_objective_before_prepare(factory: CapabilityDefinition) -> None:
    other = next(x for x in FACTORIES if x.capability_id != factory.capability_id)
    handler, coordinator = _handler(actual_id=factory.capability_id)
    with pytest.raises(ValueError, match="conflicts"):
        handler._submit_authenticated_intent({"objective": other.display_name, "selected_factory_id": factory.capability_id})
    coordinator.prepare.assert_not_called()
    cast(Mock, handler._start_execution).assert_not_called()


@factory_cases
def test_each_factory_rejects_wrong_actual_route_before_start(factory: CapabilityDefinition) -> None:
    other = next(x for x in FACTORIES if x.capability_id != factory.capability_id)
    handler, _ = _handler(actual_id=other.capability_id, status="ADMITTED")
    with pytest.raises(ExecutionCoordinatorError, match="actual route differs"):
        handler._submit_authenticated_intent({"objective": factory.display_name, "selected_factory_id": factory.capability_id})
    cast(Mock, handler._start_execution).assert_not_called()
    cast(Mock, handler._send_json).assert_not_called()


@factory_cases
def test_each_factory_rejects_unauthenticated_session_before_prepare(factory: CapabilityDefinition) -> None:
    handler, coordinator = _handler(actual_id=factory.capability_id)
    cast(Mock, handler._authenticated_session).side_effect = PermissionError("session denied")
    with pytest.raises(PermissionError, match="session denied"):
        handler._submit_authenticated_intent({"objective": factory.display_name, "selected_factory_id": factory.capability_id})
    coordinator.prepare.assert_not_called()
    cast(Mock, handler._start_execution).assert_not_called()


@factory_cases
def test_each_factory_adapter_maturity_is_reported_not_assumed(factory: CapabilityDefinition) -> None:
    descriptor = _ADAPTER_DESCRIPTORS[factory.capability_id]
    assert descriptor.maturity.value in {"VERIFIED_FINISHED_PRODUCT_ADAPTER", "IMPLEMENTED_NOT_EXECUTABLE", "REVIEW_ONLY"}
    if descriptor.maturity.value != "VERIFIED_FINISHED_PRODUCT_ADAPTER":
        assert descriptor.blocker_code


def test_rejects_noncanonical_factory_before_prepare() -> None:
    handler, coordinator = _handler()
    with pytest.raises(ValueError, match="canonical factory"):
        handler._submit_authenticated_intent({"objective": "Web Factory", "selected_factory_id": "ilaios.capability.identity-tenant"})
    coordinator.prepare.assert_not_called()


@factory_cases
def test_each_factory_rejects_multi_factory_objective_before_prepare(factory: CapabilityDefinition) -> None:
    other = next(x for x in FACTORIES if x.capability_id != factory.capability_id)
    handler, coordinator = _handler(actual_id=factory.capability_id)
    with pytest.raises(ValueError, match="conflicts"):
        handler._submit_authenticated_intent({"objective": factory.display_name + " and " + other.display_name, "selected_factory_id": factory.capability_id})
    coordinator.prepare.assert_not_called()


@factory_cases
def test_each_factory_returns_blocker_from_coordinator(factory: CapabilityDefinition) -> None:
    descriptor = _ADAPTER_DESCRIPTORS[factory.capability_id]
    if descriptor.maturity.value == "VERIFIED_FINISHED_PRODUCT_ADAPTER":
        pytest.skip("verified adapter has no maturity blocker")
    handler, coordinator = _handler(actual_id=factory.capability_id)
    coordinator.prepare.return_value["blocker_code"] = descriptor.blocker_code
    handler._submit_authenticated_intent({"objective": factory.display_name, "selected_factory_id": factory.capability_id})
    response = cast(Mock, handler._send_json).call_args.args[1]
    assert response["execution_status"] == "BLOCKED"
    assert response["blocker_code"] == descriptor.blocker_code
    cast(Mock, handler._start_execution).assert_not_called()
