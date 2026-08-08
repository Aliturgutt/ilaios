from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.video_automation.job_state_machine import (
    JobStateMachine,
    JobStateTransitionError,
)
from src.video_automation.models import JobState


def test_valid_transition_emits_auditable_record() -> None:
    machine = JobStateMachine()
    timestamp = datetime.now(timezone.utc)
    record = machine.transition(
        "job-1",
        JobState.PENDING,
        JobState.RUNNING,
        "execution started",
        timestamp=timestamp,
    )
    assert record.previous_state is JobState.PENDING
    assert record.new_state is JobState.RUNNING
    assert record.timestamp == timestamp


def test_invalid_transition_fails_closed() -> None:
    with pytest.raises(JobStateTransitionError, match="invalid"):
        JobStateMachine().transition(
            "job-1",
            JobState.PENDING,
            JobState.COMPLETED,
            "skip",
        )


def test_terminal_states_do_not_advance() -> None:
    machine = JobStateMachine()
    assert machine.can_transition(JobState.COMPLETED, JobState.RUNNING) is False
    assert machine.can_transition(JobState.FAILED, JobState.RUNNING) is False
    assert machine.can_transition(JobState.CANCELLED, JobState.RUNNING) is False
