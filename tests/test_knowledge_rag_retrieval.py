from dataclasses import replace

import pytest

from src.knowledge_rag.retrieval import (
    AuthorizationAwareRetriever,
    RetrievalError,
    RetrievalRequest,
)


def _index() -> AuthorizationAwareRetriever:
    index = AuthorizationAwareRetriever()
    index.register_chunk(
        "chunk-a",
        tenant_id="tenant-a",
        project_id="project-a",
        source_id="source-a",
        content="ILAIOS authorization aware retrieval keeps project context governed.",
        classification="internal",
        residency="eu",
        allowed_principal_ids=frozenset({"user-a"}),
        allowed_purposes=frozenset({"product-build"}),
        authorization_epoch=3,
        provenance={"locator": "repo://docs/a", "source_sha256": "a" * 64},
    )
    index.register_chunk(
        "chunk-b",
        tenant_id="tenant-b",
        project_id="project-b",
        source_id="source-b",
        content="ILAIOS authorization data belonging to another tenant must never leak.",
        classification="internal",
        residency="eu",
        allowed_principal_ids=frozenset({"user-a"}),
        allowed_purposes=frozenset({"product-build"}),
        authorization_epoch=3,
        provenance={"locator": "repo://docs/b", "source_sha256": "b" * 64},
    )
    return index


def _request() -> RetrievalRequest:
    return RetrievalRequest(
        tenant_id="tenant-a",
        project_id="project-a",
        principal_id="user-a",
        purpose="product-build",
        query="ILAIOS authorization retrieval",
        allowed_classifications=frozenset({"internal"}),
        required_residency="eu",
        authorization_epoch=3,
        max_results=5,
    )


def test_retrieval_returns_only_authorized_same_tenant_context_with_evidence() -> None:
    index = _index()
    results, evidence = index.retrieve(_request())

    assert [result.chunk_id for result in results] == ["chunk-a"]
    assert evidence.tenant_id == "tenant-a"
    assert evidence.project_id == "project-a"
    assert evidence.result_ids == ("chunk-a",)
    assert evidence.result_sha256s == (results[0].content_sha256,)
    assert len(evidence.query_sha256) == 64
    assert len(evidence.evidence_sha256) == 64


def test_cross_tenant_and_cross_project_context_is_not_returned() -> None:
    index = _index()
    results, _ = index.retrieve(replace(_request(), tenant_id="tenant-b"))
    assert results == ()

    results, _ = index.retrieve(replace(_request(), project_id="project-b"))
    assert results == ()


def test_principal_purpose_classification_and_residency_are_pre_retrieval_gates() -> None:
    index = _index()
    for request in (
        replace(_request(), principal_id="user-x"),
        replace(_request(), purpose="analytics"),
        replace(_request(), allowed_classifications=frozenset({"public"})),
        replace(_request(), required_residency="us"),
    ):
        results, evidence = index.retrieve(request)
        assert results == ()
        assert evidence.result_ids == ()


def test_revoked_stale_and_retention_invalid_sources_do_not_reappear() -> None:
    index = _index()
    index.revoke_source("source-a")
    results, _ = index.retrieve(_request())
    assert results == ()

    fresh = AuthorizationAwareRetriever()
    fresh.register_chunk(
        "stale",
        tenant_id="tenant-a",
        project_id="project-a",
        source_id="source-stale",
        content="authorization retrieval stale source",
        classification="internal",
        residency="eu",
        allowed_principal_ids=frozenset({"user-a"}),
        allowed_purposes=frozenset({"product-build"}),
        authorization_epoch=2,
        provenance={"locator": "repo://stale"},
    )
    fresh.register_chunk(
        "expired",
        tenant_id="tenant-a",
        project_id="project-a",
        source_id="source-expired",
        content="authorization retrieval expired source",
        classification="internal",
        residency="eu",
        allowed_principal_ids=frozenset({"user-a"}),
        allowed_purposes=frozenset({"product-build"}),
        authorization_epoch=3,
        retention_valid=False,
        provenance={"locator": "repo://expired"},
    )
    results, _ = fresh.retrieve(_request())
    assert results == ()


def test_ranking_and_evidence_are_deterministic() -> None:
    index = _index()
    first_results, first_evidence = index.retrieve(_request())
    second_results, second_evidence = index.retrieve(_request())
    assert first_results == second_results
    assert first_evidence == second_evidence


def test_request_and_registration_fail_closed_on_unbounded_or_missing_security_inputs() -> None:
    index = AuthorizationAwareRetriever()
    with pytest.raises(RetrievalError, match="principal authorization"):
        index.register_chunk(
            "bad",
            tenant_id="tenant-a",
            project_id="project-a",
            source_id="source-a",
            content="context",
            classification="internal",
            residency="eu",
            allowed_principal_ids=frozenset(),
            allowed_purposes=frozenset({"build"}),
            authorization_epoch=1,
            provenance={"locator": "repo://a"},
        )

    with pytest.raises(RetrievalError, match="between 1 and 20"):
        index.retrieve(replace(_request(), max_results=21))

    with pytest.raises(RetrievalError, match="allowed_classifications"):
        index.retrieve(replace(_request(), allowed_classifications=frozenset()))
