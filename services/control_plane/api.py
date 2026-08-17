"""Authenticated local command/query API with durable SQLite state."""

from __future__ import annotations

import hashlib
import hmac
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from packages.contracts.ilaios_contracts import ContractKind, SchemaVersion
from services.control_plane.migrations import migrate_database
from services.control_plane.proposals import (
    BudgetEnvelope,
    DataClass,
    GoalSpec,
    ProposedTask,
    RiskClass,
    propose_execution,
)
from src.video_automation.job_state_machine import JobStateMachine
from src.video_automation.models import JobState


class AuthenticationError(PermissionError):
    """Raised when a local control-plane request is unauthenticated."""


class ControlPlaneError(ValueError):
    """Raised when a command or query violates control-plane invariants."""


@dataclass(frozen=True, slots=True)
class ControlPlaneConfig:
    database_path: Path
    bearer_token: str

    def __post_init__(self) -> None:
        if not self.bearer_token or self.bearer_token != self.bearer_token.strip():
            raise ControlPlaneError("bearer_token must be non-blank and trimmed")


@dataclass(frozen=True, slots=True)
class GoalRecord:
    goal_id: str
    objective: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class JobRecord:
    job_id: str
    goal_id: str
    state: JobState
    created_at: datetime


class ControlPlane:
    """Authoritative command/query boundary; projections own no state."""

    def __init__(self, config: ControlPlaneConfig) -> None:
        self._config = config
        config.database_path.parent.mkdir(parents=True, exist_ok=True)
        migrate_database(config.database_path)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._config.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _authenticate(self, token: str) -> None:
        if not hmac.compare_digest(token, self._config.bearer_token):
            raise AuthenticationError("invalid local bearer token")

    def authenticate(self, token: str) -> None:
        """Validate a transport credential before non-control-plane dispatch."""
        self._authenticate(token)

    @property
    def database_path(self) -> Path:
        return self._config.database_path

    def create_goal(self, token: str, objective: str) -> GoalRecord:
        self._authenticate(token)
        if not objective or objective != objective.strip():
            raise ControlPlaneError("objective must be non-blank and trimmed")
        with self._connect() as connection:
            sequence = connection.execute("SELECT COUNT(*) + 1 FROM goals").fetchone()[0]
            record = GoalRecord(
                goal_id=f"goal-{sequence:08d}",
                objective=objective,
                created_at=datetime.now(timezone.utc),
            )
            connection.execute(
                "INSERT INTO goals VALUES (?, ?, ?)",
                (record.goal_id, record.objective, record.created_at.isoformat()),
            )
            self._append_event(
                connection,
                "goal.created",
                record.goal_id,
                {"objective": objective},
                record.created_at,
            )
        return record

    def create_job(self, token: str, goal_id: str) -> JobRecord:
        self._authenticate(token)
        goal = self.get_goal(token, goal_id)
        with self._connect() as connection:
            sequence = connection.execute("SELECT COUNT(*) + 1 FROM jobs").fetchone()[0]
            record = JobRecord(
                job_id=f"job-{sequence:08d}",
                goal_id=goal.goal_id,
                state=JobState.PENDING,
                created_at=datetime.now(timezone.utc),
            )
            connection.execute(
                "INSERT INTO jobs VALUES (?, ?, ?, ?)",
                (
                    record.job_id,
                    record.goal_id,
                    record.state.value,
                    record.created_at.isoformat(),
                ),
            )
            self._append_event(
                connection,
                "job.created",
                record.job_id,
                {"goal_id": record.goal_id, "state": record.state.value},
                record.created_at,
            )
        return record

    def get_goal(self, token: str, goal_id: str) -> GoalRecord:
        self._authenticate(token)
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM goals WHERE goal_id = ?", (goal_id,)
            ).fetchone()
        if row is None:
            raise ControlPlaneError("unknown goal_id")
        return GoalRecord(
            row["goal_id"],
            row["objective"],
            datetime.fromisoformat(row["created_at"]),
        )

    def get_job(self, token: str, job_id: str) -> JobRecord:
        self._authenticate(token)
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM jobs WHERE job_id = ?", (job_id,)
            ).fetchone()
        if row is None:
            raise ControlPlaneError("unknown job_id")
        return JobRecord(
            row["job_id"],
            row["goal_id"],
            JobState(row["state"]),
            datetime.fromisoformat(row["created_at"]),
        )

    def transition_job(
        self,
        token: str,
        job_id: str,
        target: JobState,
        *,
        reason: str,
        now: datetime,
    ) -> JobRecord:
        """Apply a canonical durable job-state transition."""
        self._authenticate(token)
        current = self.get_job(token, job_id)
        transition = JobStateMachine().transition(
            job_id, current.state, target, reason, timestamp=now
        )
        with self._connect() as connection:
            connection.execute(
                "UPDATE jobs SET state = ? WHERE job_id = ?",
                (transition.new_state.value, job_id),
            )
            self._append_event(
                connection,
                "job.updated",
                job_id,
                {
                    "previous_state": current.state.value,
                    "state": transition.new_state.value,
                    "reason": transition.reason,
                },
                transition.timestamp,
            )
        return JobRecord(job_id, current.goal_id, transition.new_state, current.created_at)

    def create_proposal(
        self,
        token: str,
        goal_id: str,
        *,
        acceptance_criteria: tuple[str, ...],
        risk_class: RiskClass,
        data_class: DataClass,
        budget: BudgetEnvelope,
        tasks: tuple[ProposedTask, ...],
    ) -> dict[str, object]:
        """Create an inspectable bounded proposal with no execution authority.

        The canonical proposal hash is a content identity. A second goal may
        legitimately request the exact same content, so durable storage scopes
        an otherwise-colliding content identity to that goal instead of treating
        a repeated user request as an integrity failure.
        """
        self._authenticate(token)
        goal = self.get_goal(token, goal_id)
        proposal = propose_execution(
            GoalSpec(
                objective=goal.objective,
                acceptance_criteria=acceptance_criteria,
                risk_class=risk_class,
                data_class=data_class,
                budget=budget,
            ),
            tasks,
        )
        inspected = proposal.inspect()
        serialized = json.dumps(inspected, sort_keys=True, separators=(",", ":"))
        created_at = datetime.now(timezone.utc)
        with self._connect() as connection:
            existing = connection.execute(
                "SELECT goal_id, proposal_json FROM proposals WHERE proposal_id = ?",
                (proposal.proposal_id,),
            ).fetchone()
            storage_id = proposal.proposal_id
            if existing is not None:
                if existing["goal_id"] == goal_id and existing["proposal_json"] == serialized:
                    return inspected
                storage_id = "proposal-" + hashlib.sha256(
                    f"{proposal.proposal_id}|{goal_id}".encode("utf-8")
                ).hexdigest()[:24]
                inspected = dict(inspected)
                inspected["proposal_id"] = storage_id
                serialized = json.dumps(
                    inspected, sort_keys=True, separators=(",", ":")
                )
                scoped = connection.execute(
                    "SELECT goal_id, proposal_json FROM proposals WHERE proposal_id = ?",
                    (storage_id,),
                ).fetchone()
                if scoped is not None:
                    if scoped["goal_id"] == goal_id and scoped["proposal_json"] == serialized:
                        return inspected
                    raise ControlPlaneError("proposal identity collision")
            connection.execute(
                "INSERT INTO proposals VALUES (?, ?, ?, ?)",
                (storage_id, goal_id, serialized, created_at.isoformat()),
            )
            self._append_event(
                connection,
                "proposal.created",
                storage_id,
                {"goal_id": goal_id},
                created_at,
            )
        return inspected

    def get_proposal(self, token: str, proposal_id: str) -> dict[str, object]:
        """Read a durable proposal through the authoritative query boundary."""
        self._authenticate(token)
        with self._connect() as connection:
            row = connection.execute(
                "SELECT proposal_json FROM proposals WHERE proposal_id = ?",
                (proposal_id,),
            ).fetchone()
        if row is None:
            raise ControlPlaneError("unknown proposal_id")
        value = json.loads(row["proposal_json"])
        if not isinstance(value, dict):
            raise ControlPlaneError("stored proposal is malformed")
        return dict(value)

    def list_events(self, token: str) -> tuple[dict[str, Any], ...]:
        self._authenticate(token)
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM events ORDER BY sequence"
            ).fetchall()
        return tuple(
            {
                "sequence": row["sequence"],
                "event_type": row["event_type"],
                "aggregate_id": row["aggregate_id"],
                "payload": json.loads(row["payload_json"]),
                "occurred_at": row["occurred_at"],
                "schema_version": row["schema_version"],
                "kind": ContractKind.EVENT.value,
            }
            for row in rows
        )

    @staticmethod
    def _append_event(
        connection: sqlite3.Connection,
        event_type: str,
        aggregate_id: str,
        payload: dict[str, str],
        occurred_at: datetime,
    ) -> None:
        connection.execute(
            "INSERT INTO events "
            "(event_type, aggregate_id, payload_json, occurred_at, schema_version) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                event_type,
                aggregate_id,
                json.dumps(payload, sort_keys=True),
                occurred_at.isoformat(),
                SchemaVersion.V1.value,
            ),
        )
