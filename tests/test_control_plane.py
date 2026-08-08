"""Authoritative local control-plane tests for PLATFORM.P05."""

from __future__ import annotations

from pathlib import Path

import pytest

from services.control_plane import (
    AuthenticationError,
    ControlPlane,
    ControlPlaneConfig,
)
from src.video_automation.models import JobState


def _control_plane(tmp_path: Path) -> ControlPlane:
    return ControlPlane(ControlPlaneConfig(tmp_path / "state.sqlite3", "local-secret"))


def test_real_goal_and_job_persist_across_instances(tmp_path: Path) -> None:
    first = _control_plane(tmp_path)
    goal = first.create_goal("local-secret", "Render governed launch video")
    job = first.create_job("local-secret", goal.goal_id)

    second = _control_plane(tmp_path)
    assert second.get_goal("local-secret", goal.goal_id) == goal
    assert second.get_job("local-secret", job.job_id) == job
    assert job.state is JobState.PENDING
    assert goal.goal_id == "goal-00000001"
    assert job.job_id == "job-00000001"


def test_command_query_and_event_boundaries_share_durable_identity(tmp_path: Path) -> None:
    control_plane = _control_plane(tmp_path)
    goal = control_plane.create_goal("local-secret", "Build a deterministic DAG")
    job = control_plane.create_job("local-secret", goal.goal_id)
    events = control_plane.list_events("local-secret")

    assert [event["event_type"] for event in events] == [
        "goal.created",
        "job.created",
    ]
    assert events[0]["aggregate_id"] == goal.goal_id
    assert events[1]["aggregate_id"] == job.job_id
    assert all(event["schema_version"] == "1.0" for event in events)


def test_every_command_and_query_requires_authentication(tmp_path: Path) -> None:
    control_plane = _control_plane(tmp_path)
    with pytest.raises(AuthenticationError):
        control_plane.create_goal("wrong", "Denied goal")
    with pytest.raises(AuthenticationError):
        control_plane.get_goal("wrong", "goal-missing")
    with pytest.raises(AuthenticationError):
        control_plane.list_events("wrong")
