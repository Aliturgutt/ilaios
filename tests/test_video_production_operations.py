from __future__ import annotations

import pytest

from src.video_automation.production_operations import (
    VideoOperationalObservation,
    VideoOperationsAlertKind,
    VideoOperationsSloTargets,
    VideoProductionOperationsError,
    project_video_operations_slo,
)

REVISION = "a" * 40
PRODUCT_ID = "finished-video-prod-001"
ARTIFACT_SHA = "b" * 64


def _observation(
    index: int,
    *,
    cost_microusd: int = 100_000,
    latency_ms: int = 20_000,
    available: bool = True,
    quality_passed: bool = True,
    artifact_sha256: str = ARTIFACT_SHA,
    environment: str = "production",
) -> VideoOperationalObservation:
    return VideoOperationalObservation(
        revision_sha=REVISION,
        product_id=PRODUCT_ID,
        artifact_sha256=artifact_sha256,
        provider_name="openrouter-video-managed",
        request_id=f"request-{index:03d}",
        observed_at=f"2026-08-15T10:{index:02d}:00+00:00",
        cost_microusd=cost_microusd,
        latency_ms=latency_ms,
        available=available,
        quality_passed=quality_passed,
        provider_receipt_ref=f"evidence://provider/receipt-{index:03d}",
        telemetry_ref=f"telemetry://video/run-{index:03d}",
        environment=environment,
    )


def _targets(*, minimum_samples: int = 5) -> VideoOperationsSloTargets:
    return VideoOperationsSloTargets(
        minimum_samples=minimum_samples,
        cost_budget_microusd=1_000_000,
        p95_latency_target_ms=60_000,
        availability_target_ratio=0.99,
        quality_target_ratio=0.90,
    )


def test_healthy_observations_emit_deterministic_slo_evidence() -> None:
    observations = tuple(_observation(index) for index in range(5))

    first = project_video_operations_slo(observations, _targets())
    second = project_video_operations_slo(tuple(reversed(observations)), _targets())

    assert first == second
    assert first.sample_count == 5
    assert first.total_cost_microusd == 500_000
    assert first.total_cost_usd == 0.5
    assert first.p95_latency_ms == 20_000
    assert first.availability_ratio == 1.0
    assert first.quality_pass_ratio == 1.0
    assert first.provider_names == ("openrouter-video-managed",)
    assert first.slo_passed is True
    assert first.alerts == ()
    assert len(first.evidence_sha256) == 64


def test_insufficient_observed_samples_fail_closed() -> None:
    snapshot = project_video_operations_slo(
        tuple(_observation(index) for index in range(2)),
        _targets(minimum_samples=3),
    )

    assert snapshot.slo_passed is False
    assert [alert.kind for alert in snapshot.alerts] == [
        VideoOperationsAlertKind.INSUFFICIENT_SAMPLES
    ]


def test_each_operational_slo_violation_emits_an_alert() -> None:
    observations = (
        _observation(
            0,
            cost_microusd=600_000,
            latency_ms=70_000,
            available=False,
            quality_passed=False,
        ),
        _observation(
            1,
            cost_microusd=600_000,
            latency_ms=65_000,
            available=True,
            quality_passed=False,
        ),
    )
    targets = VideoOperationsSloTargets(
        minimum_samples=2,
        cost_budget_microusd=1_000_000,
        p95_latency_target_ms=60_000,
        availability_target_ratio=0.99,
        quality_target_ratio=0.90,
    )

    snapshot = project_video_operations_slo(observations, targets)

    assert snapshot.slo_passed is False
    assert {alert.kind for alert in snapshot.alerts} == {
        VideoOperationsAlertKind.COST_BUDGET,
        VideoOperationsAlertKind.LATENCY_SLO,
        VideoOperationsAlertKind.AVAILABILITY_SLO,
        VideoOperationsAlertKind.QUALITY_SLO,
    }
    assert all(
        alert.evidence_ref.startswith("evidence://video-operations/alerts/")
        for alert in snapshot.alerts
    )


def test_p95_uses_nearest_rank_over_observed_latency() -> None:
    observations = tuple(
        _observation(index, latency_ms=(index + 1) * 1_000)
        for index in range(20)
    )
    targets = VideoOperationsSloTargets(
        minimum_samples=20,
        cost_budget_microusd=5_000_000,
        p95_latency_target_ms=19_000,
        availability_target_ratio=1.0,
        quality_target_ratio=1.0,
    )

    snapshot = project_video_operations_slo(observations, targets)

    assert snapshot.p95_latency_ms == 19_000
    assert snapshot.slo_passed is True


def test_cross_artifact_observations_are_rejected() -> None:
    observations = (
        _observation(0),
        _observation(1, artifact_sha256="c" * 64),
    )

    with pytest.raises(
        VideoProductionOperationsError,
        match="one exact artifact identity",
    ):
        project_video_operations_slo(observations, _targets(minimum_samples=2))


def test_duplicate_request_or_telemetry_identity_is_rejected() -> None:
    duplicate_request = _observation(0)
    with pytest.raises(
        VideoProductionOperationsError,
        match="request_id must be unique",
    ):
        project_video_operations_slo(
            (duplicate_request, duplicate_request),
            _targets(minimum_samples=2),
        )

    first = _observation(0)
    second = VideoOperationalObservation(
        revision_sha=REVISION,
        product_id=PRODUCT_ID,
        artifact_sha256=ARTIFACT_SHA,
        provider_name="volcengine-seedance",
        request_id="request-unique",
        observed_at="2026-08-15T10:01:30+00:00",
        cost_microusd=100_000,
        latency_ms=20_000,
        available=True,
        quality_passed=True,
        provider_receipt_ref="evidence://provider/receipt-unique",
        telemetry_ref=first.telemetry_ref,
    )
    with pytest.raises(
        VideoProductionOperationsError,
        match="telemetry_ref must be unique",
    ):
        project_video_operations_slo(
            (first, second),
            _targets(minimum_samples=2),
        )


def test_non_production_observation_cannot_be_used_as_production_evidence() -> None:
    with pytest.raises(
        VideoProductionOperationsError,
        match="only production observations",
    ):
        _observation(0, environment="staging")


def test_empty_observation_set_is_rejected() -> None:
    with pytest.raises(
        VideoProductionOperationsError,
        match="requires at least one observation",
    ):
        project_video_operations_slo((), _targets())
