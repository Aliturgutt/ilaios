"""Crash/restart and duplicate-event recovery tests for PLATFORM.P07."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Barrier

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
    state = restarted.workflow_state("workflow-1")
    assert state["status"] == "completed"
    assert state["terminal"] is True


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
    state = restarted.workflow_state("workflow-2")
    assert state["status"] == "timed_out"
    assert state["reason"] == "deadline elapsed"


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


def test_completed_attempt_and_workflow_closure_are_idempotent(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.create_workflow("workflow-complete")
    store.add_task("workflow-complete", "task", max_attempts=1)
    attempt = store.begin_attempt(
        "workflow-complete",
        "task",
        deadline=datetime.now(timezone.utc) + timedelta(minutes=1),
    )

    store.complete_attempt(attempt.attempt_id)
    store.complete_attempt(attempt.attempt_id)

    state = store.workflow_state("workflow-complete")
    assert state["status"] == "completed"
    assert state["terminal"] is True
    assert state["reason"] == "all required workflow tasks completed"
    assert state["attempts"][0]["status"] == "completed"
    assert state["attempts"][0]["reason"] == "attempt completed"
    assert [event["event_type"] for event in store.closure_events("workflow-complete")] == [
        "attempt.completed",
        "workflow.completed",
    ]


def test_concurrent_duplicate_closure_serializes_to_one_terminal_event_pair(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    store.create_workflow("workflow-concurrent")
    store.add_task("workflow-concurrent", "task", max_attempts=1)
    attempt = store.begin_attempt(
        "workflow-concurrent",
        "task",
        deadline=datetime.now(timezone.utc) + timedelta(minutes=1),
    )
    barrier = Barrier(2)

    def close_once() -> None:
        concurrent_store = _store(tmp_path)
        barrier.wait()
        concurrent_store.complete_attempt(attempt.attempt_id)

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(close_once) for _ in range(2)]
        for future in futures:
            future.result()

    state = store.workflow_state("workflow-concurrent")
    assert state["status"] == "completed"
    assert [event["event_type"] for event in store.closure_events("workflow-concurrent")] == [
        "attempt.completed",
        "workflow.completed",
    ]


def test_exhausted_failure_persists_reason_and_terminal_status(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.create_workflow("workflow-failed")
    store.add_task("workflow-failed", "task", max_attempts=1)
    attempt = store.begin_attempt(
        "workflow-failed",
        "task",
        deadline=datetime.now(timezone.utc) + timedelta(minutes=1),
    )

    assert store.fail_attempt(attempt.attempt_id, reason="provider rejected request") == "failed"
    assert store.fail_attempt(attempt.attempt_id, reason="provider rejected request") == "failed"

    state = store.workflow_state("workflow-failed")
    assert state["status"] == "failed"
    assert state["reason"] == "provider rejected request"
    assert state["attempts"][0]["reason"] == "provider rejected request"


def test_partial_terminal_state_is_distinct_from_success(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.create_workflow("workflow-partial")
    store.add_task("workflow-partial", "first", max_attempts=1)
    store.add_task("workflow-partial", "second", max_attempts=1)
    deadline = datetime.now(timezone.utc) + timedelta(minutes=1)

    first = store.begin_attempt("workflow-partial", "first", deadline=deadline)
    store.complete_attempt(first.attempt_id)
    assert store.workflow_state("workflow-partial")["status"] == "active"

    second = store.begin_attempt("workflow-partial", "second", deadline=deadline)
    store.fail_attempt(second.attempt_id, reason="second task exhausted")
    state = store.workflow_state("workflow-partial")
    assert state["status"] == "partial"
    assert state["terminal"] is True
    assert state["reason"] == "second task exhausted"


def test_cancel_is_terminal_and_idempotent(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.create_workflow("workflow-cancel")
    store.add_task("workflow-cancel", "task", max_attempts=2)
    deadline = datetime.now(timezone.utc) + timedelta(minutes=1)
    store.begin_attempt("workflow-cancel", "task", deadline=deadline)
    now = datetime.now(timezone.utc)

    assert store.cancel_workflow("workflow-cancel", reason="operator cancelled", now=now) == "cancelled"
    assert store.cancel_workflow("workflow-cancel", reason="operator cancelled", now=now) == "cancelled"
    state = store.workflow_state("workflow-cancel")
    assert state["status"] == "cancelled"
    assert state["attempts"][0]["status"] == "cancelled"
    assert state["attempts"][0]["reason"] == "operator cancelled"


def test_orphaned_running_attempt_is_recovered_by_deadline(tmp_path: Path) -> None:
    first = _store(tmp_path)
    first.create_workflow("workflow-orphan")
    first.add_task("workflow-orphan", "task", max_attempts=1)
    deadline = datetime.now(timezone.utc) - timedelta(seconds=1)
    attempt = first.begin_attempt("workflow-orphan", "task", deadline=deadline)

    restarted = _store(tmp_path)
    recovered = restarted.recover_expired_attempts(now=datetime.now(timezone.utc))
    assert recovered == (attempt.attempt_id,)
    state = restarted.workflow_state("workflow-orphan")
    assert state["status"] == "timed_out"
    assert state["attempts"][0]["status"] == "timed_out"
    assert restarted.recover_expired_attempts(now=datetime.now(timezone.utc)) == ()


def test_closure_metrics_surface_terminal_and_retry_counts(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.create_workflow("workflow-metrics")
    store.add_task("workflow-metrics", "task", max_attempts=2)
    deadline = datetime.now(timezone.utc) + timedelta(minutes=1)
    first = store.begin_attempt("workflow-metrics", "task", deadline=deadline)
    store.fail_attempt(first.attempt_id, reason="retry once")
    second = store.begin_attempt("workflow-metrics", "task", deadline=deadline)
    store.complete_attempt(second.attempt_id)

    metrics = store.closure_metrics()
    assert metrics["completed"] == 1
    assert metrics["retry_count"] == 1
    assert metrics["running_attempt_count"] == 0
