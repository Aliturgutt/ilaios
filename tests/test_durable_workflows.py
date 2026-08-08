"""Crash/restart and duplicate-event recovery tests for PLATFORM.P07."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from services.control_plane import WorkflowError, WorkflowStore, WorkflowStoreConfig


def _store(tmp_path: Path) -> WorkflowStore:
    return WorkflowStore(WorkflowStoreConfig(tmp_path / "workflows.sqlite3"))


def test_checkpoint_and_attempt_survive_crash_restart(tmp_path: Path) -> None:
    first = _store(tmp_path)
    first.create_workflow("workflow-1")
    first.add_task("workflow-1", "render", max_attempts=2)
    deadline = datetime.now(timezone.utc) + timedelta(minutes=5)
    attempt = first.begin_attempt("workflow-1", "render", deadline=deadline)
    first.save_checkpoint(attempt.attempt_id, "frame", {"number": 42})

    restarted = _store(tmp_path)
    assert restarted.load_checkpoint(attempt.attempt_id, "frame") == {"number": 42}
    assert restarted.fail_attempt(attempt.attempt_id, reason="worker lost") == "ready"
    retry = restarted.begin_attempt("workflow-1", "render", deadline=deadline)
    assert retry.number == 2
    restarted.complete_attempt(retry.attempt_id)


def test_timeout_retry_exhaustion_creates_durable_compensation(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.create_workflow("workflow-2")
    store.add_task(
        "workflow-2",
        "publish",
        max_attempts=1,
        compensation_event_type="publication.rollback.requested",
    )
    deadline = datetime.now(timezone.utc) - timedelta(seconds=1)
    attempt = store.begin_attempt("workflow-2", "publish", deadline=deadline)

    assert store.timeout_attempt(attempt.attempt_id, now=datetime.now(timezone.utc)) == "failed"
    restarted = _store(tmp_path)
    pending = restarted.pending_outbox()
    assert len(pending) == 1
    assert pending[0].event_type == "publication.rollback.requested"
    assert pending[0].payload["task_id"] == "publish"
    restarted.acknowledge_outbox(pending[0].event_id)
    assert restarted.pending_outbox() == ()


def test_duplicate_inbox_event_is_idempotent_after_restart(tmp_path: Path) -> None:
    first = _store(tmp_path)
    assert first.receive_event("event-1", {"state": "ready"}) is True

    restarted = _store(tmp_path)
    assert restarted.receive_event("event-1", {"state": "ready"}) is False


def test_attempt_transitions_fail_closed(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.create_workflow("workflow-3")
    store.add_task("workflow-3", "task", max_attempts=1)
    deadline = datetime.now(timezone.utc) + timedelta(minutes=1)
    attempt = store.begin_attempt("workflow-3", "task", deadline=deadline)
    with pytest.raises(WorkflowError, match="has not elapsed"):
        store.timeout_attempt(attempt.attempt_id, now=datetime.now(timezone.utc))
