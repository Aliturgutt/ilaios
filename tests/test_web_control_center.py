"""Web/Desktop semantic parity tests for PLATFORM.P16."""

from __future__ import annotations

from pathlib import Path

import pytest

from apps.web import WebControlCenter
from services.control_plane import AuthenticationError, ControlPlane, ControlPlaneConfig


def test_web_uses_authoritative_commands_queries_and_events(tmp_path: Path) -> None:
    control = ControlPlane(ControlPlaneConfig(tmp_path / "state.sqlite3", "token"))
    web = WebControlCenter(control, "token")
    goal = web.create_goal("Governed web request")
    job = web.create_job(goal.goal_id)
    projection = web.project()

    assert control.get_goal("token", goal.goal_id) == goal
    assert control.get_job("token", job.job_id) == job
    assert projection.schema_version == "1.0"
    assert (projection.goal_count, projection.job_count) == (1, 1)
    assert projection.last_event == "job.created"


def test_web_cannot_bypass_control_plane_authentication(tmp_path: Path) -> None:
    control = ControlPlane(ControlPlaneConfig(tmp_path / "state.sqlite3", "token"))
    web = WebControlCenter(control, "wrong")

    with pytest.raises(AuthenticationError):
        web.create_goal("Bypass attempt")
    with pytest.raises(AuthenticationError):
        web.project()
