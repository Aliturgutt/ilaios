"""Additional P0 proofs for provider health and conservative cost accounting."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from services.ai_governance import (
    GovernanceError,
    ModelProviderRegistry,
    ModelRecord,
    ProviderRecord,
    Scope,
    ScopeKind,
    UsageGovernor,
    UsageLimits,
    UsageRequest,
)

NOW = datetime(2026, 8, 18, 10, 0, tzinfo=timezone.utc)
TENANT = Scope(ScopeKind.TENANT, "tenant-health")


def _governor(*, threshold: int = 2) -> UsageGovernor:
    registry = ModelProviderRegistry()
    registry.register_provider(ProviderRecord("provider-a", "adapter"))
    registry.register_model(
        ModelRecord(
            "model-a",
            "provider-a",
            frozenset({"text"}),
            4096,
            1024,
            input_cost_per_million=Decimal("1"),
            output_cost_per_million=Decimal("2"),
        )
    )
    limits = UsageLimits(
        4096,
        1024,
        10,
        2,
        Decimal("10"),
        Decimal("100"),
        Decimal("100"),
        Decimal("100"),
        max_retries=2,
        max_retry_cost=Decimal("2"),
    )
    return UsageGovernor(
        registry,
        {TENANT: limits},
        circuit_failure_threshold=threshold,
        circuit_cooldown=timedelta(minutes=1),
    )


def _request(request_id: str, cost: Decimal) -> UsageRequest:
    return UsageRequest(
        request_id,
        "tenant-health",
        (TENANT,),
        "model-a",
        100,
        50,
        cost,
    )


def test_reserved_cost_reconciles_down_to_observed_cost_once() -> None:
    governor = _governor()
    evidence = governor.admit(_request("r1", Decimal("1.50")), NOW)
    assert governor.usage_snapshot(TENANT, NOW)["daily_cost"] == "1.50"
    governor.reconcile_cost(evidence, Decimal("0.40"))
    governor.complete(evidence)
    snapshot = governor.usage_snapshot(TENANT, NOW)
    assert snapshot["daily_cost"] == "0.40"
    assert snapshot["monthly_cost"] == "0.40"
    assert snapshot["daily_active"] == 0
    with pytest.raises(GovernanceError, match="already reconciled"):
        governor.reconcile_cost(evidence, Decimal("0.30"))


def test_actual_cost_cannot_exceed_reserved_budget() -> None:
    governor = _governor()
    evidence = governor.admit(_request("r1", Decimal("0.50")), NOW)
    with pytest.raises(GovernanceError, match="exceeded reserved"):
        governor.reconcile_cost(evidence, Decimal("0.51"))
    governor.complete(evidence)


def test_provider_health_opens_on_threshold_and_success_recovers() -> None:
    governor = _governor(threshold=2)
    assert governor.provider_health("provider-a", NOW)["circuit"] == "closed"
    governor.record_provider_failure("provider-a", NOW)
    assert governor.provider_health("provider-a", NOW)["recent_failures"] == 1
    governor.record_provider_failure("provider-a", NOW)
    opened = governor.provider_health("provider-a", NOW)
    assert opened["circuit"] == "open"
    assert opened["open_until"] is not None

    later = NOW + timedelta(minutes=2)
    # A successful post-cooldown probe resets the transient failure history.
    governor.record_provider_success("provider-a", later)
    healthy = governor.provider_health("provider-a", later)
    assert healthy["circuit"] == "closed"
    assert healthy["recent_failures"] == 0
