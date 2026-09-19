"""Runtime binding for provider evidence, routing intelligence, and canonical routing.

This module is intentionally not a second router. It refreshes provider evidence,
asks ``RoutingIntelligenceEngine`` to rank already-policy-eligible candidates,
then delegates final selection to the existing ``services.ai_governance.route_model``
authority through ``route_via_canonical_authority``. A route is not returned
unless its evidence is durably persisted.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from services.ai_governance import GovernanceError, ModelRecord, RoutingPolicy
from services.evidence import EvidenceError, EvidenceStore
from services.provider_catalog import ProviderCatalogSnapshot
from services.provider_state import ProviderRuntimeSnapshot
from services.routing_intelligence import (
    RoutingIntelligenceEngine,
    RoutingIntelligenceEvidence,
    RoutingIntelligenceRequest,
    route_via_canonical_authority,
)


class ProviderCatalogSource(Protocol):
    """Replaceable source for current provider/model catalog evidence."""

    def observe_catalog(self, *, now: datetime) -> ProviderCatalogSnapshot: ...


class ProviderRuntimeSource(Protocol):
    """Replaceable source for current provider health/quota evidence."""

    def observe_runtime(self, *, now: datetime) -> ProviderRuntimeSnapshot: ...


@dataclass(frozen=True, slots=True)
class RoutingResolution:
    """Canonical selection plus immutable persisted evidence identity."""

    selected_model: ModelRecord
    intelligence: RoutingIntelligenceEvidence
    artifact_digest: str
    provenance_hash: str


class GovernedRoutingRuntime:
    """Refresh evidence, narrow policy, delegate selection, and persist proof."""

    def __init__(
        self,
        catalog_source: ProviderCatalogSource,
        runtime_source: ProviderRuntimeSource,
        evidence_store: EvidenceStore,
        *,
        engine: RoutingIntelligenceEngine | None = None,
    ) -> None:
        self._catalog_source = catalog_source
        self._runtime_source = runtime_source
        self._evidence_store = evidence_store
        self._engine = engine or RoutingIntelligenceEngine()

    def resolve(
        self,
        *,
        execution_id: str,
        policy: RoutingPolicy,
        request: RoutingIntelligenceRequest,
        now: datetime,
        preferred_model: str | None = None,
    ) -> RoutingResolution:
        """Resolve one governed route or fail closed before provider execution."""

        _text("execution_id", execution_id)
        if now.tzinfo is None:
            raise ValueError("now must be timezone-aware")

        catalog = self._observe_catalog(now)
        runtime_state = self._observe_runtime(now)
        intelligence = self._engine.evaluate(
            catalog=catalog,
            runtime_state=runtime_state,
            policy=policy,
            request=request,
            now=now,
        )
        selected = route_via_canonical_authority(
            catalog.build_registry(),
            policy,
            intelligence,
            preferred_model=preferred_model,
        )

        payload = _evidence_payload(
            execution_id=execution_id,
            selected=selected,
            policy=policy,
            request=request,
            catalog=catalog,
            runtime_state=runtime_state,
            intelligence=intelligence,
        )
        try:
            artifact = self._evidence_store.put_artifact(payload)
            provenance = self._evidence_store.append_provenance(
                execution_id,
                artifact,
                "routing.resolve",
            )
        except EvidenceError as exc:
            raise GovernanceError("routing evidence persistence failed") from exc

        return RoutingResolution(
            selected,
            intelligence,
            artifact.digest,
            provenance.record_hash,
        )

    def _observe_catalog(self, now: datetime) -> ProviderCatalogSnapshot:
        try:
            return self._catalog_source.observe_catalog(now=now)
        except GovernanceError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise GovernanceError("provider catalog observation failed") from exc

    def _observe_runtime(self, now: datetime) -> ProviderRuntimeSnapshot:
        try:
            return self._runtime_source.observe_runtime(now=now)
        except GovernanceError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise GovernanceError("provider runtime observation failed") from exc


def _evidence_payload(
    *,
    execution_id: str,
    selected: ModelRecord,
    policy: RoutingPolicy,
    request: RoutingIntelligenceRequest,
    catalog: ProviderCatalogSnapshot,
    runtime_state: ProviderRuntimeSnapshot,
    intelligence: RoutingIntelligenceEvidence,
) -> bytes:
    document: dict[str, object] = {
        "schema": "ilaios.routing-evidence.v1",
        "execution_id": execution_id,
        "selected": {
            "model_id": selected.model_id,
            "provider_id": selected.provider_id,
        },
        "request": {
            "capability": request.capability,
            "input_tokens": request.input_tokens,
            "output_tokens": request.output_tokens,
            "require_health": request.require_health,
            "require_quota": request.require_quota,
            "max_catalog_age_seconds": request.max_catalog_age_seconds,
            "max_state_age_seconds": request.max_state_age_seconds,
        },
        "policy": {
            "allowed_models": sorted(policy.allowed_models),
            "denied_models": sorted(policy.denied_models),
            "allowed_providers": sorted(policy.allowed_providers),
            "denied_providers": sorted(policy.denied_providers),
            "fallback_order": list(policy.fallback_order),
        },
        "catalog": {
            "catalog_version": catalog.catalog_version,
            "observed_at": catalog.observed_at.isoformat(),
            "providers": [
                {
                    "provider_id": provider.provider_id,
                    "adapter_id": provider.adapter_id,
                    "enabled": provider.enabled,
                }
                for provider in sorted(
                    catalog.providers, key=lambda item: item.provider_id
                )
            ],
            "models": [
                {
                    "model_id": model.model_id,
                    "provider_id": model.provider_id,
                    "capabilities": sorted(model.capabilities),
                    "context_window": model.context_window,
                    "max_output_tokens": model.max_output_tokens,
                    "input_cost_per_million": str(model.input_cost_per_million),
                    "output_cost_per_million": str(model.output_cost_per_million),
                    "gpu_seconds_per_request": str(model.gpu_seconds_per_request),
                    "enabled": model.enabled,
                }
                for model in sorted(catalog.models, key=lambda item: item.model_id)
            ],
            "quality": [
                {"model_id": item.model_id, "score": str(item.score)}
                for item in sorted(catalog.quality, key=lambda item: item.model_id)
            ],
        },
        "runtime_state": {
            "state_version": runtime_state.state_version,
            "observed_at": runtime_state.observed_at.isoformat(),
            "health": [
                {
                    "provider_id": item.provider_id,
                    "observed_at": item.observed_at.isoformat(),
                    "success_rate": str(item.success_rate),
                    "p95_latency_ms": item.p95_latency_ms,
                    "consecutive_failures": item.consecutive_failures,
                    "circuit_open": item.circuit_open,
                }
                for item in sorted(
                    runtime_state.health, key=lambda item: item.provider_id
                )
            ],
            "quota": [
                {
                    "provider_id": item.provider_id,
                    "observed_at": item.observed_at.isoformat(),
                    "remaining_requests": item.remaining_requests,
                    "remaining_tokens": item.remaining_tokens,
                    "reset_at": (
                        None if item.reset_at is None else item.reset_at.isoformat()
                    ),
                }
                for item in sorted(
                    runtime_state.quota, key=lambda item: item.provider_id
                )
            ],
        },
        "intelligence": {
            "catalog_version": intelligence.catalog_version,
            "runtime_state_version": intelligence.runtime_state_version,
            "evaluated_at": intelligence.evaluated_at.isoformat(),
            "ranked_model_ids": list(intelligence.ranked_model_ids),
            "candidates": [
                {
                    "model_id": candidate.model_id,
                    "provider_id": candidate.provider_id,
                    "eligible": candidate.eligible,
                    "score": str(candidate.score),
                    "estimated_cost": str(candidate.estimated_cost),
                    "reasons": list(candidate.reasons),
                }
                for candidate in intelligence.candidates
            ],
        },
    }
    return json.dumps(
        document,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _text(name: str, value: str) -> None:
    if not value or value != value.strip():
        raise ValueError(f"{name} must be non-empty and trimmed")
