"""Lease fencing and safe rescheduling tests for PLATFORM.P10."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from services.runtime import SchedulingError, WorkerProfile, WorkerScheduler


def _scheduler() -> WorkerScheduler:
    scheduler = WorkerScheduler(lease_duration=timedelta(seconds=30))
    scheduler.register(WorkerProfile("worker-b", frozenset({"render"}), 1))
    scheduler.register(WorkerProfile("worker-a", frozenset({"render"}), 1))
    return scheduler


def test_scheduling_is_deterministic_and_enforces_quota() -> None:
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    scheduler = _scheduler()
    first = scheduler.schedule("task-1", "render", now=now)
    second = scheduler.schedule("task-2", "render", now=now)

    assert first.worker_id == "worker-a"
    assert second.worker_id == "worker-b"
    with pytest.raises(SchedulingError, match="quota"):
        scheduler.schedule("task-3", "render", now=now)


def test_scheduling_ignores_expired_leases_in_load_selection() -> None:
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    scheduler = WorkerScheduler(lease_duration=timedelta(seconds=30))
    scheduler.register(WorkerProfile("worker-b", frozenset({"render"}), 2))
    scheduler.register(WorkerProfile("worker-a", frozenset({"render"}), 2))

    first = scheduler.schedule("task-1", "render", now=now)
    second = scheduler.schedule("task-2", "render", now=now)
    renewed_second = scheduler.heartbeat(
        second,
        now=now + timedelta(seconds=10),
    )
    after_first_expiry = now + timedelta(seconds=31)
    third = scheduler.schedule("task-3", "render", now=after_first_expiry)

    assert first.worker_id == "worker-a"
    assert renewed_second.worker_id == "worker-b"
    assert third.worker_id == "worker-a"


def test_lease_loss_and_split_brain_cannot_authorize_side_effects() -> None:
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    scheduler = _scheduler()
    stale = scheduler.schedule("task-1", "render", now=now)
    after_expiry = now + timedelta(seconds=31)
    replacement = scheduler.reschedule_expired(
        "task-1", "render", now=after_expiry
    )

    assert replacement.fencing_token == stale.fencing_token + 1
    with pytest.raises(SchedulingError, match="stale"):
        scheduler.authorize_side_effect(stale, now=after_expiry)
    scheduler.authorize_side_effect(replacement, now=after_expiry)


def test_heartbeat_renews_only_the_current_lease() -> None:
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    scheduler = _scheduler()
    lease = scheduler.schedule("task-1", "render", now=now)
    renewed = scheduler.heartbeat(lease, now=now + timedelta(seconds=10))

    assert renewed.expires_at == now + timedelta(seconds=40)
    with pytest.raises(SchedulingError, match="stale"):
        scheduler.authorize_side_effect(lease, now=now + timedelta(seconds=10))
