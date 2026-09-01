"""Durable, privacy-bounded access evidence for provider reference relay GETs."""

from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path

from services.reference_relay import ReferenceRelayError


@dataclass(frozen=True, slots=True)
class ReferenceRelayAccessEvidence:
    sha256: str
    fetch_count: int
    first_fetched_at_epoch_s: int
    last_fetched_at_epoch_s: int


class ReferenceRelayAccessLedger:
    """Record successful signed relay GETs without persisting signed URLs or identities."""

    def __init__(self, database_path: Path) -> None:
        self._database = database_path
        database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS reference_relay_access ("
                "sha256 TEXT PRIMARY KEY, fetch_count INTEGER NOT NULL, "
                "first_fetched_at_epoch_s INTEGER NOT NULL, "
                "last_fetched_at_epoch_s INTEGER NOT NULL)"
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def record_fetch(self, sha256_hex: str, *, now_epoch_s: int | None = None) -> None:
        _require_sha256(sha256_hex)
        now = int(time.time()) if now_epoch_s is None else now_epoch_s
        if now <= 0:
            raise ReferenceRelayError("reference relay access time is invalid")
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO reference_relay_access "
                "(sha256, fetch_count, first_fetched_at_epoch_s, last_fetched_at_epoch_s) "
                "VALUES (?, 1, ?, ?) "
                "ON CONFLICT(sha256) DO UPDATE SET "
                "fetch_count = fetch_count + 1, last_fetched_at_epoch_s = excluded.last_fetched_at_epoch_s",
                (sha256_hex, now, now),
            )

    def evidence(self, sha256_hex: str) -> ReferenceRelayAccessEvidence | None:
        _require_sha256(sha256_hex)
        with self._connect() as connection:
            row = connection.execute(
                "SELECT sha256, fetch_count, first_fetched_at_epoch_s, last_fetched_at_epoch_s "
                "FROM reference_relay_access WHERE sha256 = ?",
                (sha256_hex,),
            ).fetchone()
        if row is None:
            return None
        return ReferenceRelayAccessEvidence(
            sha256=str(row["sha256"]),
            fetch_count=int(row["fetch_count"]),
            first_fetched_at_epoch_s=int(row["first_fetched_at_epoch_s"]),
            last_fetched_at_epoch_s=int(row["last_fetched_at_epoch_s"]),
        )


def _require_sha256(value: str) -> None:
    if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        raise ReferenceRelayError("reference relay access SHA-256 is invalid")
