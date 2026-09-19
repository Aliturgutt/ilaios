"""Bind daily YouTube orchestration to the canonical worker scheduler.

This adapter does not create a scheduler, retry loop, Video runtime, publisher,
or publication ledger. It acquires one fenced lease from the existing
``WorkerScheduler`` immediately before invoking the existing daily orchestrator,
and completes that exact lease only after the bounded invocation returns.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone

from services.runtime.scheduler import SchedulingError, WorkerScheduler
from src.video_automation.daily_topic_selection import DailyChannelPolicy
from src.video_automation.daily_youtube_orchestration import (
    DailyYouTubeOrchestrationError,
    DailyYouTubeOrchestrator,
)
from src.video_automation.daily_youtube_planning import (
    DailySourceObservation,
    YouTubeEditorialPolicy,
)
from src.video_automation.guarded_publishing import GuardedPublicationResult


class GovernedDailyYouTubeSchedulerAdapter:
    """Invoke one daily Video attempt under an existing fenced worker lease."""

    def __init__(
        self,
        scheduler: WorkerScheduler,
        orchestrator: DailyYouTubeOrchestrator,
        *,
        capability: str = "video.daily.execute",
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if not capability.strip() or capability != capability.strip():
            raise DailyYouTubeOrchestrationError(
                "daily scheduler capability must be normalized non-empty text"
            )
        self._scheduler = scheduler
        self._orchestrator = orchestrator
        self._capability = capability
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def run_once(
        self,
        *,
        task_id: str,
        observations: tuple[DailySourceObservation, ...],
        channel_policy: DailyChannelPolicy,
        youtube_policy: YouTubeEditorialPolicy,
        scheduled_at: datetime,
        recent_topic_ids: tuple[str, ...] = (),
        recent_content_fingerprints: tuple[str, ...] = (),
        topic_now: datetime | None = None,
    ) -> GuardedPublicationResult | None:
        """Run one orchestrator attempt under exactly one canonical worker lease."""

        if not task_id.strip() or task_id != task_id.strip():
            raise DailyYouTubeOrchestrationError(
                "daily scheduler task_id must be normalized non-empty text"
            )
        started_at = self._lease_time()
        try:
            lease = self._scheduler.schedule(
                task_id,
                self._capability,
                now=started_at,
            )
            self._scheduler.authorize_side_effect(lease, now=started_at)
        except SchedulingError as error:
            raise DailyYouTubeOrchestrationError(str(error)) from error

        try:
            result = self._orchestrator.run_once(
                observations=observations,
                channel_policy=channel_policy,
                youtube_policy=youtube_policy,
                scheduled_at=scheduled_at,
                recent_topic_ids=recent_topic_ids,
                recent_content_fingerprints=recent_content_fingerprints,
                now=topic_now,
            )
        except Exception:
            # Keep the lease active until its canonical expiry. Immediate replay
            # could duplicate provider or publication side effects after an
            # ambiguous failure.
            raise

        try:
            self._scheduler.complete(lease, now=self._lease_time())
        except SchedulingError as error:
            raise DailyYouTubeOrchestrationError(
                "daily Video execution completed after its worker lease became invalid"
            ) from error
        return result

    def _lease_time(self) -> datetime:
        value = self._clock()
        if value.tzinfo is None or value.utcoffset() is None:
            raise DailyYouTubeOrchestrationError(
                "daily scheduler clock must return timezone-aware datetime"
            )
        return value


__all__ = ["GovernedDailyYouTubeSchedulerAdapter"]
