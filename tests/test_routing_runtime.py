"""Runtime closure proofs for dynamic routing evidence and canonical selection."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from services.ai_governance import GovernanceError, ModelRecord, ProviderRecord, RoutingPolicy
from services.evidence import EvidenceStore
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
)
from services.routing_runtime import GovernedRoutingRuntime

NOW = datetime(2026, 8, 18, 11, 0, tzinfo=timezone.utc)


class _CatalogSource:
    def __init__(self, snapshots: tuple[ProviderCatalogSnapshot, ...]) -> None:
        self._snapshots = snapshots
        self.calls = 0

    def observe_catalog(self, *, now: datetime) -> ProviderCatalogSnapshot:
        del now
        if not self._snapshots:
            raise RuntimeError("no catalog")
        index = min(self.calls, len(self._snapshots) - 1)
        self.calls += 1
        return self._snapshots[index]


class _RuntimeSource:
    def __init__(self, snapshots: tuple[ProviderRuntimeSnapshot, ...]) -> None:
        self._snapshots = snapshots
        self.calls = 0

    def observe_runtime(self, *, now: datetime) -> ProviderRuntimeSnapshot:
        del now
        if not self._snapshots:
            raise RuntimeError("no runtime state")
        index = min(self.calls, len(self._snapshots) - 1)
        self.calls += 1
        return self._snapshots[index]


class _BrokenCatalogSource:
    def observe_catalog(self, *, now: datetime) -> ProviderCatalogSnapshot:
        del now
        raise RuntimeError("provider unavailable")


def _catalog() -> ProviderCatalogSnapshot:
    return ProviderCatalogSnapshot(
        "catalog-live-1",
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
    version: str,
    *,
    a_circuit: bool = False,
    b_circuit: bool = False,
    observed_at: datetime = NOW,
) -> ProviderRuntimeSnapshot:
    return ProviderRuntimeSnapshot(
        version,
        observed_at,
        (
            ProviderHealthState(
                "provider-a",
                observed_at,
                Decimal("0.99"),
                120,
                circuit_open=a_circuit,
            ),
            ProviderHealthState(
                "provider-b",
                observed_at,
                Decimal("0.98"),
                150,
                circuit_open=b_circuit,
            ),
        ),
        (
            ProviderQuotaState(
                "provider-a",
                observed_at,
                remaining_requests=100,
                remaining_tokens=1_000_000,
            ),
            ProviderQuotaState(
                "provider-b",
                observed_at,
                remaining_requests=100,
                remaining_tokens=1_000_000,
            ),
        ),
    )


def _request() -> RoutingIntelligenceRequest:
    return RoutingIntelligenceRequest("text.reasoning", 4_000, 1_000)


def _cost_only_engine() -> RoutingIntelligenceEngine:
    return RoutingIntelligenceEngine(
        RoutingScoreWeights(
            cost=Decimal(1),
            latency=Decimal(0),
            reliability=Decimal(0),
            quality=Decimal(0),
            quota=Decimal(0),
        )
    )


def _runtime(
    root: Path,
    catalog_source: _CatalogSource | _BrokenCatalogSource,
    runtime_source: _RuntimeSource,
) -> tuple[GovernedRoutingRuntime, EvidenceStore]:
    store = EvidenceStore(root)
    return (
        GovernedRoutingRuntime(
            catalog_source,
            runtime_source,
            store,
            engine=_cost_only_engine(),
        ),
        store,
    )


def test_runtime_refreshes_sources_delegates_and_persists_full_evidence(
    tmp_path: Path,
) -> None:
    catalog_source = _CatalogSource((_catalog(),))
    state_source = _RuntimeSource((_state("state-live-1"),))
    runtime, store = _runtime(tmp_path / "evidence", catalog_source, state_source)

    resolution = runtime.resolve(
        execution_id="execution-1",
        policy=RoutingPolicy(),
        request=_request(),
        now=NOW,
    )

    assert resolution.selected_model.model_id == "model-b"
    assert resolution.intelligence.ranked_model_ids == ("model-b", "model-a")
    assert catalog_source.calls == 1
    assert state_source.calls == 1

    document = json.loads(store.get_artifact(resolution.artifact_digest))
    assert document["schema"] == "ilaios.routing-evidence.v1"
    assert document["selected"] == {
        "model_id": "model-b",
        "provider_id": "provider-b",
    }
    assert document["catalog"]["catalog_version"] == "catalog-live-1"
    assert document["runtime_state"]["state_version"] == "state-live-1"
    assert document["intelligence"]["ranked_model_ids"] == ["model-b", "model-a"]

    provenance = store.verify()
    assert len(provenance) == 1
    assert provenance[0].action == "routing.resolve"
    assert provenance[0].record_hash == resolution.provenance_hash


def test_runtime_reobserves_dynamic_state_for_every_resolution(tmp_path: Path) -> None:
    catalog_source = _CatalogSource((_catalog(),))
    state_source = _RuntimeSource(
        (
            _state("state-1", b_circuit=True),
            _state("state-2", a_circuit=True),
        )
    )
    runtime, store = _runtime(tmp_path / "evidence", catalog_source, state_source)

    first = runtime.resolve(
        execution_id="execution-1",
        policy=RoutingPolicy(),
        request=_request(),
        now=NOW,
    )
    second = runtime.resolve(
        execution_id="execution-2",
        policy=RoutingPolicy(),
        request=_request(),
        now=NOW,
    )

    assert first.selected_model.model_id == "model-a"
    assert second.selected_model.model_id == "model-b"
    assert catalog_source.calls == 2
    assert state_source.calls == 2
    assert first.artifact_digest != second.artifact_digest
    assert len(store.verify()) == 2


def test_source_failure_is_fail_closed_and_emits_no_route_evidence(
    tmp_path: Path,
) -> None:
    runtime, store = _runtime(
        tmp_path / "evidence",
        _BrokenCatalogSource(),
        _RuntimeSource((_state("state-live-1"),)),
    )

    with pytest.raises(GovernanceError, match="catalog observation failed"):
        runtime.resolve(
            execution_id="execution-1",
            policy=RoutingPolicy(),
            request=_request(),
            now=NOW,
        )

    assert store.verify() == ()


def test_stale_runtime_state_fails_before_persisting_selection(tmp_path: Path) -> None:
    catalog_source = _CatalogSource((_catalog(),))
    stale = NOW - timedelta(minutes=10)
    state_source = _RuntimeSource((_state("stale", observed_at=stale),))
    runtime, store = _runtime(tmp_path / "evidence", catalog_source, state_source)

    with pytest.raises(GovernanceError, match="runtime evidence is stale"):
        runtime.resolve(
            execution_id="execution-1",
            policy=RoutingPolicy(),
            request=RoutingIntelligenceRequest(
                "text.reasoning",
                100,
                50,
                max_state_age_seconds=60,
            ),
            now=NOW,
        )

    assert store.verify() == ()


def test_runtime_cannot_use_intelligence_to_widen_caller_policy(tmp_path: Path) -> None:
    catalog_source = _CatalogSource((_catalog(),))
    state_source = _RuntimeSource((_state("state-live-1", a_circuit=True),))
    runtime, store = _runtime(tmp_path / "evidence", catalog_source, state_source)

    with pytest.raises(GovernanceError, match="no candidate"):
        runtime.resolve(
            execution_id="execution-1",
            policy=RoutingPolicy(allowed_models=frozenset({"model-a"})),
            request=_request(),
            now=NOW,
        )

    assert store.verify() == ()
