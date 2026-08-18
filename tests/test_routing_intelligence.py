"""Red-team proofs for ILAIOS routing intelligence beneath canonical routing."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from services.ai_governance import GovernanceError, ModelRecord, ProviderRecord, RoutingPolicy
from services.provider_catalog import ModelQualityRecord, ProviderCatalogSnapshot
from services.provider_state import (
    ProviderHealthState,
    ProviderQuotaState,
    ProviderRuntimeSnapshot,
)
from services.routing_intelligence import (
    RoutingIntelligenceEngine,
    RoutingIntelligenceRequest,
    RoutingScoreWeights,
    canonical_policy_from_evidence,
    route_via_canonical_authority,
)

NOW = datetime(2026, 8, 18, 10, 0, tzinfo=timezone.utc)


def _catalog() -> ProviderCatalogSnapshot:
    return ProviderCatalogSnapshot(
        "catalog-7",
        NOW,
        (
            ProviderRecord("provider-a", "adapter-a"),
            ProviderRecord("provider-b", "adapter-b"),
        ),
        (
            ModelRecord(
                "model-a",
                "provider-a",
                frozenset({"text.reasoning"}),
                128_000,
                8_000,
                input_cost_per_million=Decimal("4"),
                output_cost_per_million=Decimal("12"),
            ),
            ModelRecord(
                "model-b",
                "provider-b",
                frozenset({"text.reasoning"}),
                128_000,
                8_000,
                input_cost_per_million=Decimal("1"),
                output_cost_per_million=Decimal("3"),
            ),
        ),
        (
            ModelQualityRecord("model-a", Decimal("0.95")),
            ModelQualityRecord("model-b", Decimal("0.90")),
        ),
    )


def _state(
    *,
    a_circuit: bool = False,
    a_requests: int = 100,
    b_requests: int = 100,
    observed_at: datetime = NOW,
) -> ProviderRuntimeSnapshot:
    return ProviderRuntimeSnapshot(
        "state-9",
        observed_at,
        (
            ProviderHealthState(
                "provider-a", observed_at, Decimal("0.99"), 120, circuit_open=a_circuit
            ),
            ProviderHealthState("provider-b", observed_at, Decimal("0.97"), 180),
        ),
        (
            ProviderQuotaState(
                "provider-a",
                observed_at,
                remaining_requests=a_requests,
                remaining_tokens=1_000_000,
            ),
            ProviderQuotaState(
                "provider-b",
                observed_at,
                remaining_requests=b_requests,
                remaining_tokens=1_000_000,
            ),
        ),
    )


def _request() -> RoutingIntelligenceRequest:
    return RoutingIntelligenceRequest("text.reasoning", 4_000, 1_000)


def test_cost_weighted_ranking_is_deterministic_and_canonical_router_selects() -> None:
    engine = RoutingIntelligenceEngine(
        RoutingScoreWeights(
            cost=Decimal(1),
            latency=Decimal(0),
            reliability=Decimal(0),
            quality=Decimal(0),
            quota=Decimal(0),
        )
    )
    first = engine.evaluate(
        catalog=_catalog(),
        runtime_state=_state(),
        policy=RoutingPolicy(),
        request=_request(),
        now=NOW,
    )
    second = engine.evaluate(
        catalog=_catalog(),
        runtime_state=_state(),
        policy=RoutingPolicy(),
        request=_request(),
        now=NOW,
    )
    assert first == second
    assert first.ranked_model_ids == ("model-b", "model-a")
    registry = _catalog().build_registry()
    selected = route_via_canonical_authority(registry, RoutingPolicy(), first)
    assert selected.model_id == "model-b"


def test_unhealthy_or_exhausted_provider_is_excluded_before_canonical_route() -> None:
    evidence = RoutingIntelligenceEngine().evaluate(
        catalog=_catalog(),
        runtime_state=_state(a_circuit=True),
        policy=RoutingPolicy(),
        request=_request(),
        now=NOW,
    )
    assert evidence.ranked_model_ids == ("model-b",)
    excluded = {
        row.model_id: row.reasons for row in evidence.candidates if not row.eligible
    }
    assert "circuit_open" in excluded["model-a"]
    selected = route_via_canonical_authority(
        _catalog().build_registry(),
        RoutingPolicy(),
        evidence,
        preferred_model="model-a",
    )
    assert selected.model_id == "model-b"


def test_quota_exhaustion_is_fail_closed_when_no_candidate_remains() -> None:
    with pytest.raises(GovernanceError, match="no candidate"):
        RoutingIntelligenceEngine().evaluate(
            catalog=_catalog(),
            runtime_state=_state(a_requests=0, b_requests=0),
            policy=RoutingPolicy(),
            request=_request(),
            now=NOW,
        )


def test_stale_catalog_or_runtime_evidence_is_rejected() -> None:
    stale = NOW - timedelta(hours=2)
    with pytest.raises(GovernanceError, match="catalog"):
        RoutingIntelligenceEngine().evaluate(
            catalog=ProviderCatalogSnapshot(
                "old",
                stale,
                _catalog().providers,
                _catalog().models,
                _catalog().quality,
            ),
            runtime_state=_state(),
            policy=RoutingPolicy(),
            request=RoutingIntelligenceRequest(
                "text.reasoning", 100, 50, max_catalog_age_seconds=60
            ),
            now=NOW,
        )
    with pytest.raises(GovernanceError, match="runtime"):
        RoutingIntelligenceEngine().evaluate(
            catalog=_catalog(),
            runtime_state=_state(observed_at=stale),
            policy=RoutingPolicy(),
            request=RoutingIntelligenceRequest(
                "text.reasoning", 100, 50, max_state_age_seconds=60
            ),
            now=NOW,
        )


def test_intelligence_can_only_narrow_existing_policy() -> None:
    evidence = RoutingIntelligenceEngine().evaluate(
        catalog=_catalog(),
        runtime_state=_state(a_circuit=True),
        policy=RoutingPolicy(),
        request=_request(),
        now=NOW,
    )
    with pytest.raises(GovernanceError, match="outside allowed"):
        canonical_policy_from_evidence(
            RoutingPolicy(allowed_models=frozenset({"model-a"})),
            evidence,
        )


def test_missing_health_or_quota_is_not_silently_treated_as_available() -> None:
    state = ProviderRuntimeSnapshot(
        "partial",
        NOW,
        (ProviderHealthState("provider-a", NOW, Decimal("0.99"), 100),),
        (
            ProviderQuotaState(
                "provider-a",
                NOW,
                remaining_requests=10,
                remaining_tokens=10_000,
            ),
        ),
    )
    evidence = RoutingIntelligenceEngine().evaluate(
        catalog=_catalog(),
        runtime_state=state,
        policy=RoutingPolicy(),
        request=_request(),
        now=NOW,
    )
    assert evidence.ranked_model_ids == ("model-a",)
    row = next(item for item in evidence.candidates if item.model_id == "model-b")
    assert row.eligible is False
    assert set(row.reasons) == {"health_missing", "quota_missing"}
