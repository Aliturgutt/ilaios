from __future__ import annotations

from datetime import datetime, timezone

from src.video_automation.series_cadence import SeriesCadence, SeriesCadenceKind


def test_daily_cadence_runs_once_per_local_day_after_target_time() -> None:
    cadence = SeriesCadence(
        kind=SeriesCadenceKind.DAILY,
        timezone_name="Europe/Istanbul",
        local_hour=19,
    )
    before = datetime(2026, 8, 14, 15, 0, tzinfo=timezone.utc)  # 18:00 Istanbul
    due = datetime(2026, 8, 14, 16, 0, tzinfo=timezone.utc)  # 19:00 Istanbul
    assert not cadence.due(now=before, last_scheduled_at=None)
    assert cadence.due(now=due, last_scheduled_at=None)
    assert not cadence.due(now=due, last_scheduled_at=due)


def test_selected_weekday_cadence_respects_local_weekday() -> None:
    cadence = SeriesCadence(
        kind=SeriesCadenceKind.SELECTED_WEEKDAYS,
        timezone_name="Europe/Istanbul",
        local_hour=19,
        weekdays=(0, 2, 4),
    )
    friday = datetime(2026, 8, 14, 16, 30, tzinfo=timezone.utc)
    saturday = datetime(2026, 8, 15, 16, 30, tzinfo=timezone.utc)
    assert cadence.due(now=friday, last_scheduled_at=None)
    assert not cadence.due(now=saturday, last_scheduled_at=None)


def test_user_interval_cadence_enforces_elapsed_local_days() -> None:
    cadence = SeriesCadence(
        kind=SeriesCadenceKind.INTERVAL_DAYS,
        timezone_name="Europe/Istanbul",
        local_hour=10,
        interval_days=3,
    )
    last = datetime(2026, 8, 11, 7, 0, tzinfo=timezone.utc)
    too_early = datetime(2026, 8, 13, 8, 0, tzinfo=timezone.utc)
    due = datetime(2026, 8, 14, 8, 0, tzinfo=timezone.utc)
    assert not cadence.due(now=too_early, last_scheduled_at=last)
    assert cadence.due(now=due, last_scheduled_at=last)
