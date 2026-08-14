"""Adapter from the canonical worker scheduler to the Video Factory series contract."""

from __future__ import annotations

from datetime import datetime

from services.runtime.scheduler import Lease, SchedulingError, WorkerScheduler
from src.video_automation.series_scheduler import SeriesSchedulingUnavailableError


class GovernedSeriesSchedulerAdapter:
    """Reuse the canonical WorkerScheduler without exposing services into src."""

    def __init__(self, scheduler: WorkerScheduler) -> None:
        self._scheduler = scheduler

    def schedule(self, task_id: str, capability: str, *, now: datetime) -> Lease:
        try:
            return self._scheduler.schedule(task_id, capability, now=now)
        except SchedulingError as exc:
            raise SeriesSchedulingUnavailableError(str(exc)) from exc
