"""ILAIOS-native routing intelligence beneath the canonical routing authority.

This module ranks already-policy-eligible provider/model candidates using bounded
health, quota, catalog, cost, latency, reliability, and quality evidence. It
does not create a second routing authority: final selection is delegated to
``services.ai_governance.route_model``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

from services.ai_governance import (
    GovernanceError,
    ModelProviderRegistry,
    ModelRecord,
    RoutingPolicy,
    route_model,
)
from services.provider_catalog import ProviderCatalogSnapshot
from services.provider_state import ProviderQuotaState, ProviderRuntimeSnapshot

_MILLION = Decimal(1_000_000)
_ZERO = Decimal(0)
_ONE = Decimal(1)


def _text(name: str, value: str) -> None:
    if not value or value != value.strip():
        raise ValueError(f"{name} must be non-empty and trimmed")


def _unit(name: str, value: Decimal) -> None:
    if value < _ZERO or value > _ONE:
        raise ValueError(f"{name} must be in [0, 1]")


@dataclass(frozen=True, slots=True)
class RoutingScoreWeights:
    cost: Decimal = Decimal("0.30")
    latency: Decimal = Decimal("0.20")
    reliability: Decimal = Decimal("0.25")
    quality: Decimal = Decimal("0.15")
    quota: Decimal = Decimal("0.10")

    def __post_init__(self) -> None:
        values = (self.cost, self.latency, self.reliability, self.quality, self.quota)
        if any(value < _ZERO for value in values):
            raise ValueError("routing weights cannot be negative")
        if sum(values, _ZERO) <= _ZERO:
            raise ValueError("at least one routing weight must be positive")

    @property
    def total(self) -> Decimal:
        return sum(
            (self.cost, self.latency, self.reliability, self.quality, self.quota),
            _ZERO,
        )


@dataclass(frozen=True, slots=True)
class RoutingIntelligenceRequest:
    capability: str
    input_tokens: int
    output_tokens: int
    require_health: bool = True
    require_quota: bool = True
    max_catalog_age_seconds: int = 86_400
    max_state_age_seconds: int = 300

    def __post_init__(self) -> None:
        _text("capability", self.capability)
        if self.input_tokens < 0 or self.output_tokens < 0:
            raise ValueError("token estimates cannot be negative")
        if self.max_catalog_age_seconds <= 0 or self.max_state_age_seconds <= 0:
            raise ValueError("freshness windows must be positive")


@dataclass(frozen=True, slots=True)
class RoutingCandidateEvidence:
    model_id: str
    provider_id: str
    eligible: bool
    score: Decimal
    estimated_cost: Decimal
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RoutingIntelligenceEvidence:
    capability: str
    catalog_version: str
    runtime_state_version: str
    ranked_model_ids: tuple[str, ...]
    candidates: tuple[RoutingCandidateEvidence, ...]
    evaluated_at: datetime

    @property
    def excluded_model_ids(self) -> tuple[str, ...]:
        return tuple(
            candidate.model_id for candidate in self.candidates if not candidate.eligible
        )


class RoutingIntelligenceEngine:
    """Rank candidates without authorizing or executing provider work."""

    def __init__(self, weights: RoutingScoreWeights = RoutingScoreWeights()) -> None:
        self._weights = weights

    def evaluate(
        self,
        *,
        catalog: ProviderCatalogSnapshot,
        runtime_state: ProviderRuntimeSnapshot,
        policy: RoutingPolicy,
        request: RoutingIntelligenceRequest,
        now: datetime,
    ) -> RoutingIntelligenceEvidence:
        if now.tzinfo is None:
            raise ValueError("now must be timezone-aware")
        if not catalog.is_fresh(
            now, timedelta(seconds=request.max_catalog_age_seconds)
        ):
            raise GovernanceError("provider catalog evidence is stale")
        if not runtime_state.is_fresh(
            now, timedelta(seconds=request.max_state_age_seconds)
        ):
            raise GovernanceError("provider runtime evidence is stale")

        quality = catalog.quality_map()
        providers = catalog.provider_map()
        rows: list[RoutingCandidateEvidence] = []

        for model in sorted(catalog.models, key=lambda item: item.model_id):
            reasons: list[str] = []
            provider = providers.get(model.provider_id)
            if provider is None or not provider.enabled or not model.enabled:
                reasons.append("provider_or_model_disabled")
            if request.capability not in model.capabilities:
                reasons.append("capability_mismatch")
            if not policy.permits(model):
                reasons.append("policy_denied")

            health = runtime_state.health_for(model.provider_id)
            quota = runtime_state.quota_for(model.provider_id)

            if health is None:
                if request.require_health:
                    reasons.append("health_missing")
            else:
                if not health.is_fresh(
                    now, timedelta(seconds=request.max_state_age_seconds)
                ):
                    reasons.append("health_stale")
                if health.circuit_open:
                    reasons.append("circuit_open")

            requested_tokens = request.input_tokens + request.output_tokens
            if quota is None:
                if request.require_quota:
                    reasons.append("quota_missing")
            else:
                if not quota.is_fresh(
                    now, timedelta(seconds=request.max_state_age_seconds)
                ):
                    reasons.append("quota_stale")
                if quota.remaining_requests is not None and quota.remaining_requests <= 0:
                    reasons.append("request_quota_exhausted")
                if (
                    quota.remaining_tokens is not None
                    and quota.remaining_tokens < requested_tokens
                ):
                    reasons.append("token_quota_exhausted")

            estimated_cost = _estimate_cost(
                model, request.input_tokens, request.output_tokens
            )
            if reasons:
                rows.append(
                    RoutingCandidateEvidence(
                        model.model_id,
                        model.provider_id,
                        False,
                        _ZERO,
                        estimated_cost,
                        tuple(sorted(set(reasons))),
                    )
                )
                continue

            reliability_score = (
                health.success_rate if health is not None else Decimal("0.5")
            )
            latency_score = (
                _ONE / (_ONE + (Decimal(health.p95_latency_ms) / Decimal(1000)))
                if health is not None
                else Decimal("0.5")
            )
            cost_score = _ONE / (_ONE + estimated_cost)
            quality_score = quality.get(model.model_id, Decimal("0.5"))
            quota_score = _quota_score(quota, requested_tokens)
            for name, value in (
                ("reliability_score", reliability_score),
                ("latency_score", latency_score),
                ("cost_score", cost_score),
                ("quality_score", quality_score),
                ("quota_score", quota_score),
            ):
                _unit(name, value)

            weighted = (
                cost_score * self._weights.cost
                + latency_score * self._weights.latency
                + reliability_score * self._weights.reliability
                + quality_score * self._weights.quality
                + quota_score * self._weights.quota
            ) / self._weights.total
            rows.append(
                RoutingCandidateEvidence(
                    model.model_id,
                    model.provider_id,
                    True,
                    weighted,
                    estimated_cost,
                    (
                        "policy_permitted",
                        "health_acceptable",
                        "quota_available",
                        "deterministic_score",
                    ),
                )
            )

        eligible = [row for row in rows if row.eligible]
        eligible.sort(key=lambda row: (-row.score, row.estimated_cost, row.model_id))
        if not eligible:
            raise GovernanceError(
                "no candidate satisfies routing intelligence constraints"
            )

        return RoutingIntelligenceEvidence(
            request.capability,
            catalog.catalog_version,
            runtime_state.state_version,
            tuple(row.model_id for row in eligible),
            tuple(sorted(rows, key=lambda row: row.model_id)),
            now,
        )


def canonical_policy_from_evidence(
    base: RoutingPolicy,
    evidence: RoutingIntelligenceEvidence,
) -> RoutingPolicy:
    """Constrain canonical routing to the evidenced candidate set.

    The returned policy narrows, never expands, the caller's existing policy.
    """
    ranked = evidence.ranked_model_ids
    if not ranked:
        raise GovernanceError("routing intelligence produced no eligible candidates")
    ranked_set = frozenset(ranked)
    allowed = ranked_set if not base.allowed_models else base.allowed_models & ranked_set
    if not allowed:
        raise GovernanceError(
            "routing intelligence candidates are outside allowed models"
        )
    return RoutingPolicy(
        allowed_models=allowed,
        denied_models=base.denied_models,
        allowed_providers=base.allowed_providers,
        denied_providers=base.denied_providers,
        fallback_order=tuple(model_id for model_id in ranked if model_id in allowed),
    )


def route_via_canonical_authority(
    registry: ModelProviderRegistry,
    base_policy: RoutingPolicy,
    evidence: RoutingIntelligenceEvidence,
    *,
    preferred_model: str | None = None,
) -> ModelRecord:
    """Delegate final selection to the existing canonical ``route_model``."""
    policy = canonical_policy_from_evidence(base_policy, evidence)
    if preferred_model is not None and preferred_model not in policy.allowed_models:
        preferred_model = None
    return route_model(registry, policy, evidence.capability, preferred_model)


def _estimate_cost(model: ModelRecord, input_tokens: int, output_tokens: int) -> Decimal:
    return (
        Decimal(input_tokens) * model.input_cost_per_million
        + Decimal(output_tokens) * model.output_cost_per_million
    ) / _MILLION


def _quota_score(
    quota: ProviderQuotaState | None, requested_tokens: int
) -> Decimal:
    if quota is None:
        return Decimal("0.5")
    remaining_requests = quota.remaining_requests
    remaining_tokens = quota.remaining_tokens
    parts: list[Decimal] = []
    if remaining_requests is not None:
        parts.append(min(_ONE, Decimal(remaining_requests) / Decimal(10)))
    if remaining_tokens is not None:
        denominator = max(requested_tokens, 1)
        parts.append(
            min(_ONE, Decimal(remaining_tokens) / Decimal(denominator * 4))
        )
    return (
        sum(parts, _ZERO) / Decimal(len(parts))
        if parts
        else Decimal("0.5")
    )
