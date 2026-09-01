"""Configurable reliability, incident, recovery, and operational evidence."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from enum import Enum
from typing import ClassVar


class OperationsError(RuntimeError):
    """An operational control is invalid or incomplete."""


@dataclass(frozen=True, slots=True)
class ServiceLevelObjective:
    service_id: str
    sli_name: str
    target: float
    window: timedelta
    owner: str
    profile_id: str

    def __post_init__(self) -> None:
        if (
            not self.service_id
            or not self.sli_name
            or not self.owner
            or not self.profile_id
        ):
            raise ValueError("SLO identity, owner, and deployment profile are required")
        if not 0 < self.target <= 1 or self.window <= timedelta(0):
            raise ValueError("SLO target and window are invalid")


@dataclass(frozen=True, slots=True)
class SLIObservation:
    good_events: int
    total_events: int
    observed_at: datetime

    @property
    def ratio(self) -> float:
        if self.total_events <= 0 or not 0 <= self.good_events <= self.total_events:
            raise OperationsError("SLI observation is invalid")
        return self.good_events / self.total_events


@dataclass(frozen=True, slots=True)
class ErrorBudgetResult:
    objective: ServiceLevelObjective
    actual_ratio: float
    remaining_fraction: float
    exhausted: bool


def evaluate_error_budget(
    objective: ServiceLevelObjective, observations: tuple[SLIObservation, ...]
) -> ErrorBudgetResult:
    good = sum(item.good_events for item in observations)
    total = sum(item.total_events for item in observations)
    ratio = (
        SLIObservation(good, total, observations[-1].observed_at).ratio
        if observations
        else 0.0
    )
    allowed_bad = 1 - objective.target
    actual_bad = 1 - ratio
    remaining = max(0.0, allowed_bad - actual_bad)
    return ErrorBudgetResult(objective, ratio, remaining, actual_bad > allowed_bad)


@dataclass(frozen=True, slots=True)
class HealthReport:
    service_id: str
    live: bool
    ready: bool
    dependencies_ready: bool
    checked_at: datetime
    correlation_id: str

    @property
    def accepts_traffic(self) -> bool:
        return self.live and self.ready and self.dependencies_ready


class IncidentSeverity(str, Enum):
    SEV1 = "sev1"
    SEV2 = "sev2"
    SEV3 = "sev3"
    SEV4 = "sev4"


class IncidentState(str, Enum):
    DECLARED = "declared"
    CONTAINED = "contained"
    RECOVERED = "recovered"
    REVIEWED = "reviewed"


@dataclass(frozen=True, slots=True)
class Incident:
    incident_id: str
    severity: IncidentSeverity
    commander: str
    owner: str
    runbook_id: str
    escalation_target: str
    declared_at: datetime
    state: IncidentState = IncidentState.DECLARED
    post_incident_review_id: str | None = None


class IncidentRegistry:
    _transitions: ClassVar[dict[IncidentState, IncidentState]] = {
        IncidentState.DECLARED: IncidentState.CONTAINED,
        IncidentState.CONTAINED: IncidentState.RECOVERED,
        IncidentState.RECOVERED: IncidentState.REVIEWED,
    }

    def __init__(self) -> None:
        self._incidents: dict[str, Incident] = {}

    def declare(self, incident: Incident) -> None:
        if not all(
            (
                incident.commander,
                incident.owner,
                incident.runbook_id,
                incident.escalation_target,
            )
        ):
            raise OperationsError(
                "incident ownership, runbook, and escalation are required"
            )
        if incident.incident_id in self._incidents:
            raise OperationsError("incident already exists")
        self._incidents[incident.incident_id] = incident

    def transition(
        self, incident_id: str, state: IncidentState, *, review_id: str | None = None
    ) -> Incident:
        incident = self._incidents[incident_id]
        if self._transitions.get(incident.state) is not state:
            raise OperationsError("incident transition is not allowed")
        if state is IncidentState.REVIEWED and not review_id:
            raise OperationsError("post-incident review is required")
        updated = replace(incident, state=state, post_incident_review_id=review_id)
        self._incidents[incident_id] = updated
        return updated


class ExerciseKind(str, Enum):
    BACKUP_VERIFICATION = "backup_verification"
    RESTORE = "restore"
    DISASTER_RECOVERY = "disaster_recovery"
    ROLLBACK = "rollback"


@dataclass(frozen=True, slots=True)
class RecoveryExercise:
    exercise_id: str
    kind: ExerciseKind
    service_id: str
    owner: str
    started_at: datetime
    completed_at: datetime
    passed: bool
    evidence_reference: str
    measured_recovery_seconds: int | None = None
    configured_rto_seconds: int | None = None
    configured_rpo_seconds: int | None = None

    def __post_init__(self) -> None:
        if (
            self.completed_at < self.started_at
            or not self.owner
            or not self.evidence_reference
        ):
            raise ValueError("exercise timing, owner, and evidence are required")
        values = (
            self.measured_recovery_seconds,
            self.configured_rto_seconds,
            self.configured_rpo_seconds,
        )
        if any(value is not None and value < 0 for value in values):
            raise ValueError("recovery values cannot be negative")

    @property
    def meets_configured_rto(self) -> bool | None:
        if (
            self.measured_recovery_seconds is None
            or self.configured_rto_seconds is None
        ):
            return None
        return (
            self.passed
            and self.measured_recovery_seconds <= self.configured_rto_seconds
        )


class RecoveryEvidenceRegistry:
    def __init__(self) -> None:
        self._exercises: dict[str, RecoveryExercise] = {}

    def record(self, exercise: RecoveryExercise) -> None:
        if exercise.exercise_id in self._exercises:
            raise OperationsError("exercise evidence already exists")
        self._exercises[exercise.exercise_id] = exercise

    def latest_pass(self, service_id: str, kind: ExerciseKind) -> RecoveryExercise:
        matches = [
            item
            for item in self._exercises.values()
            if item.service_id == service_id and item.kind is kind and item.passed
        ]
        if not matches:
            raise OperationsError("no passing recovery exercise evidence")
        return max(matches, key=lambda item: item.completed_at)
