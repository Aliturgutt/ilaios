"""Adversarial proofs for the canonical ILAIOS Knowledge/RAG boundary."""

from dataclasses import replace

import pytest

from services.knowledge_rag import (
    AuthorizationDenied,
    InMemoryVectorIndex,
    KnowledgeRAG,
    KnowledgeRAGError,
    PrincipalScope,
    RAGSnapshot,
    RetrievalRequest,
    ScoredCandidate,
    _snapshot_evidence,
)


class RecordingIndex:
    """Record the exact authorization set presented to vector scoring."""

    def __init__(self) -> None:
        self.delegate = InMemoryVectorIndex()
        self.last_eligible: frozenset[str] = frozenset()

    def upsert(self, unit_id: str, vector: tuple[float, ...]) -> None:
        self.delegate.upsert(unit_id, vector)

    def delete(self, unit_ids: frozenset[str]) -> None:
        self.delegate.delete(unit_ids)

    def search(
        self,
        query_vector: tuple[float, ...],
        eligible_unit_ids: frozenset[str],
        limit: int,
    ) -> tuple[ScoredCandidate, ...]:
        self.last_eligible = eligible_unit_ids
        return self.delegate.search(query_vector, eligible_unit_ids, limit)


class MaliciousIndex(RecordingIndex):
    """Simulate an index/provider returning an ID outside its allowed set."""

    def search(
        self,
        query_vector: tuple[float, ...],
        eligible_unit_ids: frozenset[str],
        limit: int,
    ) -> tuple[ScoredCandidate, ...]:
        self.last_eligible = eligible_unit_ids
        return (ScoredCandidate("tenant-b-source:v1:u0", 1.0),)


def _scope() -> PrincipalScope:
    return PrincipalScope(
        principal_id="principal-a",
        tenant_id="tenant-a",
        project_id="project-a",
        allowed_classifications=frozenset({"INTERNAL"}),
        allowed_purposes=frozenset({"build"}),
        allowed_residencies=frozenset({"eu"}),
    )


def _request(retrieval_id: str = "retrieval-redteam") -> RetrievalRequest:
    return RetrievalRequest(
        retrieval_id=retrieval_id,
        scope=_scope(),
        query="canonical architecture evidence",
        purpose="build",
        top_k=3,
        candidate_limit=5,
        max_context_chars=2_000,
    )


def _ingest_two_tenants(rag: KnowledgeRAG) -> None:
    rag.ingest_source(
        "tenant-a-source",
        tenant_id="tenant-a",
        project_id="project-a",
        locator="fixture://tenant-a",
        content="canonical architecture evidence belongs to tenant A",
        trusted=True,
        classifications=frozenset({"INTERNAL"}),
        purposes=frozenset({"build"}),
        residency="eu",
    )
    rag.ingest_source(
        "tenant-b-source",
        tenant_id="tenant-b",
        project_id="project-b",
        locator="fixture://tenant-b",
        content="canonical architecture evidence belongs to tenant B",
        trusted=True,
        classifications=frozenset({"INTERNAL"}),
        purposes=frozenset({"build"}),
        residency="eu",
    )


def test_authorization_occurs_before_vector_scoring() -> None:
    index = RecordingIndex()
    rag = KnowledgeRAG(vector_index=index, chunk_size_words=20, chunk_overlap_words=0)
    _ingest_two_tenants(rag)

    result = rag.retrieve(_request())

    assert index.last_eligible
    assert all(unit_id.startswith("tenant-a-source:") for unit_id in index.last_eligible)
    assert all(unit.source_id == "tenant-a-source" for unit in result.units)


def test_index_cannot_smuggle_candidate_outside_authorized_set() -> None:
    index = MaliciousIndex()
    rag = KnowledgeRAG(vector_index=index, chunk_size_words=20, chunk_overlap_words=0)
    _ingest_two_tenants(rag)

    with pytest.raises(KnowledgeRAGError, match="unauthorized unit"):
        rag.retrieve(_request("retrieval-malicious-index"))


def test_authorized_context_rejects_query_evidence_and_citation_tampering() -> None:
    rag = KnowledgeRAG(chunk_size_words=20, chunk_overlap_words=0)
    _ingest_two_tenants(rag)
    request = _request("retrieval-integrity")
    result = rag.retrieve(request)
    assert result.units

    with pytest.raises(KnowledgeRAGError, match="query hash mismatch"):
        rag.build_authorized_context(
            request,
            replace(result, query_sha256="0" * 64),
        )

    with pytest.raises(KnowledgeRAGError, match="evidence hash mismatch"):
        rag.build_authorized_context(
            request,
            replace(result, evidence_sha256="f" * 64),
        )

    tampered_unit = replace(
        result.units[0],
        citation=replace(result.units[0].citation, locator="fixture://attacker"),
    )
    tampered_units = (tampered_unit, *result.units[1:])
    tampered_result = replace(result, units=tampered_units)
    with pytest.raises(KnowledgeRAGError, match="citation provenance mismatch"):
        rag.build_authorized_context(request, tampered_result)


def test_authorized_context_revalidates_revocation_after_retrieval() -> None:
    rag = KnowledgeRAG(chunk_size_words=20, chunk_overlap_words=0)
    _ingest_two_tenants(rag)
    request = _request("retrieval-revoked-after-read")
    result = rag.retrieve(request)
    assert result.units

    rag.revoke_source(
        "tenant-a-source",
        tenant_id="tenant-a",
        project_id="project-a",
    )

    with pytest.raises(AuthorizationDenied, match="unauthorized unit"):
        rag.build_authorized_context(request, result)


def test_restore_rejects_cross_scope_snapshot_even_with_recomputed_fingerprint() -> None:
    rag = KnowledgeRAG(chunk_size_words=20, chunk_overlap_words=0)
    rag.ingest_source(
        "source-a",
        tenant_id="tenant-a",
        project_id="project-a",
        locator="fixture://source-a",
        content="durable canonical knowledge evidence",
        trusted=True,
        classifications=frozenset({"INTERNAL"}),
        purposes=frozenset({"build"}),
        residency="eu",
    )
    snapshot = rag.snapshot(tenant_id="tenant-a", project_id="project-a")
    forged_sources = (replace(snapshot.sources[0], tenant_id="tenant-b"),)
    forged_hash = _snapshot_evidence(
        snapshot.tenant_id,
        snapshot.project_id,
        snapshot.provider_id,
        forged_sources,
        snapshot.versions,
        snapshot.units,
        snapshot.active_unit_ids,
    )
    forged = RAGSnapshot(
        tenant_id=snapshot.tenant_id,
        project_id=snapshot.project_id,
        provider_id=snapshot.provider_id,
        sources=forged_sources,
        versions=snapshot.versions,
        units=snapshot.units,
        active_unit_ids=snapshot.active_unit_ids,
        evidence_sha256=forged_hash,
    )

    with pytest.raises(KnowledgeRAGError, match="source scope mismatch"):
        KnowledgeRAG(chunk_size_words=20, chunk_overlap_words=0).restore(forged)
