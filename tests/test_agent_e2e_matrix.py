"""Exact phase/readiness coverage for the canonical 47-agent E2E matrix."""

from datetime import datetime, timezone
from pathlib import Path

from services.agent_e2e_matrix import agent_e2e_matrix, matrix_summary
from services.agent_readiness import AgentReadinessProof
from services.agent_readiness_store import AgentReadinessStore
from services.agent_registry import RuntimeReadiness, registration_for
from services.control_plane.migrations import migrate_database

NOW = datetime(2026, 8, 18, 13, 0, tzinfo=timezone.utc)
PLANNER_ID = "ilaios.agent.core.planner.v1"


def _database(tmp_path: Path) -> Path:
    database = tmp_path / "state.sqlite3"
    migrate_database(database)
    return database


def test_empty_ledger_projects_exact_47_registered_rows_and_priority_counts(
    tmp_path: Path,
) -> None:
    database = _database(tmp_path)
    rows = agent_e2e_matrix(database)
    assert len(rows) == 47
    assert sum(row.phase == "P0" for row in rows) == 21
    assert sum(row.phase == "P1" for row in rows) == 18
    assert sum(row.phase == "P2" for row in rows) == 8
    assert {row.readiness for row in rows} == {RuntimeReadiness.REGISTERED}
    assert all(not row.executable_gate_passed for row in rows)
    assert all(not row.verified_gate_passed for row in rows)
    summary = matrix_summary(database)
    assert summary["total"] == 47
    assert summary["readiness"] == {
        "registered": 47,
        "executable": 0,
        "verified": 0,
    }


def test_one_verified_proof_changes_only_its_exact_agent_row(tmp_path: Path) -> None:
    database = _database(tmp_path)
    verifier_id = registration_for(PLANNER_ID).manifest.verifier_id
    proof = AgentReadinessProof(
        agent_id=PLANNER_ID,
        verifier_id=verifier_id,
        invocation_passed=True,
        skill_passed=True,
        permission_passed=True,
        provider_passed=True,
        output_passed=True,
        independent_verification_passed=True,
        evidence_persisted=True,
        desktop_projection_passed=True,
        regression_e2e_passed=True,
        evidence_digest="a" * 64,
    )
    record = AgentReadinessStore(database).persist(proof, created_at=NOW)
    rows = agent_e2e_matrix(database)
    planner = next(row for row in rows if row.agent_id == PLANNER_ID)
    assert planner.readiness is RuntimeReadiness.VERIFIED
    assert planner.executable_gate_passed is True
    assert planner.verified_gate_passed is True
    assert planner.evidence_id == record.evidence_id
    assert planner.evidence_digest == record.record_digest
    assert sum(row.readiness is RuntimeReadiness.VERIFIED for row in rows) == 1
    assert sum(row.readiness is RuntimeReadiness.REGISTERED for row in rows) == 46
