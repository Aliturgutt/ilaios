"""Bounded proofs for OPS.I05."""

from datetime import datetime, timedelta, timezone

import pytest

from services.operations import (
    ExerciseKind,
    HealthReport,
    Incident,
    IncidentRegistry,
    IncidentSeverity,
    IncidentState,
    OperationsError,
    RecoveryEvidenceRegistry,
    RecoveryExercise,
    ServiceLevelObjective,
    SLIObservation,
    evaluate_error_budget,
)

NOW = datetime(2026, 8, 9, tzinfo=timezone.utc)


def test_configured_slo_and_error_budget_are_measurable_not_contractual_defaults() -> (
    None
):
    objective = ServiceLevelObjective(
        "api", "availability", 0.99, timedelta(days=30), "owner-1", "profile-a"
    )
    result = evaluate_error_budget(objective, (SLIObservation(98, 100, NOW),))
    assert result.exhausted and result.actual_ratio == 0.98
    with pytest.raises(ValueError, match="target"):
        ServiceLevelObjective(
            "api", "availability", 0, timedelta(days=1), "owner", "profile"
        )


def test_health_distinguishes_liveness_readiness_and_dependency_readiness() -> None:
    report = HealthReport("api", True, True, False, NOW, "correlation-1")
    assert not report.accepts_traffic


def test_incident_severity_workflow_escalation_and_review_are_enforced() -> None:
    registry = IncidentRegistry()
    incident = Incident(
        "inc-1",
        IncidentSeverity.SEV1,
        "commander-1",
        "owner-1",
        "runbook-1",
        "executive-on-call",
        NOW,
    )
    registry.declare(incident)
    registry.transition("inc-1", IncidentState.CONTAINED)
    registry.transition("inc-1", IncidentState.RECOVERED)
    with pytest.raises(OperationsError, match="review"):
        registry.transition("inc-1", IncidentState.REVIEWED)
    assert (
        registry.transition("inc-1", IncidentState.REVIEWED, review_id="pir-1").state
        is IncidentState.REVIEWED
    )


def test_backup_restore_dr_and_rollback_evidence_require_real_results() -> None:
    registry = RecoveryEvidenceRegistry()
    for index, kind in enumerate(ExerciseKind):
        registry.record(
            RecoveryExercise(
                f"exercise-{index}",
                kind,
                "api",
                "owner-1",
                NOW,
                NOW + timedelta(minutes=1),
                True,
                f"evidence/{index}",
                measured_recovery_seconds=60,
                configured_rto_seconds=120,
            )
        )
        assert registry.latest_pass("api", kind).meets_configured_rto is True
    with pytest.raises(OperationsError, match="no passing"):
        registry.latest_pass("other", ExerciseKind.RESTORE)
