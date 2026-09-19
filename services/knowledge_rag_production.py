"""Durable RAG.14 readiness primitives without autonomous production authority."""

from __future__ import annotations

import hashlib
import json
import math
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from services.knowledge_rag import KnowledgeRAGError, ScoredCandidate


class RAGProductionReadinessError(KnowledgeRAGError):
    """Raised when durable RAG state or promotion evidence is invalid."""


@dataclass(frozen=True, slots=True)
class VectorIndexHealthReport:
    adapter_id: str
    row_count: int
    integrity_ok: bool
    evidence_sha256: str


class SQLiteVectorIndex:
    """Durable exact-ID vector index that only scores pre-authorized IDs.

    This adapter intentionally has no tenant or authorization policy of its own.
    The canonical KnowledgeRAG service must compute the eligible unit set before
    calling search(). The database persists vectors across process restarts and
    is compatible with the repository RuntimeBackupManager because it is SQLite.
    """

    adapter_id = "ilaios.rag.vector.sqlite.v1"

    def __init__(self, database: Path) -> None:
        if database.exists() and database.is_symlink():
            raise RAGProductionReadinessError("vector database must not be a symlink")
        database.parent.mkdir(parents=True, exist_ok=True)
        self._database = database
        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("PRAGMA synchronous=FULL")
            connection.execute(
                "CREATE TABLE IF NOT EXISTS rag_vectors ("
                "unit_id TEXT PRIMARY KEY, "
                "dimension INTEGER NOT NULL, "
                "vector_json TEXT NOT NULL, "
                "vector_sha256 TEXT NOT NULL)"
            )

    @property
    def state_path(self) -> Path:
        return self._database

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database)
        connection.row_factory = sqlite3.Row
        return connection

    def upsert(self, unit_id: str, vector: tuple[float, ...]) -> None:
        _require_id(unit_id, "unit_id")
        payload = _encode_vector(vector)
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "INSERT INTO rag_vectors (unit_id, dimension, vector_json, vector_sha256) "
                "VALUES (?, ?, ?, ?) "
                "ON CONFLICT(unit_id) DO UPDATE SET "
                "dimension=excluded.dimension, vector_json=excluded.vector_json, "
                "vector_sha256=excluded.vector_sha256",
                (unit_id, len(vector), payload, digest),
            )

    def delete(self, unit_ids: frozenset[str]) -> None:
        if not unit_ids:
            return
        for unit_id in unit_ids:
            _require_id(unit_id, "unit_id")
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.executemany(
                "DELETE FROM rag_vectors WHERE unit_id = ?",
                ((unit_id,) for unit_id in sorted(unit_ids)),
            )

    def reset(self) -> None:
        """Clear derived vector rows before deterministic rebuild from source truth."""
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("DELETE FROM rag_vectors")

    def search(
        self,
        query_vector: tuple[float, ...],
        eligible_unit_ids: frozenset[str],
        limit: int,
    ) -> tuple[ScoredCandidate, ...]:
        query = _validated_vector(query_vector)
        if limit < 1:
            raise RAGProductionReadinessError("search limit must be positive")
        if not eligible_unit_ids:
            return ()
        for unit_id in eligible_unit_ids:
            _require_id(unit_id, "eligible unit_id")

        scored: list[ScoredCandidate] = []
        with self._connect() as connection:
            for unit_id in sorted(eligible_unit_ids):
                row = connection.execute(
                    "SELECT dimension, vector_json, vector_sha256 "
                    "FROM rag_vectors WHERE unit_id = ?",
                    (unit_id,),
                ).fetchone()
                if row is None:
                    continue
                vector = _decode_verified_vector(
                    str(row["vector_json"]),
                    str(row["vector_sha256"]),
                    int(row["dimension"]),
                )
                if len(vector) != len(query):
                    raise RAGProductionReadinessError("embedding dimension mismatch")
                score = sum(a * b for a, b in zip(query, vector, strict=True))
                if not math.isfinite(score):
                    raise RAGProductionReadinessError("retrieval score must be finite")
                scored.append(ScoredCandidate(unit_id=unit_id, semantic_score=score))
        scored.sort(key=lambda item: (-item.semantic_score, item.unit_id))
        return tuple(scored[:limit])

    def health(self) -> VectorIndexHealthReport:
        evidence_parts: list[str] = []
        with self._connect() as connection:
            integrity_row = connection.execute("PRAGMA integrity_check").fetchone()
            integrity_ok = integrity_row is not None and str(integrity_row[0]) == "ok"
            if not integrity_ok:
                raise RAGProductionReadinessError("vector database integrity check failed")
            rows = connection.execute(
                "SELECT unit_id, dimension, vector_json, vector_sha256 "
                "FROM rag_vectors ORDER BY unit_id"
            ).fetchall()
        for row in rows:
            unit_id = str(row["unit_id"])
            vector = _decode_verified_vector(
                str(row["vector_json"]),
                str(row["vector_sha256"]),
                int(row["dimension"]),
            )
            evidence_parts.append(
                f"{unit_id}:{len(vector)}:{str(row['vector_sha256'])}"
            )
        material = "|".join((self.adapter_id, *evidence_parts))
        return VectorIndexHealthReport(
            adapter_id=self.adapter_id,
            row_count=len(rows),
            integrity_ok=True,
            evidence_sha256=hashlib.sha256(material.encode("utf-8")).hexdigest(),
        )


RAG14_REQUIREMENTS: tuple[str, ...] = (
    "production_embedding_provider",
    "durable_vector_index",
    "production_tenant_isolation",
    "production_authorization_policy",
    "production_dlp_and_injection_controls",
    "production_leakage_redteam",
    "production_backup_restore",
    "production_deletion_reconciliation",
    "production_observability_slo",
    "production_routing_finops",
    "exact_release_artifact",
    "exact_deployment_result",
    "deployment_health",
    "rollback_recovery",
)


@dataclass(frozen=True, slots=True)
class RAG14EvidenceItem:
    requirement: str
    evidence_ref: str
    evidence_sha256: str
    verified_by: str
    exact_release_scope: str

    def __post_init__(self) -> None:
        if self.requirement not in RAG14_REQUIREMENTS:
            raise RAGProductionReadinessError("unknown RAG.14 evidence requirement")
        _require_id(self.evidence_ref, "evidence_ref")
        _require_sha256(self.evidence_sha256, "evidence_sha256")
        _require_id(self.verified_by, "verified_by")
        _require_id(self.exact_release_scope, "exact_release_scope")


@dataclass(frozen=True, slots=True)
class RAG14ReadinessReport:
    status: str
    satisfied_requirements: tuple[str, ...]
    missing_requirements: tuple[str, ...]
    evidence_sha256: str
    production_approved: bool


class RAG14PromotionGate:
    """Fail-closed evidence completeness gate.

    Even a complete report is only READY_FOR_GOVERNED_PROMOTION_REVIEW. This
    component never deploys, mutates production, or sets production_approved.
    """

    def evaluate(self, items: tuple[RAG14EvidenceItem, ...]) -> RAG14ReadinessReport:
        by_requirement: dict[str, RAG14EvidenceItem] = {}
        release_scopes: set[str] = set()
        for item in items:
            if item.requirement in by_requirement:
                raise RAGProductionReadinessError("duplicate RAG.14 evidence requirement")
            by_requirement[item.requirement] = item
            release_scopes.add(item.exact_release_scope)
        if len(release_scopes) > 1:
            raise RAGProductionReadinessError(
                "RAG.14 evidence items must bind one exact release scope"
            )

        satisfied = tuple(
            requirement
            for requirement in RAG14_REQUIREMENTS
            if requirement in by_requirement
        )
        missing = tuple(
            requirement
            for requirement in RAG14_REQUIREMENTS
            if requirement not in by_requirement
        )
        evidence_material = "|".join(
            f"{item.requirement}:{item.evidence_ref}:{item.evidence_sha256}:"
            f"{item.verified_by}:{item.exact_release_scope}"
            for item in sorted(items, key=lambda current: current.requirement)
        )
        evidence_sha = hashlib.sha256(evidence_material.encode("utf-8")).hexdigest()
        status = "BLOCKED" if missing else "READY_FOR_GOVERNED_PROMOTION_REVIEW"
        return RAG14ReadinessReport(
            status=status,
            satisfied_requirements=satisfied,
            missing_requirements=missing,
            evidence_sha256=evidence_sha,
            production_approved=False,
        )


def _require_id(value: str, name: str) -> None:
    if not value or value != value.strip():
        raise RAGProductionReadinessError(f"{name} must be non-empty and trimmed")


def _require_sha256(value: str, name: str) -> None:
    if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        raise RAGProductionReadinessError(f"{name} must be lowercase SHA-256")


def _validated_vector(vector: tuple[float, ...]) -> tuple[float, ...]:
    if not vector:
        raise RAGProductionReadinessError("vector must not be empty")
    if not all(math.isfinite(value) for value in vector):
        raise RAGProductionReadinessError("vector values must be finite")
    return vector


def _encode_vector(vector: tuple[float, ...]) -> str:
    validated = _validated_vector(vector)
    return json.dumps(validated, separators=(",", ":"), allow_nan=False)


def _decode_verified_vector(
    payload: str, expected_sha256: str, dimension: int
) -> tuple[float, ...]:
    if dimension < 1:
        raise RAGProductionReadinessError("stored vector dimension is invalid")
    _require_sha256(expected_sha256, "stored vector SHA")
    actual = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    if actual != expected_sha256:
        raise RAGProductionReadinessError("stored vector integrity check failed")
    raw: object = json.loads(payload)
    if not isinstance(raw, list):
        raise RAGProductionReadinessError("stored vector payload is invalid")
    values: list[float] = []
    for item in raw:
        if isinstance(item, bool) or not isinstance(item, (int, float)):
            raise RAGProductionReadinessError("stored vector value is invalid")
        value = float(item)
        if not math.isfinite(value):
            raise RAGProductionReadinessError("stored vector value is not finite")
        values.append(value)
    vector = tuple(values)
    if len(vector) != dimension:
        raise RAGProductionReadinessError("stored vector dimension mismatch")
    return vector
