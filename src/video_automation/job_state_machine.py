"""Canonical M26 deterministic job-state execution control."""

from __future__ import annotations

from datetime import datetime, timezone

from .models import JobState, JobStateRecord


class JobStateTransitionError(ValueError):
    """Raised when a job attempts an invalid state transition."""


_ALLOWED: dict[JobState, frozenset[JobState]] = {
    JobState.PENDING: frozenset({JobState.RUNNING, JobState.CANCELLED}),
    JobState.RUNNING: frozenset({JobState.WAITING_PROVIDER, JobState.VALIDATING, JobState.FAILED, JobState.CANCELLED}),
    JobState.WAITING_PROVIDER: frozenset({JobState.RUNNING, JobState.RETRY_PENDING, JobState.FAILED, JobState.CANCELLED}),
    JobState.VALIDATING: frozenset({JobState.COMPLETED, JobState.RETRY_PENDING, JobState.FAILED, JobState.CANCELLED}),
    JobState.RETRY_PENDING: frozenset({JobState.RUNNING, JobState.FAILED, JobState.CANCELLED}),
    JobState.COMPLETED: frozenset(),
    JobState.FAILED: frozenset(),
    JobState.CANCELLED: frozenset(),
}


class JobStateMachine:
    """Validate transitions and emit immutable auditable state records."""

    def can_transition(self, current: JobState, target: JobState) -> bool:
        return target in _ALLOWED[current]

    def transition(
        self,
        job_id: str,
        current: JobState,
        target: JobState,
        reason: str,
        *,
        timestamp: datetime | None = None,
    ) -> JobStateRecord:
        if not self.can_transition(current, target):
            raise JobStateTransitionError(
                f"invalid job-state transition: {current.value} -> {target.value}"
            )
        return JobStateRecord(
            job_id=job_id,
            previous_state=current,
            new_state=target,
            reason=reason,
            timestamp=timestamp or datetime.now(timezone.utc),
        )
