"""Series episode scheduling through the existing ILAIOS scheduler authority."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from .series_state import EpisodeProgressState, SeriesStateError, SeriesStateStore

SERIES_EPISODE_CAPABILITY = "video.series.episode"


@dataclass(frozen=True, slots=True)
class SeriesLease:
    """Minimal immutable lease view consumed by the Video Factory domain."""

    task_id: str
    worker_id: str
    fencing_token: int
    expires_at: datetime


class SeriesSchedulingUnavailableError(PermissionError):
    """Raised by a runtime adapter when governed scheduling fails closed."""


class SeriesScheduler(Protocol):
    """Narrow contract implemented by the canonical scheduler adapter."""

    def schedule(
        self,
        task_id: str,
        capability: str,
        *,
        now: datetime,
    ) -> SeriesLease: ...


@dataclass(frozen=True, slots=True)
class ScheduledSeriesEpisode:
    series_id: str
    episode_id: str
    episode_number: int
    task_id: str
    lease: SeriesLease


class SeriesEpisodeScheduler:
    """Create a governed episode job without directly invoking any provider."""

    def __init__(self, *, state_store: SeriesStateStore, scheduler: SeriesScheduler) -> None:
        self._state_store = state_store
        self._scheduler = scheduler

    def schedule_next(
        self,
        *,
        series_id: str,
        episode_id: str,
        now: datetime,
    ) -> ScheduledSeriesEpisode:
        state = self._state_store.load_series(series_id)
        episode_number = state.next_episode_number
        self._state_store.begin_episode(
            series_id=series_id,
            episode_id=episode_id,
            episode_number=episode_number,
            checkpoint="SCHEDULER_JOB_CREATED",
        )
        progress, _ = self._state_store.episode_progress(
            series_id=series_id,
            episode_id=episode_id,
        )
        if progress is EpisodeProgressState.ACCEPTED:
            raise SeriesStateError("accepted episode cannot be scheduled again")
        task_id = f"series:{series_id}:episode:{episode_number}:{episode_id}"
        try:
            lease = self._scheduler.schedule(
                task_id,
                SERIES_EPISODE_CAPABILITY,
                now=now,
            )
        except PermissionError:
            self._state_store.checkpoint_episode(
                series_id=series_id,
                episode_id=episode_id,
                checkpoint="SCHEDULER_UNAVAILABLE",
                incomplete=True,
            )
            raise
        self._state_store.checkpoint_episode(
            series_id=series_id,
            episode_id=episode_id,
            checkpoint="GOVERNED_JOB_LEASED",
        )
        return ScheduledSeriesEpisode(
            series_id=series_id,
            episode_id=episode_id,
            episode_number=episode_number,
            task_id=task_id,
            lease=lease,
        )
