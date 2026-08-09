"""Sequenced, replayable, DLP-safe authoritative live-state transport."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class LiveStateError(ValueError):
    """Raised when an event would violate live-state ordering."""


@dataclass(frozen=True, slots=True)
class LiveEvent:
    sequence: int
    aggregate_id: str
    version: int
    event_type: str
    state: dict[str, Any]


class LiveStateTransport:
    """Durable source for reconnectable state events and snapshots."""

    _SENSITIVE_KEYS = frozenset(
        {"access_token", "api_key", "authorization", "password", "secret", "token"}
    )

    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path
        database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS live_events (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    aggregate_id TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    event_type TEXT NOT NULL,
                    state_json TEXT NOT NULL,
                    occurred_at TEXT NOT NULL,
                    UNIQUE (aggregate_id, version)
                );
                CREATE TABLE IF NOT EXISTS live_state (
                    aggregate_id TEXT PRIMARY KEY,
                    version INTEGER NOT NULL,
                    state_json TEXT NOT NULL,
                    last_sequence INTEGER NOT NULL
                );
                """
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def publish(
        self,
        aggregate_id: str,
        event_type: str,
        state: dict[str, Any],
    ) -> LiveEvent:
        _require_text(aggregate_id, "aggregate_id")
        _require_text(event_type, "event_type")
        safe_state = _redact(state, self._SENSITIVE_KEYS)
        with self._connect() as connection:
            current = connection.execute(
                "SELECT version FROM live_state WHERE aggregate_id = ?",
                (aggregate_id,),
            ).fetchone()
            version = 1 if current is None else current["version"] + 1
            cursor = connection.execute(
                "INSERT INTO live_events "
                "(aggregate_id, version, event_type, state_json, occurred_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    aggregate_id,
                    version,
                    event_type,
                    json.dumps(safe_state, sort_keys=True),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            if cursor.lastrowid is None:
                raise LiveStateError("event sequence was not allocated")
            sequence = cursor.lastrowid
            connection.execute(
                "INSERT INTO live_state VALUES (?, ?, ?, ?) "
                "ON CONFLICT(aggregate_id) DO UPDATE SET "
                "version = excluded.version, state_json = excluded.state_json, "
                "last_sequence = excluded.last_sequence",
                (
                    aggregate_id,
                    version,
                    json.dumps(safe_state, sort_keys=True),
                    sequence,
                ),
            )
        return LiveEvent(sequence, aggregate_id, version, event_type, safe_state)

    def replay(self, *, after_sequence: int = 0) -> tuple[LiveEvent, ...]:
        if after_sequence < 0:
            raise LiveStateError("after_sequence cannot be negative")
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM live_events WHERE sequence > ? ORDER BY sequence",
                (after_sequence,),
            ).fetchall()
        return tuple(_event_from_row(row) for row in rows)

    def snapshot(self, aggregate_id: str) -> LiveEvent:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT aggregate_id, version, state_json, last_sequence "
                "FROM live_state WHERE aggregate_id = ?",
                (aggregate_id,),
            ).fetchone()
        if row is None:
            raise LiveStateError("unknown aggregate_id")
        return LiveEvent(
            row["last_sequence"],
            row["aggregate_id"],
            row["version"],
            "state.snapshot",
            dict(json.loads(row["state_json"])),
        )


class LiveStateProjection:
    """Reconnectable non-authoritative projection that fails closed on gaps."""

    def __init__(self) -> None:
        self._last_sequence = 0
        self._states: dict[str, LiveEvent] = {}

    @property
    def last_sequence(self) -> int:
        return self._last_sequence

    def reconcile(self, events: tuple[LiveEvent, ...]) -> None:
        for event in sorted(events, key=lambda item: item.sequence):
            if event.sequence <= self._last_sequence:
                continue
            if event.sequence != self._last_sequence + 1:
                raise LiveStateError("event sequence contains a gap")
            current = self._states.get(event.aggregate_id)
            if current is not None and event.version != current.version + 1:
                raise LiveStateError("aggregate version is out of order")
            self._states[event.aggregate_id] = event
            self._last_sequence = event.sequence

    def restore_snapshot(self, snapshot: LiveEvent) -> None:
        """Restore an authoritative snapshot after a detected replay gap."""
        if snapshot.event_type != "state.snapshot":
            raise LiveStateError("snapshot event type is required")
        if snapshot.sequence < 1 or snapshot.version < 1:
            raise LiveStateError("snapshot sequence and version must be positive")
        self._states[snapshot.aggregate_id] = snapshot
        self._last_sequence = snapshot.sequence

    def state(self, aggregate_id: str) -> dict[str, Any]:
        try:
            return dict(self._states[aggregate_id].state)
        except KeyError as error:
            raise LiveStateError("unknown projected aggregate_id") from error


def _event_from_row(row: sqlite3.Row) -> LiveEvent:
    return LiveEvent(
        row["sequence"],
        row["aggregate_id"],
        row["version"],
        row["event_type"],
        dict(json.loads(row["state_json"])),
    )


def _redact(value: Any, sensitive_keys: frozenset[str]) -> Any:
    if isinstance(value, dict):
        return {
            str(key): "[REDACTED]"
            if str(key).lower() in sensitive_keys
            else _redact(item, sensitive_keys)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact(item, sensitive_keys) for item in value]
    return value


def _require_text(value: str, field: str) -> None:
    if not value or value != value.strip():
        raise LiveStateError(f"{field} must be non-blank and trimmed")
