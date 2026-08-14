"""Durable provider-health evidence for canonical routing eligibility.

This store never selects or reroutes a provider. It only returns whether a candidate
is currently eligible; the canonical ILAIOS RoutingDecision remains authoritative.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path


class ProviderHealthError(RuntimeError):
    """Raised when provider health state is invalid or unavailable."""


class CircuitState(str, Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


@dataclass(frozen=True, slots=True)
class ProviderHealthSnapshot:
    provider_id: str
    state: CircuitState
    consecutive_failures: int
    opened_at: str | None
    last_success_at: str | None
    last_failure_at: str | None
    last_failure_reason: str | None


_SCHEMA = """
CREATE TABLE IF NOT EXISTS provider_health (
 provider_id TEXT PRIMARY KEY,
 state TEXT NOT NULL,
 consecutive_failures INTEGER NOT NULL CHECK (consecutive_failures >= 0),
 opened_at TEXT,
 last_success_at TEXT,
 last_failure_at TEXT,
 last_failure_reason TEXT
);
"""


class ProviderHealthStore:
    """Persistent circuit breaker whose output is only an eligibility signal."""

    def __init__(
        self,
        root: Path,
        *,
        failure_threshold: int = 3,
        cooldown: timedelta = timedelta(minutes=5),
    ) -> None:
        if failure_threshold <= 0:
            raise ProviderHealthError("failure_threshold must be positive")
        if cooldown <= timedelta(0):
            raise ProviderHealthError("cooldown must be positive")
        root.mkdir(parents=True, exist_ok=True)
        self._database = root / "media_provider_health.sqlite3"
        self._threshold = failure_threshold
        self._cooldown = cooldown
        with self._connect() as connection:
            connection.executescript(_SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database)
        connection.row_factory = sqlite3.Row
        return connection

    def snapshot(self, provider_id: str, *, now: datetime) -> ProviderHealthSnapshot:
        provider_id = _text("provider_id", provider_id)
        now = _utc(now)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM provider_health WHERE provider_id=?", (provider_id,)
            ).fetchone()
            if row is None:
                connection.execute(
                    "INSERT INTO provider_health VALUES (?, ?, 0, NULL, NULL, NULL, NULL)",
                    (provider_id, CircuitState.CLOSED.value),
                )
                return ProviderHealthSnapshot(
                    provider_id, CircuitState.CLOSED, 0, None, None, None, None
                )
            current = _snapshot(row)
            if current.state is CircuitState.OPEN and current.opened_at is not None:
                opened = datetime.fromisoformat(current.opened_at)
                if now >= opened + self._cooldown:
                    connection.execute(
                        "UPDATE provider_health SET state=? WHERE provider_id=?",
                        (CircuitState.HALF_OPEN.value, provider_id),
                    )
                    return ProviderHealthSnapshot(
                        provider_id=current.provider_id,
                        state=CircuitState.HALF_OPEN,
                        consecutive_failures=current.consecutive_failures,
                        opened_at=current.opened_at,
                        last_success_at=current.last_success_at,
                        last_failure_at=current.last_failure_at,
                        last_failure_reason=current.last_failure_reason,
                    )
            return current

    def assert_candidate_eligible(self, provider_id: str, *, now: datetime) -> None:
        snapshot = self.snapshot(provider_id, now=now)
        if snapshot.state is CircuitState.OPEN:
            raise ProviderHealthError(
                "provider candidate is circuit-open; canonical routing must choose or wait"
            )

    def record_failure(
        self, provider_id: str, *, reason: str, now: datetime
    ) -> ProviderHealthSnapshot:
        provider_id = _text("provider_id", provider_id)
        reason = _text("reason", reason)
        now = _utc(now)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM provider_health WHERE provider_id=?", (provider_id,)
            ).fetchone()
            previous = _snapshot(row) if row is not None else ProviderHealthSnapshot(
                provider_id, CircuitState.CLOSED, 0, None, None, None, None
            )
            failures = previous.consecutive_failures + 1
            state = previous.state
            if failures >= self._threshold or previous.state is CircuitState.HALF_OPEN:
                state = CircuitState.OPEN
            opened_at = now.isoformat() if state is CircuitState.OPEN else previous.opened_at
            connection.execute(
                "INSERT INTO provider_health "
                "(provider_id,state,consecutive_failures,opened_at,last_success_at,"
                "last_failure_at,last_failure_reason) VALUES (?,?,?,?,?,?,?) "
                "ON CONFLICT(provider_id) DO UPDATE SET state=excluded.state,"
                "consecutive_failures=excluded.consecutive_failures,opened_at=excluded.opened_at,"
                "last_success_at=excluded.last_success_at,last_failure_at=excluded.last_failure_at,"
                "last_failure_reason=excluded.last_failure_reason",
                (
                    provider_id,
                    state.value,
                    failures,
                    opened_at,
                    previous.last_success_at,
                    now.isoformat(),
                    reason,
                ),
            )
        return self.snapshot(provider_id, now=now)

    def record_success(self, provider_id: str, *, now: datetime) -> ProviderHealthSnapshot:
        provider_id = _text("provider_id", provider_id)
        now = _utc(now)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "INSERT INTO provider_health "
                "(provider_id,state,consecutive_failures,opened_at,last_success_at,"
                "last_failure_at,last_failure_reason) VALUES (?, ?, 0, NULL, ?, NULL, NULL) "
                "ON CONFLICT(provider_id) DO UPDATE SET state=excluded.state,"
                "consecutive_failures=0,opened_at=NULL,last_success_at=excluded.last_success_at,"
                "last_failure_reason=NULL",
                (provider_id, CircuitState.CLOSED.value, now.isoformat()),
            )
        return self.snapshot(provider_id, now=now)


def _snapshot(row: sqlite3.Row | None) -> ProviderHealthSnapshot:
    if row is None:
        raise ProviderHealthError("provider health row is missing")
    return ProviderHealthSnapshot(
        provider_id=str(row["provider_id"]),
        state=CircuitState(str(row["state"])),
        consecutive_failures=int(row["consecutive_failures"]),
        opened_at=_optional(row["opened_at"]),
        last_success_at=_optional(row["last_success_at"]),
        last_failure_at=_optional(row["last_failure_at"]),
        last_failure_reason=_optional(row["last_failure_reason"]),
    )


def _optional(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _text(name: str, value: str) -> str:
    if not value or value != value.strip():
        raise ProviderHealthError(f"{name} must be non-blank and trimmed")
    return value


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ProviderHealthError("provider health timestamps must be timezone-aware")
    return value.astimezone(timezone.utc)
