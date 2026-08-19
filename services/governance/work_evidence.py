"""Narrow read-only evidence projection for persisted governed work.

This module does not authorize, approve, execute, reconcile, or mutate work. It
reads only server-authored identity/status columns needed to bind certification
evidence to an exact persisted request without exposing payloads, secrets, or
result bodies.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

from .gates import GateError


class GovernedWorkEvidenceReader:
    """Read exact persisted work identity from an existing governance database."""

    def __init__(self, database_path: Path) -> None:
        self._database = database_path.resolve()

    def snapshot(self, request_id: str) -> dict[str, str]:
        if not request_id or request_id != request_id.strip():
            raise GateError("a valid governed work request id is required")
        if not self._database.is_file():
            raise GateError("governed work evidence database is unavailable")
        connection = sqlite3.connect(
            self._database.as_uri() + "?mode=ro",
            uri=True,
            timeout=10,
        )
        connection.row_factory = sqlite3.Row
        try:
            row = connection.execute(
                "SELECT request_id, requester_id, agent_id, skill_id, capability, status "
                "FROM governed_work WHERE request_id = ?",
                (request_id,),
            ).fetchone()
        finally:
            connection.close()
        if row is None:
            raise GateError("governed work evidence is unavailable")
        values = {
            "request_id": str(row["request_id"]),
            "requester_id": str(row["requester_id"]),
            "agent_id": str(row["agent_id"]),
            "skill_id": str(row["skill_id"]),
            "capability": str(row["capability"]),
            "status": str(row["status"]),
        }
        if any(not value for value in values.values()):
            raise GateError("governed work evidence identity is malformed")
        return values
