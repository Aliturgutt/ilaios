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


class WorkflowStore:
    """SQLite-backed workflow state that remains authoritative after restart."""

    def __init__(self, config: WorkflowStoreConfig) -> None:
        self._config = config
        config.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._config.database_path)
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
        with self._connect() as connection:
            attempt = self._running_attempt(connection, attempt_id)
            connection.execute(
                "UPDATE attempts SET status = 'completed' WHERE attempt_id = ?",
                (attempt_id,),
            )
            connection.execute(
                "UPDATE workflow_tasks SET status = 'completed' "
                "WHERE workflow_id = ? AND task_id = ?",
                (attempt["workflow_id"], attempt["task_id"]),
            )

    def fail_attempt(self, attempt_id: str, *, reason: str) -> str:
        return self._terminate_attempt(attempt_id, "failed", reason)

    def timeout_attempt(self, attempt_id: str, *, now: datetime) -> str:
        with self._connect() as connection:
            attempt = self._running_attempt(connection, attempt_id)
            if now.tzinfo is None:
                raise WorkflowError("now must be timezone-aware")
            if now < datetime.fromisoformat(attempt["deadline"]):
                raise WorkflowError("attempt deadline has not elapsed")
        return self._terminate_attempt(attempt_id, "timed_out", "deadline elapsed")

    def _terminate_attempt(self, attempt_id: str, status: str, reason: str) -> str:
        if not reason or reason != reason.strip():
            raise WorkflowError("reason must be non-blank and trimmed")
        with self._connect() as connection:
            attempt = self._running_attempt(connection, attempt_id)
            task = connection.execute(
                "SELECT max_attempts, compensation_event_type FROM workflow_tasks "
                "WHERE workflow_id = ? AND task_id = ?",
                (attempt["workflow_id"], attempt["task_id"]),
            ).fetchone()
            connection.execute(
                "UPDATE attempts SET status = ? WHERE attempt_id = ?",
                (status, attempt_id),
            )
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
        return task_status

    @staticmethod
    def _running_attempt(
        connection: sqlite3.Connection, attempt_id: str
    ) -> sqlite3.Row:
        attempt = connection.execute(
            "SELECT * FROM attempts WHERE attempt_id = ? AND status = 'running'",
            (attempt_id,),
        ).fetchone()
        if attempt is None:
            raise WorkflowError("attempt is not running")
        return cast(sqlite3.Row, attempt)

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
