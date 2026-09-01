"""Content-addressed artifact store with append-only hash-chain provenance."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


class EvidenceError(ValueError):
    """Raised when stored evidence cannot independently prove integrity."""


@dataclass(frozen=True, slots=True)
class ArtifactRecord:
    digest: str
    size: int
    path: Path


@dataclass(frozen=True, slots=True)
class ProvenanceRecord:
    sequence: int
    execution_id: str
    artifact_digest: str
    action: str
    previous_hash: str
    record_hash: str


class EvidenceStore:
    """Durable evidence boundary with no mutation API for accepted records."""

    def __init__(self, root: Path) -> None:
        self._root = root
        self._artifacts = root / "artifacts"
        self._artifacts.mkdir(parents=True, exist_ok=True)
        self._database = root / "provenance.sqlite3"
        with self._connect() as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS provenance ("
                "sequence INTEGER PRIMARY KEY AUTOINCREMENT, "
                "execution_id TEXT NOT NULL, artifact_digest TEXT NOT NULL, "
                "action TEXT NOT NULL, occurred_at TEXT NOT NULL, "
                "previous_hash TEXT NOT NULL, record_hash TEXT UNIQUE NOT NULL)"
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database)
        connection.row_factory = sqlite3.Row
        return connection

    def put_artifact(self, content: bytes) -> ArtifactRecord:
        digest = hashlib.sha256(content).hexdigest()
        path = self._artifacts / digest
        if path.exists() and path.read_bytes() != content:
            raise EvidenceError("artifact digest collision")
        if not path.exists():
            path.write_bytes(content)
        return ArtifactRecord(digest, len(content), path)

    def get_artifact(self, digest: str) -> bytes:
        """Return verified bytes for a stable content identity."""
        if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
            raise EvidenceError("artifact digest must be a lowercase SHA-256 identity")
        path = self._artifacts / digest
        if not path.is_file():
            raise EvidenceError("artifact is missing")
        content = path.read_bytes()
        if hashlib.sha256(content).hexdigest() != digest:
            raise EvidenceError("artifact integrity check failed")
        return content

    def append_provenance(
        self, execution_id: str, artifact: ArtifactRecord, action: str
    ) -> ProvenanceRecord:
        occurred_at = datetime.now(timezone.utc).isoformat()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            last = connection.execute(
                "SELECT record_hash FROM provenance ORDER BY sequence DESC LIMIT 1"
            ).fetchone()
            previous_hash = "0" * 64 if last is None else str(last["record_hash"])
            payload = {
                "execution_id": execution_id,
                "artifact_digest": artifact.digest,
                "action": action,
                "occurred_at": occurred_at,
                "previous_hash": previous_hash,
            }
            record_hash = hashlib.sha256(
                json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest()
            cursor = connection.execute(
                "INSERT INTO provenance "
                "(execution_id, artifact_digest, action, occurred_at, previous_hash, record_hash) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    execution_id,
                    artifact.digest,
                    action,
                    occurred_at,
                    previous_hash,
                    record_hash,
                ),
            )
            if cursor.lastrowid is None:
                raise EvidenceError("provenance sequence was not allocated")
            return ProvenanceRecord(
                cursor.lastrowid,
                execution_id,
                artifact.digest,
                action,
                previous_hash,
                record_hash,
            )

    def verify(self) -> tuple[ProvenanceRecord, ...]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM provenance ORDER BY sequence"
            ).fetchall()
        previous_hash = "0" * 64
        records: list[ProvenanceRecord] = []
        for row in rows:
            artifact_path = self._artifacts / row["artifact_digest"]
            if not artifact_path.is_file():
                raise EvidenceError("referenced artifact is missing")
            actual_digest = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
            if actual_digest != row["artifact_digest"]:
                raise EvidenceError("artifact integrity check failed")
            payload = {
                "execution_id": row["execution_id"],
                "artifact_digest": row["artifact_digest"],
                "action": row["action"],
                "occurred_at": row["occurred_at"],
                "previous_hash": row["previous_hash"],
            }
            expected = hashlib.sha256(
                json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest()
            if row["previous_hash"] != previous_hash or row["record_hash"] != expected:
                raise EvidenceError("provenance hash chain is invalid")
            record = ProvenanceRecord(
                row["sequence"],
                row["execution_id"],
                row["artifact_digest"],
                row["action"],
                row["previous_hash"],
                row["record_hash"],
            )
            records.append(record)
            previous_hash = record.record_hash
        return tuple(records)
