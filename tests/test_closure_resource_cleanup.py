"""Red-team closure tests for durable resource cleanup."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from services.control_plane import ControlPlane, ControlPlaneConfig
from services.runtime import DurableWorkerScheduler, SchedulingError, WorkerProfile


def _scheduler(tmp_path: Path) -> DurableWorkerScheduler:
    state = tmp_path / "state.sqlite3"
    ControlPlane(ControlPlaneConfig(state, "token"))
    scheduler = DurableWorkerScheduler(state, lease_duration=timedelta(seconds=30))
    scheduler.register(WorkerProfile("worker-1", frozenset({"video"}), 1))
    return scheduler


def test_current_lease_release_is_idempotent_and_removes_resource(tmp_path: Path) -> None:
    scheduler = _scheduler(tmp_path)
    now = datetime(2026, 8, 16, 0, 0, tzinfo=timezone.utc)
    lease = scheduler.schedule("task-1", "video", now=now)

    assert scheduler.release(lease) is True
    assert scheduler.release(lease) is False
    assert scheduler.state()["leases"] == []


def test_stale_fence_cannot_release_replacement_lease(tmp_path: Path) -> None:
    scheduler = _scheduler(tmp_path)
    now = datetime(2026, 8, 16, 0, 0, tzinfo=timezone.utc)
    first = scheduler.schedule("task-1", "video", now=now)
    replacement = scheduler.reschedule_expired(
        "task-1", "video", now=now + timedelta(seconds=31)
    )

    with pytest.raises(SchedulingError, match="stale or replaced"):
        scheduler.release(first)
    assert scheduler.release(replacement) is True
    assert scheduler.state()["leases"] == []


def test_terminal_worker_unregister_is_idempotent(tmp_path: Path) -> None:
    scheduler = _scheduler(tmp_path)
    assert len(scheduler.state()["workers"]) == 1

    assert scheduler.unregister("worker-1") is True
    assert scheduler.unregister("worker-1") is False
    assert scheduler.state()["workers"] == []


def test_worker_cannot_be_unregistered_while_any_lease_is_owned(tmp_path: Path) -> None:
    scheduler = _scheduler(tmp_path)
    now = datetime(2026, 8, 16, 0, 0, tzinfo=timezone.utc)
    lease = scheduler.schedule("task-1", "video", now=now)

    with pytest.raises(SchedulingError, match="worker with lease"):
        scheduler.unregister("worker-1")
    assert len(scheduler.state()["workers"]) == 1

    assert scheduler.release(lease) is True
    assert scheduler.unregister("worker-1") is True
    assert scheduler.state()["workers"] == []
