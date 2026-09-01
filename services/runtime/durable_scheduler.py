"""Concurrent durable worker scheduler with fencing-enforced side effects."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from services.runtime.scheduler import Lease, SchedulingError, WorkerProfile


class DurableWorkerScheduler:
    """SQLite scheduler whose lease decisions are atomic across threads/processes."""

    def __init__(self, database_path: Path, *, lease_duration: timedelta) -> None:
        if lease_duration <= timedelta(0):
            raise SchedulingError("lease_duration must be positive")
        self._database_path = database_path
        self._lease_duration = lease_duration

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def register(self, profile: WorkerProfile) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO scheduler_workers VALUES (?, ?, ?)",
                (
                    profile.worker_id,
                    json.dumps(sorted(profile.capabilities)),
                    profile.max_concurrent_tasks,
                ),
            )

    def unregister(self, worker_id: str) -> bool:
        """Remove a terminal worker only after all of its leases are released."""
        if not worker_id or worker_id != worker_id.strip():
            raise SchedulingError("worker_id must be non-blank and trimmed")
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            leased = connection.execute(
                "SELECT 1 FROM scheduler_leases WHERE worker_id = ? LIMIT 1",
                (worker_id,),
            ).fetchone()
            if leased is not None:
                raise SchedulingError("cannot unregister worker with lease")
            deleted = connection.execute(
                "DELETE FROM scheduler_workers WHERE worker_id = ?", (worker_id,)
            ).rowcount
        return deleted == 1

    def schedule(self, task_id: str, capability: str, *, now: datetime) -> Lease:
        _require_aware(now, "now")
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                "SELECT expires_at FROM scheduler_leases WHERE task_id = ?",
                (task_id,),
            ).fetchone()
            if existing is not None and datetime.fromisoformat(existing[0]) > now:
                raise SchedulingError("task already has an active lease")
            workers = connection.execute(
                "SELECT * FROM scheduler_workers ORDER BY worker_id"
            ).fetchall()
            eligible: list[tuple[int, sqlite3.Row]] = []
            for worker in workers:
                capabilities = set(json.loads(worker["capabilities_json"]))
                active = connection.execute(
                    "SELECT COUNT(*) FROM scheduler_leases "
                    "WHERE worker_id = ? AND expires_at > ?",
                    (worker["worker_id"], now.isoformat()),
                ).fetchone()[0]
                if capability in capabilities and active < worker["max_concurrent_tasks"]:
                    eligible.append((int(active), worker))
            if not eligible:
                raise SchedulingError("no worker is within capability and quota")
            eligible.sort(key=lambda item: (item[0], item[1]["worker_id"]))
            worker_id = str(eligible[0][1]["worker_id"])
            fence_row = connection.execute(
                "SELECT fencing_token FROM scheduler_fences WHERE task_id = ?",
                (task_id,),
            ).fetchone()
            fence = 1 if fence_row is None else int(fence_row[0]) + 1
            connection.execute(
                "INSERT INTO scheduler_fences VALUES (?, ?) "
                "ON CONFLICT(task_id) DO UPDATE SET fencing_token=excluded.fencing_token",
                (task_id, fence),
            )
            expires_at = now + self._lease_duration
            connection.execute(
                "INSERT INTO scheduler_leases VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT(task_id) DO UPDATE SET worker_id=excluded.worker_id, "
                "capability=excluded.capability, fencing_token=excluded.fencing_token, "
                "expires_at=excluded.expires_at",
                (task_id, worker_id, capability, fence, expires_at.isoformat()),
            )
        return Lease(task_id, worker_id, fence, expires_at)

    def heartbeat(self, lease: Lease, *, now: datetime) -> Lease:
        renewed = Lease(
            lease.task_id,
            lease.worker_id,
            lease.fencing_token,
            now + self._lease_duration,
        )
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            self._authorize(connection, lease, now)
            connection.execute(
                "UPDATE scheduler_leases SET expires_at = ? WHERE task_id = ?",
                (renewed.expires_at.isoformat(), lease.task_id),
            )
        return renewed

    def reschedule_expired(
        self, task_id: str, capability: str, *, now: datetime
    ) -> Lease:
        with self._connect() as connection:
            current = connection.execute(
                "SELECT expires_at FROM scheduler_leases WHERE task_id = ?",
                (task_id,),
            ).fetchone()
        if current is None or datetime.fromisoformat(current[0]) > now:
            raise SchedulingError("task lease is not expired")
        return self.schedule(task_id, capability, now=now)

    def record_side_effect(
        self, lease: Lease, *, now: datetime, payload: dict[str, Any]
    ) -> None:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            self._authorize(connection, lease, now)
            connection.execute(
                "INSERT INTO scheduler_effects VALUES (?, ?, ?, ?)",
                (
                    lease.task_id,
                    lease.fencing_token,
                    json.dumps(payload, sort_keys=True),
                    now.isoformat(),
                ),
            )

    def authorize(self, lease: Lease, *, now: datetime) -> None:
        """Verify the current durable lease without recording an effect."""
        with self._connect() as connection:
            self._authorize(connection, lease, now)

    def release(self, lease: Lease) -> bool:
        """Release exactly the current fenced lease; duplicate release is idempotent."""
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM scheduler_leases WHERE task_id = ?", (lease.task_id,)
            ).fetchone()
            if row is None:
                return False
            if (
                row["worker_id"] != lease.worker_id
                or row["fencing_token"] != lease.fencing_token
                or row["expires_at"] != lease.expires_at.isoformat()
            ):
                raise SchedulingError("cannot release stale or replaced fencing token")
            connection.execute(
                "DELETE FROM scheduler_leases WHERE task_id = ?", (lease.task_id,)
            )
        return True

    def state(self) -> dict[str, Any]:
        with self._connect() as connection:
            workers = [
                dict(row)
                for row in connection.execute(
                    "SELECT * FROM scheduler_workers ORDER BY worker_id"
                )
            ]
            leases = [
                dict(row)
                for row in connection.execute(
                    "SELECT * FROM scheduler_leases ORDER BY task_id"
                )
            ]
            effects = [
                dict(row)
                for row in connection.execute(
                    "SELECT * FROM scheduler_effects ORDER BY task_id, fencing_token"
                )
            ]
        return {"workers": workers, "leases": leases, "effects": effects}

    @staticmethod
    def _authorize(
        connection: sqlite3.Connection, lease: Lease, now: datetime
    ) -> None:
        _require_aware(now, "now")
        row = connection.execute(
            "SELECT * FROM scheduler_leases WHERE task_id = ?", (lease.task_id,)
        ).fetchone()
        if (
            row is None
            or row["worker_id"] != lease.worker_id
            or row["fencing_token"] != lease.fencing_token
            or row["expires_at"] != lease.expires_at.isoformat()
        ):
            raise SchedulingError("stale or replaced fencing token")
        if datetime.fromisoformat(row["expires_at"]) <= now:
            raise SchedulingError("lease expired")


def _require_aware(value: datetime, field: str) -> None:
    if value.tzinfo is None:
        raise SchedulingError(f"{field} must be timezone-aware")
