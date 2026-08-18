"""Append-only SQLite persistence for evidence-derived agent readiness."""

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
        self._database_path = database_path

    def persist(
        self,
        proof: AgentReadinessProof,
        *,
        created_at: datetime,
    ) -> AgentReadinessRecord:
        if created_at.tzinfo is None:
            raise AgentReadinessStoreError("readiness evidence timestamp must be timezone-aware")
        registration_for(proof.agent_id)
        readiness = effective_readiness(proof)
        material = {
            "proof": asdict(proof),
            "derived_readiness": readiness.value,
            "created_at": created_at.isoformat(),
        }
        canonical = json.dumps(material, sort_keys=True, separators=(",", ":")).encode()
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
                        json.dumps(asdict(proof), sort_keys=True, separators=(",", ":")),
                        created_at.isoformat(),
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise AgentReadinessStoreError("duplicate or invalid readiness evidence") from exc
            sequence = cursor.lastrowid
        if not isinstance(sequence, int):
            raise AgentReadinessStoreError("readiness evidence sequence was not created")
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
        """Return at most one latest evidence row per canonical agent."""
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

    def projection(self) -> dict[str, dict[str, object]]:
        """Return Desktop/control-plane-safe latest readiness telemetry."""
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
        connection = sqlite3.connect(self._database_path)
        connection.row_factory = sqlite3.Row
        return connection


def _record(row: sqlite3.Row) -> AgentReadinessRecord:
    try:
        raw = json.loads(row["proof_json"])
        proof = AgentReadinessProof(**raw)
        readiness = RuntimeReadiness(str(row["readiness"]))
        created_at = datetime.fromisoformat(str(row["created_at"]))
    except (json.JSONDecodeError, TypeError, ValueError, KeyError) as exc:
        raise AgentReadinessStoreError("persisted readiness evidence is corrupt") from exc
    if created_at.tzinfo is None:
        raise AgentReadinessStoreError("persisted readiness timestamp lost timezone")
    if effective_readiness(proof) is not readiness:
        raise AgentReadinessStoreError("persisted readiness diverges from evidence")
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
