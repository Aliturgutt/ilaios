from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import cast

import pytest

from services.integrations.video_daily_scheduler import (
    GovernedDailyYouTubeSchedulerAdapter,
)
from services.runtime.scheduler import WorkerProfile, WorkerScheduler
from src.video_automation.daily_topic_selection import DailyChannelPolicy
from src.video_automation.daily_youtube_orchestration import (
    DailyYouTubeOrchestrationError,
    DailyYouTubeOrchestrator,
)
from src.video_automation.daily_youtube_planning import YouTubeEditorialPolicy


class _FakeDailyOrchestrator:
    def __init__(self, *, fail: bool = False) -> None:
        self.calls = 0
        self.fail = fail

    def run_once(self, **_: object) -> None:
        self.calls += 1
        if self.fail:
            raise RuntimeError("ambiguous daily failure")


def _scheduler() -> WorkerScheduler:
    scheduler = WorkerScheduler(lease_duration=timedelta(minutes=10))
    scheduler.register(
        WorkerProfile(
            worker_id="video-worker-001",
            capabilities=frozenset({"video.daily.execute"}),
            max_concurrent_tasks=1,
        )
    )
    return scheduler


def _run(
    adapter: GovernedDailyYouTubeSchedulerAdapter,
    *,
    task_id: str = "daily-2026-09-12",
) -> None:
    now = datetime(2026, 9, 12, 15, 0, tzinfo=timezone.utc)
    result = adapter.run_once(
        task_id=task_id,
        observations=(),
        channel_policy=cast(DailyChannelPolicy, object()),
        youtube_policy=cast(YouTubeEditorialPolicy, object()),
        scheduled_at=now,
        topic_now=now,
    )
    assert result is None


def test_daily_scheduler_invokes_orchestrator_under_canonical_worker_lease() -> None:
    now = datetime(2026, 9, 12, 15, 0, tzinfo=timezone.utc)
    orchestrator = _FakeDailyOrchestrator()
    adapter = GovernedDailyYouTubeSchedulerAdapter(
        _scheduler(),
        cast(DailyYouTubeOrchestrator, orchestrator),
        clock=lambda: now,
    )

    _run(adapter)
    _run(adapter)

    assert orchestrator.calls == 2


def test_daily_scheduler_keeps_failed_attempt_leased_to_block_immediate_replay() -> None:
    now = datetime(2026, 9, 12, 15, 0, tzinfo=timezone.utc)
    orchestrator = _FakeDailyOrchestrator(fail=True)
    adapter = GovernedDailyYouTubeSchedulerAdapter(
        _scheduler(),
        cast(DailyYouTubeOrchestrator, orchestrator),
        clock=lambda: now,
    )

    with pytest.raises(RuntimeError, match="ambiguous daily failure"):
        _run(adapter)
    with pytest.raises(DailyYouTubeOrchestrationError, match="active lease"):
        _run(adapter)

    assert orchestrator.calls == 1


def test_daily_scheduler_fails_closed_without_capable_worker() -> None:
    now = datetime(2026, 9, 12, 15, 0, tzinfo=timezone.utc)
    scheduler = WorkerScheduler(lease_duration=timedelta(minutes=10))
    orchestrator = _FakeDailyOrchestrator()
    adapter = GovernedDailyYouTubeSchedulerAdapter(
        scheduler,
        cast(DailyYouTubeOrchestrator, orchestrator),
        clock=lambda: now,
    )

    with pytest.raises(DailyYouTubeOrchestrationError, match="no worker"):
        _run(adapter)

    assert orchestrator.calls == 0


def test_daily_scheduler_rejects_naive_clock() -> None:
    orchestrator = _FakeDailyOrchestrator()
    adapter = GovernedDailyYouTubeSchedulerAdapter(
        _scheduler(),
        cast(DailyYouTubeOrchestrator, orchestrator),
        clock=lambda: datetime(2026, 9, 12, 15, 0),
    )

    with pytest.raises(DailyYouTubeOrchestrationError, match="timezone-aware"):
        _run(adapter)

    assert orchestrator.calls == 0
