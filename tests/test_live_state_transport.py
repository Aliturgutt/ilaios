"""Replay, reconnect, reorder, and DLP tests for PLATFORM.P08."""

from __future__ import annotations

from pathlib import Path

import pytest

from services.control_plane import (
    LiveStateError,
    LiveStateProjection,
    LiveStateTransport,
)


def test_authoritative_state_survives_restart_and_reconnect(tmp_path: Path) -> None:
    database = tmp_path / "live.sqlite3"
    first = LiveStateTransport(database)
    created = first.publish("job-1", "job.created", {"state": "pending"})
    first.publish("job-1", "job.started", {"state": "running"})

    restarted = LiveStateTransport(database)
    replay = restarted.replay(after_sequence=created.sequence)
    assert [event.event_type for event in replay] == ["job.started"]
    assert restarted.snapshot("job-1").state == {"state": "running"}


def test_reordered_delivery_reconciles_by_authoritative_sequence(tmp_path: Path) -> None:
    transport = LiveStateTransport(tmp_path / "live.sqlite3")
    transport.publish("job-1", "job.created", {"state": "pending"})
    transport.publish("job-1", "job.started", {"state": "running"})
    transport.publish("job-1", "job.completed", {"state": "completed"})
    events = transport.replay()

    projection = LiveStateProjection()
    projection.reconcile(tuple(reversed(events)))

    assert projection.last_sequence == 3
    assert projection.state("job-1") == {"state": "completed"}


def test_sensitive_values_are_redacted_before_persistence(tmp_path: Path) -> None:
    transport = LiveStateTransport(tmp_path / "live.sqlite3")
    event = transport.publish(
        "job-1",
        "job.configured",
        {"token": "raw-token", "nested": {"password": "raw-password"}},
    )

    assert event.state == {
        "token": "[REDACTED]",
        "nested": {"password": "[REDACTED]"},
    }
    assert "raw-token" not in (tmp_path / "live.sqlite3").read_bytes().decode(
        errors="ignore"
    )


def test_projection_fails_closed_on_sequence_gap(tmp_path: Path) -> None:
    transport = LiveStateTransport(tmp_path / "live.sqlite3")
    transport.publish("job-1", "job.created", {"state": "pending"})
    second = transport.publish("job-1", "job.started", {"state": "running"})

    with pytest.raises(LiveStateError, match="gap"):
        LiveStateProjection().reconcile((second,))


def test_projection_recovers_from_authoritative_snapshot(tmp_path: Path) -> None:
    transport = LiveStateTransport(tmp_path / "live.sqlite3")
    transport.publish("job-1", "job.created", {"state": "pending"})
    transport.publish("job-1", "job.started", {"state": "running"})

    projection = LiveStateProjection()
    projection.restore_snapshot(transport.snapshot("job-1"))

    assert projection.last_sequence == 2
    assert projection.state("job-1") == {"state": "running"}
