"""Non-authoritative web command/query/event projection."""

from __future__ import annotations

from dataclasses import dataclass

from packages.contracts.ilaios_contracts import SchemaVersion
from services.control_plane import ControlPlane, GoalRecord, JobRecord


@dataclass(frozen=True, slots=True)
class ControlCenterProjection:
    schema_version: str
    goal_count: int
    job_count: int
    last_event: str | None


class WebControlCenter:
    """Delegates all mutations and reads to the authoritative control plane."""

    def __init__(self, control_plane: ControlPlane, token: str) -> None:
        self._control_plane = control_plane
        self._token = token

    def create_goal(self, objective: str) -> GoalRecord:
        return self._control_plane.create_goal(self._token, objective)

    def create_job(self, goal_id: str) -> JobRecord:
        return self._control_plane.create_job(self._token, goal_id)

    def project(self) -> ControlCenterProjection:
        events = self._control_plane.list_events(self._token)
        goal_count = sum(event["event_type"] == "goal.created" for event in events)
        job_count = sum(event["event_type"] == "job.created" for event in events)
        return ControlCenterProjection(
            SchemaVersion.V1.value,
            goal_count,
            job_count,
            None if not events else str(events[-1]["event_type"]),
        )
