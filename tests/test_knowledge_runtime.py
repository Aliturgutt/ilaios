"""Durable runtime integration proofs for the canonical Knowledge/RAG plane."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from services.knowledge_runtime import (
    DurableKnowledgeRuntime,
    KnowledgeRuntimeConfig,
    KnowledgeRuntimeError,
    KnowledgeRuntimePolicy,
)


def _runtime(
    tmp_path: Path,
    *,
    tenant_id: str = "tenant-a",
    project_id: str = "project-a",
    principal_id: str = "service-rag",
) -> DurableKnowledgeRuntime:
    return DurableKnowledgeRuntime(
        KnowledgeRuntimeConfig(
            metadata_database=tmp_path / "knowledge.sqlite3",
            vector_database=tmp_path / "knowledge-vectors.sqlite3",
            policy=KnowledgeRuntimePolicy(
                principal_id=principal_id,
                tenant_id=tenant_id,
                project_id=project_id,
                allowed_classifications=frozenset({"PUBLIC", "INTERNAL"}),
                allowed_purposes=frozenset({"build", "research"}),
                allowed_residencies=frozenset({"eu"}),
            ),
        )
    )


def test_runtime_persists_source_and_retrieval_across_restart(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    source = runtime.ingest_source(
        source_id="source-a",
        locator="fixture://source-a",
        content="governed durable knowledge for the project",
        trusted=True,
        classifications=frozenset({"INTERNAL"}),
        purposes=frozenset({"build"}),
        residency="eu",
    )
    assert source["tenant_id"] == "tenant-a"

    first = runtime.retrieve(
        retrieval_id="retrieval-1",
        query="durable knowledge",
        purpose="build",
        top_k=5,
        candidate_limit=10,
        max_context_chars=2000,
    )
    units = first["units"]
    assert isinstance(units, list)
    assert [unit["source_id"] for unit in units] == ["source-a"]

    restarted = _runtime(tmp_path)
    state = restarted.state()
    assert state["event_count"] == 1
    assert state["retrieval_count"] == 1
    vector_index = state["vector_index"]
    assert isinstance(vector_index, dict)
    assert vector_index["row_count"] == 1
    second = restarted.retrieve(
        retrieval_id="retrieval-2",
        query="project knowledge",
        purpose="build",
        top_k=5,
        candidate_limit=10,
        max_context_chars=2000,
    )
    second_units = second["units"]
    assert isinstance(second_units, list)
    assert [unit["source_id"] for unit in second_units] == ["source-a"]


def test_runtime_scope_is_server_side_and_policy_rejects_excess_labels(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    assert runtime.tenant_id == "tenant-a"
    assert runtime.project_id == "project-a"
    with pytest.raises(KnowledgeRuntimeError, match="classification"):
        runtime.ingest_source(
            source_id="source-secret",
            locator="fixture://secret",
            content="classified material",
            trusted=True,
            classifications=frozenset({"SECRET"}),
            purposes=frozenset({"build"}),
            residency="eu",
        )
    with pytest.raises(KnowledgeRuntimeError, match="purpose"):
        runtime.retrieve(
            retrieval_id="retrieval-denied",
            query="anything",
            purpose="admin",
            top_k=5,
            candidate_limit=10,
            max_context_chars=2000,
        )


def test_runtime_scope_binding_rejects_cross_tenant_reopen(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    runtime.ingest_source(
        source_id="source-a",
        locator="fixture://a",
        content="tenant-a durable evidence",
        trusted=True,
        classifications=frozenset({"INTERNAL"}),
        purposes=frozenset({"build"}),
        residency="eu",
    )

    with pytest.raises(KnowledgeRuntimeError, match="scope binding mismatch"):
        _runtime(tmp_path, tenant_id="tenant-b")


def test_runtime_scope_binding_rejects_cross_project_or_principal_reopen(
    tmp_path: Path,
) -> None:
    _runtime(tmp_path)

    with pytest.raises(KnowledgeRuntimeError, match="scope binding mismatch"):
        _runtime(tmp_path, project_id="project-b")
    with pytest.raises(KnowledgeRuntimeError, match="scope binding mismatch"):
        _runtime(tmp_path, principal_id="service-other")


def test_runtime_scope_binding_tamper_fails_closed(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    runtime.ingest_source(
        source_id="source-a",
        locator="fixture://a",
        content="scope binding tamper evidence",
        trusted=True,
        classifications=frozenset({"INTERNAL"}),
        purposes=frozenset({"build"}),
        residency="eu",
    )
    with sqlite3.connect(tmp_path / "knowledge.sqlite3") as connection:
        connection.execute(
            "UPDATE knowledge_runtime_scope SET tenant_id = ? WHERE scope_id = 1",
            ("tenant-b",),
        )

    with pytest.raises(KnowledgeRuntimeError, match="scope binding mismatch"):
        runtime.state()
    with pytest.raises(KnowledgeRuntimeError, match="scope binding mismatch"):
        _runtime(tmp_path)


def test_runtime_refuses_legacy_unbound_nonempty_state(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    runtime.ingest_source(
        source_id="source-a",
        locator="fixture://a",
        content="legacy-state evidence",
        trusted=True,
        classifications=frozenset({"INTERNAL"}),
        purposes=frozenset({"build"}),
        residency="eu",
    )
    with sqlite3.connect(tmp_path / "knowledge.sqlite3") as connection:
        connection.execute("DELETE FROM knowledge_runtime_scope")

    with pytest.raises(KnowledgeRuntimeError, match="legacy Knowledge state"):
        _runtime(tmp_path)


def test_runtime_revoke_and_delete_reconcile_persisted_index(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    runtime.ingest_source(
        source_id="source-a",
        locator="fixture://a",
        content="revoke delete durable vector",
        trusted=True,
        classifications=frozenset({"INTERNAL"}),
        purposes=frozenset({"build"}),
        residency="eu",
    )
    first_index = runtime.state()["vector_index"]
    assert isinstance(first_index, dict)
    assert first_index["row_count"] == 1
    runtime.revoke_source(source_id="source-a")
    revoked_index = runtime.state()["vector_index"]
    assert isinstance(revoked_index, dict)
    assert revoked_index["row_count"] == 0

    restarted = _runtime(tmp_path)
    restarted_index = restarted.state()["vector_index"]
    assert isinstance(restarted_index, dict)
    assert restarted_index["row_count"] == 0
    restarted.delete_source(source_id="source-a")
    final = _runtime(tmp_path)
    final_index = final.state()["vector_index"]
    assert isinstance(final_index, dict)
    assert final_index["row_count"] == 0
    assert final.verify()["event_chain"] == "verified"


def test_runtime_rejects_event_chain_tampering_on_restart(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    runtime.ingest_source(
        source_id="source-a",
        locator="fixture://a",
        content="original content",
        trusted=True,
        classifications=frozenset({"INTERNAL"}),
        purposes=frozenset({"build"}),
        residency="eu",
    )
    with sqlite3.connect(tmp_path / "knowledge.sqlite3") as connection:
        connection.execute(
            "UPDATE knowledge_events SET payload_json = ? WHERE sequence = 1",
            ('{"source_id":"forged"}',),
        )
    with pytest.raises(KnowledgeRuntimeError, match="integrity"):
        _runtime(tmp_path)
