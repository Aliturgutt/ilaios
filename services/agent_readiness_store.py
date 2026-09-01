"""Append-only SQLite persistence for evidence-derived agent readiness.

This store is intentionally separate from the authoritative control-plane schema.
It owns only readiness evidence and therefore cannot widen control-plane authority
or force a destructive control-plane migration.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from services.agent_readiness import AgentReadinessProof, effective_readiness
from services.agent_registry import RuntimeReadiness, registration_for


class AgentReadinessStoreError(RuntimeError):
    """Readiness evidence persistence or reconstruction failed closed."""


@dataclass(frozen=True, slots=True)
class AgentReadinessRecord:
    sequence: int
    evidence_id: str
    agent_id: str
    verifier_id: str
    readiness: RuntimeReadiness
    producer_evidence_digest: str
    record_digest: str
    proof: AgentReadinessProof
    created_at: datetime


class AgentReadinessStore:
    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path.resolve()
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @property
    def database_path(self) -> Path:
        return self._database_path

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS agent_readiness_evidence (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    evidence_id TEXT UNIQUE NOT NULL,
                    agent_id TEXT NOT NULL,
                    verifier_id TEXT NOT NULL,
                    readiness TEXT NOT NULL CHECK (
                        readiness IN ('registered', 'executable', 'verified')
                    ),
                    producer_evidence_digest TEXT NOT NULL,
                    record_digest TEXT UNIQUE NOT NULL,
                    proof_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS agent_readiness_agent_sequence
                    ON agent_readiness_evidence(agent_id, sequence DESC);
                CREATE TRIGGER IF NOT EXISTS agent_readiness_no_update
                BEFORE UPDATE ON agent_readiness_evidence
                BEGIN
                    SELECT RAISE(ABORT, 'agent readiness evidence is append-only');
                END;
                CREATE TRIGGER IF NOT EXISTS agent_readiness_no_delete
                BEFORE DELETE ON agent_readiness_evidence
                BEGIN
                    SELECT RAISE(ABORT, 'agent readiness evidence is append-only');
                END;
                """
            )

    def persist(
        self,
        proof: AgentReadinessProof,
        *,
        created_at: datetime,
    ) -> AgentReadinessRecord:
        if created_at.tzinfo is None:
            raise AgentReadinessStoreError(
                "readiness evidence timestamp must be timezone-aware"
            )
        registration_for(proof.agent_id)
        readiness = effective_readiness(proof)
        material = {
            "proof": asdict(proof),
            "derived_readiness": readiness.value,
            "created_at": created_at.isoformat(),
        }
        canonical = json.dumps(
            material, sort_keys=True, separators=(",", ":")
        ).encode()
        digest = hashlib.sha256(canonical).hexdigest()
        evidence_id = f"agent-readiness-{digest[:24]}"
        with self._connect() as connection:
            try:
                cursor = connection.execute(
                    "INSERT INTO agent_readiness_evidence "
                    "(evidence_id, agent_id, verifier_id, readiness, "
                    "producer_evidence_digest, record_digest, proof_json, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        evidence_id,
                        proof.agent_id,
                        proof.verifier_id,
                        readiness.value,
                        proof.evidence_digest,
                        digest,
                        json.dumps(
                            asdict(proof), sort_keys=True, separators=(",", ":")
                        ),
                        created_at.isoformat(),
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise AgentReadinessStoreError(
                    "duplicate or invalid readiness evidence"
                ) from exc
            sequence = cursor.lastrowid
        if not isinstance(sequence, int):
            raise AgentReadinessStoreError(
                "readiness evidence sequence was not created"
            )
        return AgentReadinessRecord(
            sequence,
            evidence_id,
            proof.agent_id,
            proof.verifier_id,
            readiness,
            proof.evidence_digest,
            digest,
            proof,
            created_at,
        )

    def latest(self, agent_id: str) -> AgentReadinessRecord | None:
        registration_for(agent_id)
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM agent_readiness_evidence "
                "WHERE agent_id = ? ORDER BY sequence DESC LIMIT 1",
                (agent_id,),
            ).fetchone()
        return None if row is None else _record(row)

    def all_latest(self) -> tuple[AgentReadinessRecord, ...]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT evidence.* FROM agent_readiness_evidence AS evidence "
                "JOIN (SELECT agent_id, MAX(sequence) AS sequence "
                "      FROM agent_readiness_evidence GROUP BY agent_id) latest "
                "ON evidence.agent_id = latest.agent_id "
                "AND evidence.sequence = latest.sequence "
                "ORDER BY evidence.agent_id"
            ).fetchall()
        return tuple(_record(row) for row in rows)

    def verify(self) -> tuple[AgentReadinessRecord, ...]:
        """Reconstruct every record and detect tampering or semantic drift."""
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM agent_readiness_evidence ORDER BY sequence"
            ).fetchall()
        records = tuple(_record(row) for row in rows)
        expected = list(range(1, len(records) + 1))
        if [record.sequence for record in records] != expected:
            raise AgentReadinessStoreError("readiness evidence sequence has a gap")
        return records

    def projection(self) -> dict[str, dict[str, object]]:
        return {
            record.agent_id: {
                "readiness": record.readiness.value,
                "readiness_evidence_id": record.evidence_id,
                "readiness_evidence_digest": record.record_digest,
                "producer_evidence_digest": record.producer_evidence_digest,
                "verifier_id": record.verifier_id,
                "readiness_updated_at": record.created_at.isoformat(),
            }
            for record in self.all_latest()
        }

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection


def _record(row: sqlite3.Row) -> AgentReadinessRecord:
    try:
        raw = json.loads(row["proof_json"])
        proof = AgentReadinessProof(**raw)
        readiness = RuntimeReadiness(str(row["readiness"]))
        created_at = datetime.fromisoformat(str(row["created_at"]))
    except (json.JSONDecodeError, TypeError, ValueError, KeyError) as exc:
        raise AgentReadinessStoreError(
            "persisted readiness evidence is corrupt"
        ) from exc
    if created_at.tzinfo is None:
        raise AgentReadinessStoreError(
            "persisted readiness timestamp lost timezone"
        )
    if effective_readiness(proof) is not readiness:
        raise AgentReadinessStoreError(
            "persisted readiness diverges from evidence"
        )
    material: dict[str, Any] = {
        "proof": asdict(proof),
        "derived_readiness": readiness.value,
        "created_at": created_at.isoformat(),
    }
    expected_digest = hashlib.sha256(
        json.dumps(material, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    if expected_digest != row["record_digest"]:
        raise AgentReadinessStoreError("readiness evidence digest mismatch")
    return AgentReadinessRecord(
        int(row["sequence"]),
        str(row["evidence_id"]),
        proof.agent_id,
        proof.verifier_id,
        readiness,
        proof.evidence_digest,
        expected_digest,
        proof,
        created_at,
    )
