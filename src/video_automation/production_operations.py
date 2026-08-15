"""Production Video operational observations, SLI/SLO projection, and alerts.

This module deliberately does not own job state, provider truth, or promotion.
It turns exact-artifact-bound production observations into deterministic
operational evidence that can later be admitted by the production acceptance
gate. Missing or insufficient observations fail closed.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from hashlib import sha256
from math import ceil


class VideoProductionOperationsError(ValueError):
    """Raised when operational evidence cannot be projected safely."""


class VideoOperationsAlertKind(str, Enum):
    INSUFFICIENT_SAMPLES = "INSUFFICIENT_SAMPLES"
    COST_BUDGET = "COST_BUDGET"
    LATENCY_SLO = "LATENCY_SLO"
    AVAILABILITY_SLO = "AVAILABILITY_SLO"
    QUALITY_SLO = "QUALITY_SLO"


@dataclass(frozen=True, slots=True)
class VideoOperationalObservation:
    revision_sha: str
    product_id: str
    artifact_sha256: str
    provider_name: str
    request_id: str
    observed_at: str
    cost_microusd: int
    latency_ms: int
    available: bool
    quality_passed: bool
    provider_receipt_ref: str
    telemetry_ref: str
    environment: str = "production"

    def __post_init__(self) -> None:
        _git_sha("revision_sha", self.revision_sha)
        _text("product_id", self.product_id)
        _sha256("artifact_sha256", self.artifact_sha256)
        _text("provider_name", self.provider_name)
        _text("request_id", self.request_id)
        _timestamp("observed_at", self.observed_at)
        if self.cost_microusd < 0:
            raise VideoProductionOperationsError("cost_microusd cannot be negative")
        if self.latency_ms < 0:
            raise VideoProductionOperationsError("latency_ms cannot be negative")
        _text("provider_receipt_ref", self.provider_receipt_ref)
        _text("telemetry_ref", self.telemetry_ref)
        if self.environment != "production":
            raise VideoProductionOperationsError(
                "production SLO evidence accepts only production observations"
            )


@dataclass(frozen=True, slots=True)
class VideoOperationsSloTargets:
    minimum_samples: int
    cost_budget_microusd: int
    p95_latency_target_ms: int
    availability_target_ratio: float
    quality_target_ratio: float

    def __post_init__(self) -> None:
        if self.minimum_samples <= 0:
            raise VideoProductionOperationsError("minimum_samples must be positive")
        if self.cost_budget_microusd < 0:
            raise VideoProductionOperationsError(
                "cost_budget_microusd cannot be negative"
            )
        if self.p95_latency_target_ms < 0:
            raise VideoProductionOperationsError(
                "p95_latency_target_ms cannot be negative"
            )
        _ratio("availability_target_ratio", self.availability_target_ratio)
        _ratio("quality_target_ratio", self.quality_target_ratio)


@dataclass(frozen=True, slots=True)
class VideoOperationsAlert:
    kind: VideoOperationsAlertKind
    observed: float
    threshold: float
    evidence_ref: str

    def __post_init__(self) -> None:
        _text("evidence_ref", self.evidence_ref)


@dataclass(frozen=True, slots=True)
class VideoOperationsSloSnapshot:
    revision_sha: str
    product_id: str
    artifact_sha256: str
    window_start: str
    window_end: str
    sample_count: int
    total_cost_microusd: int
    p95_latency_ms: int
    availability_ratio: float
    quality_pass_ratio: float
    provider_names: tuple[str, ...]
    observation_refs: tuple[str, ...]
    alerts: tuple[VideoOperationsAlert, ...]
    evidence_sha256: str

    @property
    def slo_passed(self) -> bool:
        return not self.alerts

    @property
    def total_cost_usd(self) -> float:
        return self.total_cost_microusd / 1_000_000.0


def project_video_operations_slo(
    observations: tuple[VideoOperationalObservation, ...],
    targets: VideoOperationsSloTargets,
) -> VideoOperationsSloSnapshot:
    """Project deterministic SLI/SLO evidence from production observations."""

    if not observations:
        raise VideoProductionOperationsError(
            "production SLO projection requires at least one observation"
        )

    first = observations[0]
    identity = (first.revision_sha, first.product_id, first.artifact_sha256)
    request_ids: set[str] = set()
    telemetry_refs: set[str] = set()
    parsed: list[tuple[datetime, VideoOperationalObservation]] = []
    for observation in observations:
        if (
            observation.revision_sha,
            observation.product_id,
            observation.artifact_sha256,
        ) != identity:
            raise VideoProductionOperationsError(
                "all production observations must bind to one exact artifact identity"
            )
        if observation.request_id in request_ids:
            raise VideoProductionOperationsError(
                "production observation request_id must be unique"
            )
        request_ids.add(observation.request_id)
        if observation.telemetry_ref in telemetry_refs:
            raise VideoProductionOperationsError(
                "production observation telemetry_ref must be unique"
            )
        telemetry_refs.add(observation.telemetry_ref)
        parsed.append((_timestamp("observed_at", observation.observed_at), observation))

    parsed.sort(key=lambda item: (item[0], item[1].request_id))
    ordered = tuple(item[1] for item in parsed)
    latencies = sorted(item.latency_ms for item in ordered)
    p95_index = max(0, ceil(len(latencies) * 0.95) - 1)
    p95_latency_ms = latencies[p95_index]
    total_cost_microusd = sum(item.cost_microusd for item in ordered)
    availability_ratio = sum(item.available for item in ordered) / len(ordered)
    quality_pass_ratio = sum(item.quality_passed for item in ordered) / len(ordered)

    alerts: list[VideoOperationsAlert] = []
    alert_ref = _alert_evidence_ref(first, ordered, targets)
    if len(ordered) < targets.minimum_samples:
        alerts.append(
            VideoOperationsAlert(
                kind=VideoOperationsAlertKind.INSUFFICIENT_SAMPLES,
                observed=float(len(ordered)),
                threshold=float(targets.minimum_samples),
                evidence_ref=alert_ref,
            )
        )
    if total_cost_microusd > targets.cost_budget_microusd:
        alerts.append(
            VideoOperationsAlert(
                kind=VideoOperationsAlertKind.COST_BUDGET,
                observed=float(total_cost_microusd),
                threshold=float(targets.cost_budget_microusd),
                evidence_ref=alert_ref,
            )
        )
    if p95_latency_ms > targets.p95_latency_target_ms:
        alerts.append(
            VideoOperationsAlert(
                kind=VideoOperationsAlertKind.LATENCY_SLO,
                observed=float(p95_latency_ms),
                threshold=float(targets.p95_latency_target_ms),
                evidence_ref=alert_ref,
            )
        )
    if availability_ratio < targets.availability_target_ratio:
        alerts.append(
            VideoOperationsAlert(
                kind=VideoOperationsAlertKind.AVAILABILITY_SLO,
                observed=availability_ratio,
                threshold=targets.availability_target_ratio,
                evidence_ref=alert_ref,
            )
        )
    if quality_pass_ratio < targets.quality_target_ratio:
        alerts.append(
            VideoOperationsAlert(
                kind=VideoOperationsAlertKind.QUALITY_SLO,
                observed=quality_pass_ratio,
                threshold=targets.quality_target_ratio,
                evidence_ref=alert_ref,
            )
        )

    window_start = parsed[0][0].astimezone(timezone.utc).isoformat()
    window_end = parsed[-1][0].astimezone(timezone.utc).isoformat()
    provider_names = tuple(sorted({item.provider_name for item in ordered}))
    observation_refs = tuple(item.telemetry_ref for item in ordered)
    normalized_alerts = tuple(sorted(alerts, key=lambda item: item.kind.value))
    evidence_sha256 = _snapshot_digest(
        revision_sha=first.revision_sha,
        product_id=first.product_id,
        artifact_sha256=first.artifact_sha256,
        window_start=window_start,
        window_end=window_end,
        sample_count=len(ordered),
        total_cost_microusd=total_cost_microusd,
        p95_latency_ms=p95_latency_ms,
        availability_ratio=availability_ratio,
        quality_pass_ratio=quality_pass_ratio,
        provider_names=provider_names,
        observation_refs=observation_refs,
        alerts=normalized_alerts,
    )
    return VideoOperationsSloSnapshot(
        revision_sha=first.revision_sha,
        product_id=first.product_id,
        artifact_sha256=first.artifact_sha256,
        window_start=window_start,
        window_end=window_end,
        sample_count=len(ordered),
        total_cost_microusd=total_cost_microusd,
        p95_latency_ms=p95_latency_ms,
        availability_ratio=availability_ratio,
        quality_pass_ratio=quality_pass_ratio,
        provider_names=provider_names,
        observation_refs=observation_refs,
        alerts=normalized_alerts,
        evidence_sha256=evidence_sha256,
    )


def _alert_evidence_ref(
    first: VideoOperationalObservation,
    observations: tuple[VideoOperationalObservation, ...],
    targets: VideoOperationsSloTargets,
) -> str:
    material = {
        "revision_sha": first.revision_sha,
        "product_id": first.product_id,
        "artifact_sha256": first.artifact_sha256,
        "telemetry_refs": [item.telemetry_ref for item in observations],
        "targets": {
            "minimum_samples": targets.minimum_samples,
            "cost_budget_microusd": targets.cost_budget_microusd,
            "p95_latency_target_ms": targets.p95_latency_target_ms,
            "availability_target_ratio": targets.availability_target_ratio,
            "quality_target_ratio": targets.quality_target_ratio,
        },
    }
    return "evidence://video-operations/alerts/" + _json_digest(material)


def _snapshot_digest(
    *,
    revision_sha: str,
    product_id: str,
    artifact_sha256: str,
    window_start: str,
    window_end: str,
    sample_count: int,
    total_cost_microusd: int,
    p95_latency_ms: int,
    availability_ratio: float,
    quality_pass_ratio: float,
    provider_names: tuple[str, ...],
    observation_refs: tuple[str, ...],
    alerts: tuple[VideoOperationsAlert, ...],
) -> str:
    material = {
        "revision_sha": revision_sha,
        "product_id": product_id,
        "artifact_sha256": artifact_sha256,
        "window_start": window_start,
        "window_end": window_end,
        "sample_count": sample_count,
        "total_cost_microusd": total_cost_microusd,
        "p95_latency_ms": p95_latency_ms,
        "availability_ratio": availability_ratio,
        "quality_pass_ratio": quality_pass_ratio,
        "provider_names": list(provider_names),
        "observation_refs": list(observation_refs),
        "alerts": [
            {
                "kind": alert.kind.value,
                "observed": alert.observed,
                "threshold": alert.threshold,
                "evidence_ref": alert.evidence_ref,
            }
            for alert in alerts
        ],
    }
    return _json_digest(material)


def _json_digest(material: object) -> str:
    encoded = json.dumps(
        material,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


def _timestamp(name: str, value: str) -> datetime:
    _text(name, value)
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise VideoProductionOperationsError(f"{name} must be ISO-8601") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise VideoProductionOperationsError(f"{name} must be timezone-aware")
    return parsed


def _ratio(name: str, value: float) -> None:
    if not 0.0 <= value <= 1.0:
        raise VideoProductionOperationsError(f"{name} must be normalized")


def _text(name: str, value: str) -> None:
    if not value or value != value.strip():
        raise VideoProductionOperationsError(f"{name} must be normalized non-blank text")


def _sha256(name: str, value: str) -> None:
    if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        raise VideoProductionOperationsError(f"{name} must be lowercase SHA-256")


def _git_sha(name: str, value: str) -> None:
    if len(value) != 40 or any(character not in "0123456789abcdef" for character in value):
        raise VideoProductionOperationsError(f"{name} must be lowercase 40-hex Git SHA")
