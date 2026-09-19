"""Durable workflow execution records and recovery primitives."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast


class WorkflowError(ValueError):
    """Raised when a durable workflow transition is invalid."""


@dataclass(frozen=True, slots=True)
class WorkflowStoreConfig:
    database_path: Path


@dataclass(frozen=True, slots=True)
class AttemptRecord:
    attempt_id: str
    workflow_id: str
    task_id: str
    number: int
    status: str
    deadline: datetime


@dataclass(frozen=True, slots=True)
class OutboxRecord:
    sequence: int
    event_id: str
    event_type: str
    payload: dict[str, Any]


_TERMINAL_WORKFLOW_STATES = frozenset(
    {"completed", "failed", "cancelled", "partial", "timed_out"}
)


class WorkflowStore:
    """SQLite-backed workflow state that remains authoritative after restart."""

    def __init__(self, config: WorkflowStoreConfig) -> None:
        self._config = config
        config.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._config.database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS workflows (
                    workflow_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS workflow_tasks (
                    workflow_id TEXT NOT NULL REFERENCES workflows(workflow_id),
                    task_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    max_attempts INTEGER NOT NULL,
                    compensation_event_type TEXT,
                    PRIMARY KEY (workflow_id, task_id)
                );
                CREATE TABLE IF NOT EXISTS attempts (
                    attempt_id TEXT PRIMARY KEY,
                    workflow_id TEXT NOT NULL,
                    task_id TEXT NOT NULL,
                    number INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    deadline TEXT NOT NULL,
                    FOREIGN KEY (workflow_id, task_id)
                        REFERENCES workflow_tasks(workflow_id, task_id)
                );
                CREATE TABLE IF NOT EXISTS checkpoints (
                    attempt_id TEXT NOT NULL REFERENCES attempts(attempt_id),
                    checkpoint_key TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    PRIMARY KEY (attempt_id, checkpoint_key)
                );
                CREATE TABLE IF NOT EXISTS outbox (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT UNIQUE NOT NULL,
                    event_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    delivered INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS inbox (
                    event_id TEXT PRIMARY KEY,
                    payload_json TEXT NOT NULL,
                    received_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS workflow_closure (
                    workflow_id TEXT PRIMARY KEY REFERENCES workflows(workflow_id),
                    terminal_status TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    terminal_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS attempt_termination (
                    attempt_id TEXT PRIMARY KEY REFERENCES attempts(attempt_id),
                    terminal_status TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    terminal_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS workflow_closure_events (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    workflow_id TEXT NOT NULL REFERENCES workflows(workflow_id),
                    task_id TEXT,
                    attempt_id TEXT,
                    event_type TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    occurred_at TEXT NOT NULL
                );
                """
            )

    def create_workflow(self, workflow_id: str) -> None:
        _require_identifier(workflow_id, "workflow_id")
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO workflows VALUES (?, 'active', ?)",
                (workflow_id, datetime.now(timezone.utc).isoformat()),
            )

    def add_task(
        self,
        workflow_id: str,
        task_id: str,
        *,
        max_attempts: int,
        compensation_event_type: str | None = None,
    ) -> None:
        _require_identifier(task_id, "task_id")
        if max_attempts < 1:
            raise WorkflowError("max_attempts must be positive")
        with self._connect() as connection:
            workflow = connection.execute(
                "SELECT status FROM workflows WHERE workflow_id = ?", (workflow_id,)
            ).fetchone()
            if workflow is None:
                raise WorkflowError("unknown workflow")
            if workflow["status"] != "active":
                raise WorkflowError("cannot add task to a closed workflow")
            connection.execute(
                "INSERT INTO workflow_tasks VALUES (?, ?, 'ready', ?, ?)",
                (workflow_id, task_id, max_attempts, compensation_event_type),
            )

    def begin_attempt(
        self,
        workflow_id: str,
        task_id: str,
        *,
        deadline: datetime,
    ) -> AttemptRecord:
        if deadline.tzinfo is None:
            raise WorkflowError("deadline must be timezone-aware")
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            workflow = connection.execute(
                "SELECT status FROM workflows WHERE workflow_id = ?", (workflow_id,)
            ).fetchone()
            if workflow is None or workflow["status"] != "active":
                raise WorkflowError("workflow is not active")
            task = connection.execute(
                "SELECT status, max_attempts FROM workflow_tasks "
                "WHERE workflow_id = ? AND task_id = ?",
                (workflow_id, task_id),
            ).fetchone()
            if task is None or task["status"] != "ready":
                raise WorkflowError("task is not ready")
            number = connection.execute(
                "SELECT COUNT(*) + 1 FROM attempts "
                "WHERE workflow_id = ? AND task_id = ?",
                (workflow_id, task_id),
            ).fetchone()[0]
            if number > task["max_attempts"]:
                raise WorkflowError("retry budget exhausted")
            record = AttemptRecord(
                attempt_id=f"{workflow_id}:{task_id}:{number}",
                workflow_id=workflow_id,
                task_id=task_id,
                number=number,
                status="running",
                deadline=deadline,
            )
            connection.execute(
                "INSERT INTO attempts VALUES (?, ?, ?, ?, ?, ?)",
                (
                    record.attempt_id,
                    workflow_id,
                    task_id,
                    number,
                    record.status,
                    deadline.isoformat(),
                ),
            )
            connection.execute(
                "UPDATE workflow_tasks SET status = 'running' "
                "WHERE workflow_id = ? AND task_id = ?",
                (workflow_id, task_id),
            )
        return record

    def save_checkpoint(
        self, attempt_id: str, checkpoint_key: str, payload: dict[str, Any]
    ) -> None:
        _require_identifier(checkpoint_key, "checkpoint_key")
        with self._connect() as connection:
            running = connection.execute(
                "SELECT 1 FROM attempts WHERE attempt_id = ? AND status = 'running'",
                (attempt_id,),
            ).fetchone()
            if running is None:
                raise WorkflowError("checkpoint requires a running attempt")
            connection.execute(
                "INSERT OR REPLACE INTO checkpoints VALUES (?, ?, ?)",
                (attempt_id, checkpoint_key, json.dumps(payload, sort_keys=True)),
            )

    def load_checkpoint(self, attempt_id: str, checkpoint_key: str) -> dict[str, Any]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload_json FROM checkpoints "
                "WHERE attempt_id = ? AND checkpoint_key = ?",
                (attempt_id, checkpoint_key),
            ).fetchone()
        if row is None:
            raise WorkflowError("unknown checkpoint")
        return dict(json.loads(row["payload_json"]))

    def complete_attempt(self, attempt_id: str) -> None:
        terminal_at = datetime.now(timezone.utc)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            attempt = self._attempt(connection, attempt_id)
            if attempt["status"] == "completed":
                return
            if attempt["status"] != "running":
                raise WorkflowError("attempt is not running")
            connection.execute(
                "UPDATE attempts SET status = 'completed' WHERE attempt_id = ?",
                (attempt_id,),
            )
            connection.execute(
                "UPDATE workflow_tasks SET status = 'completed' "
                "WHERE workflow_id = ? AND task_id = ?",
                (attempt["workflow_id"], attempt["task_id"]),
            )
            self._record_attempt_termination(
                connection,
                attempt,
                "completed",
                "attempt completed",
                terminal_at,
            )
            self._reconcile_workflow(
                connection,
                str(attempt["workflow_id"]),
                terminal_hint="completed",
                reason="all required workflow tasks completed",
                now=terminal_at,
            )

    def fail_attempt(self, attempt_id: str, *, reason: str) -> str:
        return self._terminate_attempt(attempt_id, "failed", reason)

    def timeout_attempt(self, attempt_id: str, *, now: datetime) -> str:
        if now.tzinfo is None:
            raise WorkflowError("now must be timezone-aware")
        with self._connect() as connection:
            attempt = self._attempt(connection, attempt_id)
            if attempt["status"] == "timed_out":
                task = connection.execute(
                    "SELECT status FROM workflow_tasks WHERE workflow_id = ? AND task_id = ?",
                    (attempt["workflow_id"], attempt["task_id"]),
                ).fetchone()
                if task is None:
                    raise WorkflowError("unknown task")
                return str(task["status"])
            if attempt["status"] != "running":
                raise WorkflowError("attempt is not running")
            if now < datetime.fromisoformat(attempt["deadline"]):
                raise WorkflowError("attempt deadline has not elapsed")
        return self._terminate_attempt(
            attempt_id,
            "timed_out",
            "deadline elapsed",
            terminal_at=now,
        )

    def cancel_workflow(self, workflow_id: str, *, reason: str, now: datetime) -> str:
        _require_identifier(workflow_id, "workflow_id")
        _require_reason(reason)
        if now.tzinfo is None:
            raise WorkflowError("now must be timezone-aware")
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = self._closure(connection, workflow_id)
            if existing is not None:
                return str(existing["terminal_status"])
            workflow = connection.execute(
                "SELECT status FROM workflows WHERE workflow_id = ?", (workflow_id,)
            ).fetchone()
            if workflow is None:
                raise WorkflowError("unknown workflow")
            running = connection.execute(
                "SELECT * FROM attempts WHERE workflow_id = ? AND status = 'running'",
                (workflow_id,),
            ).fetchall()
            for attempt in running:
                connection.execute(
                    "UPDATE attempts SET status = 'cancelled' WHERE attempt_id = ?",
                    (attempt["attempt_id"],),
                )
                self._record_attempt_termination(
                    connection, attempt, "cancelled", reason, now
                )
            completed = connection.execute(
                "SELECT COUNT(*) FROM workflow_tasks "
                "WHERE workflow_id = ? AND status = 'completed'",
                (workflow_id,),
            ).fetchone()[0]
            connection.execute(
                "UPDATE workflow_tasks SET status = 'cancelled' "
                "WHERE workflow_id = ? AND status IN ('ready', 'running')",
                (workflow_id,),
            )
            terminal = "partial" if int(completed) > 0 else "cancelled"
            self._close_workflow(connection, workflow_id, terminal, reason, now)
            return terminal

    def recover_expired_attempts(self, *, now: datetime) -> tuple[str, ...]:
        """Deterministically close attempts that were orphaned beyond their deadline."""
        if now.tzinfo is None:
            raise WorkflowError("now must be timezone-aware")
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT attempt_id, deadline FROM attempts WHERE status = 'running' "
                "ORDER BY attempt_id"
            ).fetchall()
        expired = tuple(
            str(row["attempt_id"])
            for row in rows
            if datetime.fromisoformat(row["deadline"]) <= now
        )
        for attempt_id in expired:
            self.timeout_attempt(attempt_id, now=now)
        return expired

    def workflow_state(self, workflow_id: str) -> dict[str, Any]:
        """Return the durable workflow terminal truth, including reasons and attempts."""
        _require_identifier(workflow_id, "workflow_id")
        with self._connect() as connection:
            workflow = connection.execute(
                "SELECT * FROM workflows WHERE workflow_id = ?", (workflow_id,)
            ).fetchone()
            if workflow is None:
                raise WorkflowError("unknown workflow")
            closure = self._closure(connection, workflow_id)
            tasks = [
                dict(row)
                for row in connection.execute(
                    "SELECT task_id, status, max_attempts FROM workflow_tasks "
                    "WHERE workflow_id = ? ORDER BY task_id",
                    (workflow_id,),
                )
            ]
            attempts = [
                dict(row)
                for row in connection.execute(
                    "SELECT a.attempt_id, a.task_id, a.number, a.status, a.deadline, "
                    "t.reason, t.terminal_at FROM attempts a "
                    "LEFT JOIN attempt_termination t ON t.attempt_id = a.attempt_id "
                    "WHERE a.workflow_id = ? ORDER BY a.task_id, a.number",
                    (workflow_id,),
                )
            ]
        return {
            "workflow_id": workflow_id,
            "status": str(workflow["status"]),
            "terminal": str(workflow["status"]) in _TERMINAL_WORKFLOW_STATES,
            "reason": None if closure is None else str(closure["reason"]),
            "terminal_at": None if closure is None else str(closure["terminal_at"]),
            "tasks": tasks,
            "attempts": attempts,
        }

    def closure_events(self, workflow_id: str) -> tuple[dict[str, Any], ...]:
        _require_identifier(workflow_id, "workflow_id")
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT sequence, workflow_id, task_id, attempt_id, event_type, reason, occurred_at "
                "FROM workflow_closure_events WHERE workflow_id = ? ORDER BY sequence",
                (workflow_id,),
            ).fetchall()
        return tuple(dict(row) for row in rows)

    def closure_metrics(self) -> dict[str, int]:
        """Expose low-cardinality durable closure counters for operational telemetry."""
        with self._connect() as connection:
            counts = {
                str(row["status"]): int(row["count"])
                for row in connection.execute(
                    "SELECT status, COUNT(*) AS count FROM workflows GROUP BY status"
                )
            }
            retries = int(
                connection.execute(
                    "SELECT COUNT(*) FROM attempts WHERE number > 1"
                ).fetchone()[0]
            )
            running = int(
                connection.execute(
                    "SELECT COUNT(*) FROM attempts WHERE status = 'running'"
                ).fetchone()[0]
            )
        result = {state: counts.get(state, 0) for state in sorted(_TERMINAL_WORKFLOW_STATES)}
        result["active"] = counts.get("active", 0)
        result["retry_count"] = retries
        result["running_attempt_count"] = running
        return result

    def _terminate_attempt(
        self,
        attempt_id: str,
        status: str,
        reason: str,
        *,
        terminal_at: datetime | None = None,
    ) -> str:
        if status not in {"failed", "timed_out"}:
            raise WorkflowError("invalid attempt terminal status")
        _require_reason(reason)
        at = terminal_at or datetime.now(timezone.utc)
        if at.tzinfo is None:
            raise WorkflowError("terminal time must be timezone-aware")
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            attempt = self._attempt(connection, attempt_id)
            if attempt["status"] == status:
                task = connection.execute(
                    "SELECT status FROM workflow_tasks WHERE workflow_id = ? AND task_id = ?",
                    (attempt["workflow_id"], attempt["task_id"]),
                ).fetchone()
                if task is None:
                    raise WorkflowError("unknown task")
                return str(task["status"])
            if attempt["status"] != "running":
                raise WorkflowError("attempt is not running")
            task = connection.execute(
                "SELECT max_attempts, compensation_event_type FROM workflow_tasks "
                "WHERE workflow_id = ? AND task_id = ?",
                (attempt["workflow_id"], attempt["task_id"]),
            ).fetchone()
            if task is None:
                raise WorkflowError("unknown task")
            connection.execute(
                "UPDATE attempts SET status = ? WHERE attempt_id = ?",
                (status, attempt_id),
            )
            self._record_attempt_termination(connection, attempt, status, reason, at)
            retry = attempt["number"] < task["max_attempts"]
            task_status = "ready" if retry else "failed"
            connection.execute(
                "UPDATE workflow_tasks SET status = ? "
                "WHERE workflow_id = ? AND task_id = ?",
                (task_status, attempt["workflow_id"], attempt["task_id"]),
            )
            if not retry and task["compensation_event_type"]:
                self._enqueue(
                    connection,
                    f"compensate:{attempt['workflow_id']}:{attempt['task_id']}",
                    task["compensation_event_type"],
                    {
                        "workflow_id": attempt["workflow_id"],
                        "task_id": attempt["task_id"],
                        "reason": reason,
                    },
                )
            if not retry:
                self._reconcile_workflow(
                    connection,
                    str(attempt["workflow_id"]),
                    terminal_hint=status,
                    reason=reason,
                    now=at,
                )
        return task_status

    @staticmethod
    def _attempt(connection: sqlite3.Connection, attempt_id: str) -> sqlite3.Row:
        attempt = connection.execute(
            "SELECT * FROM attempts WHERE attempt_id = ?", (attempt_id,)
        ).fetchone()
        if attempt is None:
            raise WorkflowError("unknown attempt")
        return cast(sqlite3.Row, attempt)

    @staticmethod
    def _closure(connection: sqlite3.Connection, workflow_id: str) -> sqlite3.Row | None:
        row = connection.execute(
            "SELECT * FROM workflow_closure WHERE workflow_id = ?", (workflow_id,)
        ).fetchone()
        return None if row is None else cast(sqlite3.Row, row)

    def _record_attempt_termination(
        self,
        connection: sqlite3.Connection,
        attempt: sqlite3.Row,
        status: str,
        reason: str,
        now: datetime,
    ) -> None:
        connection.execute(
            "INSERT OR IGNORE INTO attempt_termination VALUES (?, ?, ?, ?)",
            (attempt["attempt_id"], status, reason, now.isoformat()),
        )
        connection.execute(
            "INSERT INTO workflow_closure_events "
            "(workflow_id, task_id, attempt_id, event_type, reason, occurred_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                attempt["workflow_id"],
                attempt["task_id"],
                attempt["attempt_id"],
                f"attempt.{status}",
                reason,
                now.isoformat(),
            ),
        )

    def _reconcile_workflow(
        self,
        connection: sqlite3.Connection,
        workflow_id: str,
        *,
        terminal_hint: str,
        reason: str,
        now: datetime,
    ) -> None:
        if self._closure(connection, workflow_id) is not None:
            return
        rows = connection.execute(
            "SELECT status FROM workflow_tasks WHERE workflow_id = ? ORDER BY task_id",
            (workflow_id,),
        ).fetchall()
        if not rows:
            return
        states = tuple(str(row["status"]) for row in rows)
        if all(state == "completed" for state in states):
            self._close_workflow(
                connection,
                workflow_id,
                "completed",
                "all required workflow tasks completed",
                now,
            )
            return
        if "failed" not in states:
            return
        terminal = "partial" if "completed" in states else (
            "timed_out" if terminal_hint == "timed_out" else "failed"
        )
        self._close_workflow(connection, workflow_id, terminal, reason, now)

    @staticmethod
    def _close_workflow(
        connection: sqlite3.Connection,
        workflow_id: str,
        terminal_status: str,
        reason: str,
        now: datetime,
    ) -> None:
        if terminal_status not in _TERMINAL_WORKFLOW_STATES:
            raise WorkflowError("invalid workflow terminal status")
        changed = connection.execute(
            "UPDATE workflows SET status = ? WHERE workflow_id = ? AND status = 'active'",
            (terminal_status, workflow_id),
        ).rowcount
        if changed != 1:
            existing = connection.execute(
                "SELECT status FROM workflows WHERE workflow_id = ?", (workflow_id,)
            ).fetchone()
            if existing is None:
                raise WorkflowError("unknown workflow")
            if str(existing["status"]) != terminal_status:
                raise WorkflowError("workflow terminal state changed concurrently")
        connection.execute(
            "INSERT OR IGNORE INTO workflow_closure VALUES (?, ?, ?, ?)",
            (workflow_id, terminal_status, reason, now.isoformat()),
        )
        connection.execute(
            "INSERT INTO workflow_closure_events "
            "(workflow_id, task_id, attempt_id, event_type, reason, occurred_at) "
            "VALUES (?, NULL, NULL, ?, ?, ?)",
            (
                workflow_id,
                f"workflow.{terminal_status}",
                reason,
                now.isoformat(),
            ),
        )

    def receive_event(self, event_id: str, payload: dict[str, Any]) -> bool:
        """Persist an inbound event exactly once; duplicates are acknowledged safely."""
        _require_identifier(event_id, "event_id")
        with self._connect() as connection:
            cursor = connection.execute(
                "INSERT OR IGNORE INTO inbox VALUES (?, ?, ?)",
                (
                    event_id,
                    json.dumps(payload, sort_keys=True),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
        return cursor.rowcount == 1

    def pending_outbox(self) -> tuple[OutboxRecord, ...]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM outbox WHERE delivered = 0 ORDER BY sequence"
            ).fetchall()
        return tuple(
            OutboxRecord(
                row["sequence"],
                row["event_id"],
                row["event_type"],
                dict(json.loads(row["payload_json"])),
            )
            for row in rows
        )

    def acknowledge_outbox(self, event_id: str) -> None:
        with self._connect() as connection:
            cursor = connection.execute(
                "UPDATE outbox SET delivered = 1 WHERE event_id = ?",
                (event_id,),
            )
        if cursor.rowcount != 1:
            raise WorkflowError("unknown outbox event")

    def task_state(self, workflow_id: str) -> tuple[dict[str, str], ...]:
        """Return durable task outcomes for acceptance verification."""
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT task_id, status FROM workflow_tasks "
                "WHERE workflow_id = ? ORDER BY task_id",
                (workflow_id,),
            ).fetchall()
        if not rows:
            raise WorkflowError("unknown workflow")
        return tuple(
            {"task_id": str(row["task_id"]), "status": str(row["status"])}
            for row in rows
        )

    @staticmethod
    def _enqueue(
        connection: sqlite3.Connection,
        event_id: str,
        event_type: str,
        payload: dict[str, Any],
    ) -> None:
        connection.execute(
            "INSERT OR IGNORE INTO outbox "
            "(event_id, event_type, payload_json) VALUES (?, ?, ?)",
            (event_id, event_type, json.dumps(payload, sort_keys=True)),
        )


def _require_identifier(value: str, field: str) -> None:
    if not value or value != value.strip():
        raise WorkflowError(f"{field} must be non-blank and trimmed")


def _require_reason(reason: str) -> None:
    if not reason or reason != reason.strip():
        raise WorkflowError("reason must be non-blank and trimmed")
