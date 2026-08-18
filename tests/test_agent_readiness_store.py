"""Persistent readiness evidence ledger tests."""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pytest

from services.agent_readiness import AgentReadinessProof
from services.agent_readiness_store import AgentReadinessStore, AgentReadinessStoreError
from services.agent_registry import RuntimeReadiness, registration_for
from services.control_plane.migrations import LATEST_SCHEMA_VERSION, migrate_database

NOW = datetime(2026, 8, 18, 11, 0, tzinfo=timezone.utc)
AGENT_ID = "ilaios.agent.engineering.core.v1"


def _proof(*, regression: bool = False) -> AgentReadinessProof:
    return AgentReadinessProof(
        agent_id=AGENT_ID,
        verifier_id=registration_for(AGENT_ID).manifest.verifier_id,
        invocation_passed=True,
        skill_passed=True,
        permission_passed=True,
        provider_passed=True,
        output_passed=True,
        independent_verification_passed=True,
        evidence_persisted=True,
        desktop_projection_passed=True,
        regression_e2e_passed=regression,
        evidence_digest="a" * 64,
    )


def test_migration_creates_schema_v8_append_only_readiness_ledger(tmp_path: Path) -> None:
    database = tmp_path / "state.sqlite3"
    assert migrate_database(database) == LATEST_SCHEMA_VERSION == 8
    with sqlite3.connect(database) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        triggers = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='trigger'"
            )
        }
    assert "agent_readiness_evidence" in tables
    assert "agent_readiness_no_update" in triggers
    assert "agent_readiness_no_delete" in triggers


def test_store_derives_executable_then_verified_without_static_registry_promotion(
    tmp_path: Path,
) -> None:
    database = tmp_path / "state.sqlite3"
    migrate_database(database)
    store = AgentReadinessStore(database)
    executable = store.persist(_proof(), created_at=NOW)
    verified = store.persist(
        _proof(regression=True),
        created_at=NOW.replace(minute=1),
    )
    assert executable.readiness is RuntimeReadiness.EXECUTABLE
    assert verified.readiness is RuntimeReadiness.VERIFIED
    latest = store.latest(AGENT_ID)
    assert latest is not None and latest.readiness is RuntimeReadiness.VERIFIED
    assert registration_for(AGENT_ID).readiness is RuntimeReadiness.REGISTERED
    projection = store.projection()[AGENT_ID]
    assert projection["readiness"] == "verified"
    assert len(str(projection["readiness_evidence_digest"])) == 64


def test_duplicate_record_and_sql_update_delete_fail_closed(tmp_path: Path) -> None:
    database = tmp_path / "state.sqlite3"
    migrate_database(database)
    store = AgentReadinessStore(database)
    store.persist(_proof(), created_at=NOW)
    with pytest.raises(AgentReadinessStoreError, match="duplicate"):
        store.persist(_proof(), created_at=NOW)

    with sqlite3.connect(database) as connection:
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute(
                "UPDATE agent_readiness_evidence SET readiness='verified' WHERE agent_id=?",
                (AGENT_ID,),
            )
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute(
                "DELETE FROM agent_readiness_evidence WHERE agent_id=?",
                (AGENT_ID,),
            )


def test_partial_evidence_can_be_recorded_but_remains_registered(tmp_path: Path) -> None:
    database = tmp_path / "state.sqlite3"
    migrate_database(database)
    store = AgentReadinessStore(database)
    proof = AgentReadinessProof(
        agent_id=AGENT_ID,
        verifier_id=registration_for(AGENT_ID).manifest.verifier_id,
        invocation_passed=True,
        skill_passed=True,
        permission_passed=True,
        provider_passed=False,
        output_passed=False,
        independent_verification_passed=False,
        evidence_persisted=False,
        desktop_projection_passed=False,
        regression_e2e_passed=False,
        evidence_digest="",
    )
    record = store.persist(proof, created_at=NOW)
    assert record.readiness is RuntimeReadiness.REGISTERED
