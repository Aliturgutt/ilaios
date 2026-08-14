"""Deterministic user-defined cadence policy for autonomous series goals."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .series_state import SeriesStateError


class SeriesCadenceKind(str, Enum):
    DAILY = "DAILY"
    SELECTED_WEEKDAYS = "SELECTED_WEEKDAYS"
    INTERVAL_DAYS = "INTERVAL_DAYS"


@dataclass(frozen=True, slots=True)
class SeriesCadence:
    kind: SeriesCadenceKind
    timezone_name: str
    local_hour: int
    local_minute: int = 0
    weekdays: tuple[int, ...] = ()
    interval_days: int | None = None

    def __post_init__(self) -> None:
        if not self.timezone_name or not self.timezone_name.strip():
            raise SeriesStateError("series cadence timezone_name must not be blank")
        try:
            ZoneInfo(self.timezone_name)
        except ZoneInfoNotFoundError as exc:
            raise SeriesStateError("series cadence timezone is unknown") from exc
        if not 0 <= self.local_hour <= 23:
            raise SeriesStateError("series cadence local_hour must be 0..23")
        if not 0 <= self.local_minute <= 59:
            raise SeriesStateError("series cadence local_minute must be 0..59")
        if len(self.weekdays) != len(set(self.weekdays)):
            raise SeriesStateError("series cadence weekdays must be unique")
        if any(day < 0 or day > 6 for day in self.weekdays):
            raise SeriesStateError("series cadence weekday must be 0..6")
        if self.kind is SeriesCadenceKind.SELECTED_WEEKDAYS and not self.weekdays:
            raise SeriesStateError("selected-weekday cadence requires weekdays")
        if self.kind is not SeriesCadenceKind.SELECTED_WEEKDAYS and self.weekdays:
            raise SeriesStateError("weekdays apply only to selected-weekday cadence")
        if self.kind is SeriesCadenceKind.INTERVAL_DAYS:
            if self.interval_days is None or self.interval_days < 1:
                raise SeriesStateError("interval cadence requires interval_days >= 1")
        elif self.interval_days is not None:
            raise SeriesStateError("interval_days applies only to interval cadence")

    def due(
        self,
        *,
        now: datetime,
        last_scheduled_at: datetime | None,
    ) -> bool:
        """Return whether a new governed episode job is due at this instant."""

        _aware("now", now)
        if last_scheduled_at is not None:
            _aware("last_scheduled_at", last_scheduled_at)
        zone = ZoneInfo(self.timezone_name)
        local_now = now.astimezone(zone)
        if (local_now.hour, local_now.minute) < (self.local_hour, self.local_minute):
            return False
        local_last = (
            None if last_scheduled_at is None else last_scheduled_at.astimezone(zone)
        )
        if self.kind is SeriesCadenceKind.DAILY:
            return local_last is None or local_last.date() < local_now.date()
        if self.kind is SeriesCadenceKind.SELECTED_WEEKDAYS:
            if local_now.weekday() not in self.weekdays:
                return False
            return local_last is None or local_last.date() < local_now.date()
        if local_last is None:
            return True
        assert self.interval_days is not None
        return (local_now.date() - local_last.date()).days >= self.interval_days


def _aware(name: str, value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise SeriesStateError(f"series cadence {name} must be timezone-aware")
