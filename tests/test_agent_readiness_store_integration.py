from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pytest

from services.agent_readiness import AgentReadinessProof
from services.agent_readiness_store import AgentReadinessStore
from services.agent_registry import ORCHESTRATOR_ID, registration_for


def _proof(*, executable: bool, regression: bool = False) -> AgentReadinessProof:
    verifier = registration_for(ORCHESTRATOR_ID).manifest.verifier_id
    return AgentReadinessProof(
        agent_id=ORCHESTRATOR_ID,
        verifier_id=verifier,
        invocation_passed=executable,
        skill_passed=executable,
        permission_passed=executable,
        provider_passed=executable,
        output_passed=executable,
        independent_verification_passed=executable,
        evidence_persisted=executable,
        desktop_projection_passed=executable,
        regression_e2e_passed=regression,
        evidence_digest="a" * 64 if executable else "",
    )


def test_readiness_store_isolated_append_only_and_evidence_derived(tmp_path: Path) -> None:
    path = tmp_path / "agent-readiness.sqlite3"
    store = AgentReadinessStore(path)
    registered = store.persist(_proof(executable=False), created_at=datetime.now(timezone.utc))
    assert registered.readiness.value == "registered"

    executable = store.persist(_proof(executable=True), created_at=datetime.now(timezone.utc))
    assert executable.readiness.value == "executable"
    assert store.latest(ORCHESTRATOR_ID) == executable
    assert len(store.verify()) == 2

    with sqlite3.connect(path) as connection, pytest.raises(sqlite3.DatabaseError):
        connection.execute(
            "UPDATE agent_readiness_evidence SET readiness = 'verified' WHERE sequence = 1"
        )


def test_verified_requires_regression_after_all_executable_gates(tmp_path: Path) -> None:
    store = AgentReadinessStore(tmp_path / "agent-readiness.sqlite3")
    record = store.persist(
        _proof(executable=True, regression=True),
        created_at=datetime.now(timezone.utc),
    )
    assert record.readiness.value == "verified"
