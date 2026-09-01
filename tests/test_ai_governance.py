"""Exact proofs for GOV.I01 AI/model/token/cost governance."""

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from services.ai_governance import (
    GovernanceError,
    ModelProviderRegistry,
    ModelRecord,
    ProviderRecord,
    RoutingPolicy,
    Scope,
    ScopeKind,
    UsageGovernor,
    UsageLimits,
    UsageRequest,
    route_model,
)

NOW = datetime(2026, 8, 9, tzinfo=timezone.utc)


def _registry() -> ModelProviderRegistry:
    registry = ModelProviderRegistry()
    registry.register_provider(ProviderRecord("portable-a", "adapter-a"))
    registry.register_provider(ProviderRecord("portable-b", "adapter-b"))
    registry.register_model(
        ModelRecord("model-a", "portable-a", frozenset({"text"}), 100, 40)
    )
    registry.register_model(
        ModelRecord("model-b", "portable-b", frozenset({"text"}), 200, 80)
    )
    return registry


def _limits() -> UsageLimits:
    return UsageLimits(
        80,
        40,
        2,
        1,
        Decimal(10),
        Decimal(20),
        Decimal(30),
        Decimal(60),
        max_retries=1,
        max_retry_cost=Decimal(2),
    )


def _request(
    request_id: str, scopes: tuple[Scope, ...], **overrides: object
) -> UsageRequest:
    values: dict[str, object] = {
        "request_id": request_id,
        "tenant_id": "tenant-a",
        "scopes": scopes,
        "model_id": "model-a",
        "input_tokens": 50,
        "output_tokens": 20,
        "estimated_cost": Decimal(8),
        "estimated_gpu_seconds": Decimal(5),
        "estimated_runtime_seconds": Decimal(10),
    }
    values.update(overrides)
    return UsageRequest(**values)  # type: ignore[arg-type]


def test_registry_routing_allow_deny_and_deterministic_fallback() -> None:
    registry = _registry()
    policy = RoutingPolicy(
        denied_models=frozenset({"model-a"}), fallback_order=("model-a", "model-b")
    )
    assert route_model(registry, policy, "text", "model-a").model_id == "model-b"
    with pytest.raises(GovernanceError, match="no model"):
        route_model(
            registry,
            RoutingPolicy(denied_providers=frozenset({"portable-a", "portable-b"})),
            "text",
        )


def test_all_scopes_enforced_warning_attribution_and_concurrency() -> None:
    scopes = tuple(Scope(kind, f"{kind.value}-a") for kind in ScopeKind)
    governor = UsageGovernor(_registry(), {scope: _limits() for scope in scopes})
    evidence = governor.admit(_request("r1", scopes), NOW)
    assert evidence.tenant_id == "tenant-a"
    assert evidence.provider_id == "portable-a"
    assert evidence.warnings == ("daily_cost_warning",)
    with pytest.raises(GovernanceError, match="concurrency"):
        governor.admit(_request("r2", scopes), NOW)
    governor.complete(evidence)
    assert governor.admit(_request("r2", scopes, estimated_cost=Decimal(2)), NOW)


def test_hard_ceilings_fail_closed() -> None:
    cases: tuple[tuple[dict[str, object], str], ...] = (
        ({"input_tokens": 81, "output_tokens": 0}, "input token"),
        ({"output_tokens": 41}, "output token"),
        ({"input_tokens": 80, "output_tokens": 30}, "context window"),
        ({"estimated_cost": Decimal(11)}, "daily cost"),
        ({"estimated_gpu_seconds": Decimal(31)}, "GPU"),
        ({"estimated_runtime_seconds": Decimal(61)}, "runtime"),
        ({"retry_number": 2}, "retry limit"),
        ({"retry_accumulated_cost": Decimal(3)}, "retry cost"),
    )
    for index, (overrides, message) in enumerate(cases):
        tenant = Scope(ScopeKind.TENANT, "tenant-a")
        governor = UsageGovernor(_registry(), {tenant: _limits()})
        with pytest.raises(GovernanceError, match=message):
            governor.admit(_request(f"r{index}", (tenant,), **overrides), NOW)


def test_missing_tenant_or_scope_policy_cannot_be_bypassed() -> None:
    user = Scope(ScopeKind.USER, "user-a")
    with pytest.raises(ValueError, match="tenant scope"):
        _request("r1", (user,))
    tenant = Scope(ScopeKind.TENANT, "tenant-a")
    governor = UsageGovernor(_registry(), {tenant: _limits()})
    with pytest.raises(GovernanceError, match="no configured limit"):
        governor.admit(_request("r1", (tenant, user)), NOW)


def test_duplicate_accounting_and_provider_circuit_breaker_fail_closed() -> None:
    tenant = Scope(ScopeKind.TENANT, "tenant-a")
    governor = UsageGovernor(
        _registry(), {tenant: _limits()}, circuit_failure_threshold=2
    )
    evidence = governor.admit(_request("r1", (tenant,), estimated_cost=Decimal(1)), NOW)
    governor.complete(evidence)
    with pytest.raises(GovernanceError, match="duplicate"):
        governor.admit(_request("r1", (tenant,), estimated_cost=Decimal(1)), NOW)
    governor.record_provider_failure("portable-a", NOW)
    governor.record_provider_failure("portable-a", NOW)
    with pytest.raises(GovernanceError, match="circuit"):
        governor.admit(_request("r2", (tenant,), estimated_cost=Decimal(1)), NOW)
