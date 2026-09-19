"""Durable scoped grants, blast-radius accounting, revocation, and stops."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

from services.runtime.grants import BlastRadiusBudget, ExecutionGrant, GrantError


class DurableGrantPolicy:
    """Persist grant state and atomically reserve blast-radius usage."""

    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def register(self, grant: ExecutionGrant) -> None:
        if grant.expires_at.tzinfo is None:
            raise GrantError("grant times must be timezone-aware")
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO execution_grants VALUES (?, ?, ?, ?, ?, ?, ?, 0)",
                (
                    grant.grant_id,
                    grant.subject_id,
                    json.dumps(sorted(grant.actions)),
                    json.dumps(sorted(grant.resources)),
                    grant.expires_at.isoformat(),
                    grant.budget.max_side_effects,
                    grant.budget.max_resources,
                ),
            )

    def get(self, grant_id: str) -> ExecutionGrant:
        if not grant_id or grant_id != grant_id.strip():
            raise GrantError("grant_id must be non-blank and trimmed")
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM execution_grants WHERE grant_id = ?", (grant_id,)
            ).fetchone()
        if row is None:
            raise GrantError("grant is not registered")
        return ExecutionGrant(
            str(row["grant_id"]),
            str(row["subject_id"]),
            frozenset(json.loads(row["actions_json"])),
            frozenset(json.loads(row["resources_json"])),
            datetime.fromisoformat(str(row["expires_at"])),
            BlastRadiusBudget(
                int(row["max_side_effects"]),
                int(row["max_resources"]),
            ),
        )

    def authorize(
        self,
        grant: ExecutionGrant,
        *,
        subject_id: str,
        action: str,
        resource: str,
        now: datetime,
    ) -> None:
        if not isinstance(grant, ExecutionGrant):
            raise GrantError("canonical ExecutionGrant is required")
        self.authorize_and_record(
            grant.grant_id,
            subject_id=subject_id,
            action=action,
            resource=resource,
            now=now,
        )

    def authorize_and_record(
        self,
        grant_id: str,
        *,
        subject_id: str,
        action: str,
        resource: str,
        now: datetime,
    ) -> None:
        if now.tzinfo is None:
            raise GrantError("grant times must be timezone-aware")
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            grant = connection.execute(
                "SELECT * FROM execution_grants WHERE grant_id = ?", (grant_id,)
            ).fetchone()
            if grant is None:
                raise GrantError("grant is not registered")
            revoked = connection.execute(
                "SELECT 1 FROM revoked_grants WHERE grant_id = ?", (grant_id,)
            ).fetchone()
            if revoked is not None:
                raise GrantError("grant is revoked")
            stopped = connection.execute(
                "SELECT 1 FROM stopped_subjects WHERE subject_id = ?", (subject_id,)
            ).fetchone()
            if stopped is not None:
                raise GrantError("subject is stopped")
            if grant["subject_id"] != subject_id:
                raise GrantError("grant subject mismatch")
            if now >= datetime.fromisoformat(grant["expires_at"]):
                raise GrantError("grant is expired")
            if action not in json.loads(grant["actions_json"]) or resource not in json.loads(
                grant["resources_json"]
            ):
                raise GrantError("action or resource is outside grant scope")
            if grant["used_side_effects"] >= grant["max_side_effects"]:
                raise GrantError("side-effect budget exhausted")
            used = connection.execute(
                "SELECT COUNT(*) FROM grant_resources WHERE grant_id = ?", (grant_id,)
            ).fetchone()[0]
            known = connection.execute(
                "SELECT 1 FROM grant_resources WHERE grant_id = ? AND resource = ?",
                (grant_id, resource),
            ).fetchone()
            if known is None and used >= grant["max_resources"]:
                raise GrantError("resource budget exhausted")
            connection.execute(
                "UPDATE execution_grants SET used_side_effects = used_side_effects + 1 "
                "WHERE grant_id = ?",
                (grant_id,),
            )
            connection.execute(
                "INSERT OR IGNORE INTO grant_resources VALUES (?, ?)",
                (grant_id, resource),
            )

    def revoke(self, grant_id: str, *, now: datetime) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT OR IGNORE INTO revoked_grants VALUES (?, ?)",
                (grant_id, now.isoformat()),
            )

    def kill(self, subject_id: str, *, now: datetime) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT OR IGNORE INTO stopped_subjects VALUES (?, ?)",
                (subject_id, now.isoformat()),
            )

    def state(self) -> dict[str, object]:
        with self._connect() as connection:
            return {
                "grants": [
                    dict(row)
                    for row in connection.execute(
                        "SELECT * FROM execution_grants ORDER BY grant_id"
                    )
                ],
                "revoked": [
                    dict(row)
                    for row in connection.execute(
                        "SELECT * FROM revoked_grants ORDER BY grant_id"
                    )
                ],
                "stopped": [
                    dict(row)
                    for row in connection.execute(
                        "SELECT * FROM stopped_subjects ORDER BY subject_id"
                    )
                ],
            }
