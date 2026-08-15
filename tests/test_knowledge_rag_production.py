"""RAG.14 durable readiness and fail-closed promotion proofs."""

from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path

import pytest

from services.deployment.backup import RuntimeBackupManager
from services.knowledge_rag import (
    DeterministicHashEmbeddingProvider,
    KnowledgeRAG,
    PrincipalScope,
    RetrievalRequest,
)
from services.knowledge_rag_production import (
    RAG14_REQUIREMENTS,
    RAG14EvidenceItem,
    RAG14PromotionGate,
    RAGProductionReadinessError,
    SQLiteVectorIndex,
)


_EXACT_SCOPE = "source:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@image:sha256:bbbb"


def _sha(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def test_sqlite_vector_index_persists_and_scores_only_eligible_ids(tmp_path: Path) -> None:
    database = tmp_path / "rag" / "vectors.sqlite3"
    provider = DeterministicHashEmbeddingProvider(dimensions=16)
    index = SQLiteVectorIndex(database)
    alpha = provider.embed("alpha governed knowledge")
    beta = provider.embed("beta private knowledge")
    index.upsert("unit-alpha", alpha)
    index.upsert("unit-beta", beta)

    reopened = SQLiteVectorIndex(database)
    result = reopened.search(alpha, frozenset({"unit-alpha"}), 5)

    assert [item.unit_id for item in result] == ["unit-alpha"]
    assert reopened.health().row_count == 2
    assert reopened.health().integrity_ok is True


def test_sqlite_vector_index_detects_persisted_vector_tampering(tmp_path: Path) -> None:
    database = tmp_path / "vectors.sqlite3"
    provider = DeterministicHashEmbeddingProvider(dimensions=16)
    index = SQLiteVectorIndex(database)
    index.upsert("unit-a", provider.embed("tamper resistant vector"))

    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE rag_vectors SET vector_json = ? WHERE unit_id = ?",
            ("[0.0,1.0]", "unit-a"),
        )

    with pytest.raises(RAGProductionReadinessError, match="integrity"):
        index.health()


def test_vector_delete_survives_restart(tmp_path: Path) -> None:
    database = tmp_path / "vectors.sqlite3"
    provider = DeterministicHashEmbeddingProvider(dimensions=16)
    vector = provider.embed("revoked source")
    index = SQLiteVectorIndex(database)
    index.upsert("unit-a", vector)
    index.delete(frozenset({"unit-a"}))

    reopened = SQLiteVectorIndex(database)
    assert reopened.search(vector, frozenset({"unit-a"}), 1) == ()
    assert reopened.health().row_count == 0


def test_sqlite_vector_state_is_covered_by_runtime_backup_restore(tmp_path: Path) -> None:
    state_root = tmp_path / "state"
    database = state_root / "rag" / "vectors.sqlite3"
    provider = DeterministicHashEmbeddingProvider(dimensions=16)
    vector = provider.embed("durable backup knowledge")
    index = SQLiteVectorIndex(database)
    index.upsert("unit-a", vector)

    archive = tmp_path / "backup.zip"
    manager = RuntimeBackupManager()
    manifest = manager.backup(state_root, archive)
    restored_root = tmp_path / "restored"
    manager.restore(archive, restored_root)

    restored = SQLiteVectorIndex(restored_root / "rag" / "vectors.sqlite3")
    result = restored.search(vector, frozenset({"unit-a"}), 1)

    files = manifest["files"]
    assert isinstance(files, dict)
    assert "rag/vectors.sqlite3" in files
    assert [item.unit_id for item in result] == ["unit-a"]
    assert restored.health().row_count == 1


def test_knowledge_rag_can_use_durable_index_without_changing_auth_order(tmp_path: Path) -> None:
    index = SQLiteVectorIndex(tmp_path / "vectors.sqlite3")
    rag = KnowledgeRAG(vector_index=index, chunk_size_words=20, chunk_overlap_words=0)
    rag.ingest_source(
        "source-a",
        tenant_id="tenant-a",
        project_id="project-a",
        locator="fixture://a",
        content="governed durable retrieval evidence",
        trusted=True,
        classifications=frozenset({"INTERNAL"}),
        purposes=frozenset({"build"}),
        residency="eu",
    )
    rag.ingest_source(
        "source-b",
        tenant_id="tenant-b",
        project_id="project-b",
        locator="fixture://b",
        content="governed durable retrieval hidden tenant",
        trusted=True,
        classifications=frozenset({"INTERNAL"}),
        purposes=frozenset({"build"}),
        residency="eu",
    )

    result = rag.retrieve(
        RetrievalRequest(
            retrieval_id="durable-auth",
            scope=PrincipalScope(
                principal_id="principal-a",
                tenant_id="tenant-a",
                project_id="project-a",
                allowed_classifications=frozenset({"INTERNAL"}),
                allowed_purposes=frozenset({"build"}),
                allowed_residencies=frozenset({"eu"}),
            ),
            query="governed durable retrieval",
            purpose="build",
            top_k=5,
            candidate_limit=10,
            max_context_chars=2_000,
        )
    )

    assert {unit.source_id for unit in result.units} == {"source-a"}
    assert index.health().row_count == 2


def test_rag14_gate_stays_blocked_until_every_required_proof_exists() -> None:
    first = RAG14EvidenceItem(
        requirement=RAG14_REQUIREMENTS[0],
        evidence_ref="evidence://embedding/provider",
        evidence_sha256=_sha("embedding"),
        verified_by="ilaios.governance.production-evidence",
        exact_release_scope=_EXACT_SCOPE,
    )

    report = RAG14PromotionGate().evaluate((first,))

    assert report.status == "BLOCKED"
    assert report.satisfied_requirements == (RAG14_REQUIREMENTS[0],)
    assert len(report.missing_requirements) == len(RAG14_REQUIREMENTS) - 1
    assert report.production_approved is False


def test_rag14_gate_rejects_duplicate_malformed_or_cross_scope_evidence() -> None:
    valid = RAG14EvidenceItem(
        requirement=RAG14_REQUIREMENTS[0],
        evidence_ref="evidence://embedding/provider",
        evidence_sha256=_sha("embedding"),
        verified_by="ilaios.governance.production-evidence",
        exact_release_scope=_EXACT_SCOPE,
    )
    with pytest.raises(RAGProductionReadinessError, match="duplicate"):
        RAG14PromotionGate().evaluate((valid, valid))

    with pytest.raises(RAGProductionReadinessError, match="SHA-256"):
        RAG14EvidenceItem(
            requirement=RAG14_REQUIREMENTS[1],
            evidence_ref="evidence://vector/index",
            evidence_sha256="not-a-sha",
            verified_by="ilaios.governance.production-evidence",
            exact_release_scope=_EXACT_SCOPE,
        )

    other_scope = RAG14EvidenceItem(
        requirement=RAG14_REQUIREMENTS[1],
        evidence_ref="evidence://vector/index",
        evidence_sha256=_sha("vector"),
        verified_by="ilaios.governance.production-evidence",
        exact_release_scope="source:cccc@image:sha256:dddd",
    )
    with pytest.raises(RAGProductionReadinessError, match="one exact release scope"):
        RAG14PromotionGate().evaluate((valid, other_scope))


def test_complete_rag14_evidence_only_allows_governed_review_not_auto_production() -> None:
    items = tuple(
        RAG14EvidenceItem(
            requirement=requirement,
            evidence_ref=f"evidence://rag14/{requirement}",
            evidence_sha256=_sha(requirement),
            verified_by="ilaios.governance.production-evidence",
            exact_release_scope=_EXACT_SCOPE,
        )
        for requirement in RAG14_REQUIREMENTS
    )

    report = RAG14PromotionGate().evaluate(items)

    assert report.status == "READY_FOR_GOVERNED_PROMOTION_REVIEW"
    assert report.missing_requirements == ()
    assert report.satisfied_requirements == RAG14_REQUIREMENTS
    assert len(report.evidence_sha256) == 64
    assert report.production_approved is False
