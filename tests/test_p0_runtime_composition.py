"""Single-runtime P0 composition and restart/drift proofs."""

import json
import sqlite3
from pathlib import Path

import pytest

from services.control_plane.migrations import migrate_database
from services.independent_verifier_execution import INDEPENDENT_VERIFIER_PROVIDER_ID
from services.p0_runtime_composition import (
    P0RuntimeCompositionError,
    compose_p0_runtime,
)
from services.runtime import GovernedRuntime, GrantPolicy
from services.runtime.security_agent_adapters import SecurityAgentRuntimeAdapters
from services.software_factory_skills import default_skills_root

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_SKILL_ENGINEERING_AUTHORITIES = {
    "skill-create": ["architecture.propose"],
    "skill-validate": ["test.execute"],
    "skill-evaluate": ["code.review"],
    "skill-benchmark": ["test.execute"],
    "skill-regression": ["test.execute"],
}


def _runtime(tmp_path: Path) -> tuple[Path, GovernedRuntime]:
    database = tmp_path / "state.sqlite3"
    migrate_database(database)
    security = SecurityAgentRuntimeAdapters()
    return database, GovernedRuntime(
        database,
        external_adapters=security.runtime_adapters(),
    )


def test_p0_composes_exact_targets_plus_verifier_dependency_on_same_runtime(
    tmp_path: Path,
) -> None:
    database, runtime = _runtime(tmp_path)
    composition = compose_p0_runtime(
        runtime,
        GrantPolicy(),
        engineering_skills_root=default_skills_root(ROOT),
    )
    assert composition.target_agent_count == 21
    assert composition.provisioned_identity_count == 22
    assert composition.skill_count == 32
    assert composition.skill_engineering_skill_count == 5
    assert composition.security_provider_count == 5
    assert composition.verifier_provider_count == 1
    assert composition.ai_provider_count == 0
    assert composition.ai_configured is False

    with sqlite3.connect(database) as connection:
        agent_count = connection.execute(
            "SELECT COUNT(*) FROM runtime_agents"
        ).fetchone()[0]
        skill_count = connection.execute(
            "SELECT COUNT(*) FROM runtime_skills"
        ).fetchone()[0]
        skill_engineering_rows = connection.execute(
            "SELECT skill_id, authorities_json FROM runtime_skills "
            "WHERE skill_id LIKE 'skill-%' ORDER BY skill_id"
        ).fetchall()
        provider_rows = connection.execute(
            "SELECT provider_id, deterministic "
            "FROM runtime_providers ORDER BY provider_id"
        ).fetchall()
    assert agent_count == 22
    assert skill_count == 32
    assert {
        skill_id: json.loads(authorities_json)
        for skill_id, authorities_json in skill_engineering_rows
    } == EXPECTED_SKILL_ENGINEERING_AUTHORITIES
    assert len(provider_rows) == 6
    assert all(deterministic == 1 for _, deterministic in provider_rows)
    assert any(
        provider_id == INDEPENDENT_VERIFIER_PROVIDER_ID
        for provider_id, _ in provider_rows
    )


def test_p0_composition_is_restart_idempotent(tmp_path: Path) -> None:
    database, runtime = _runtime(tmp_path)
    first = compose_p0_runtime(
        runtime,
        GrantPolicy(),
        engineering_skills_root=default_skills_root(ROOT),
    )
    second = compose_p0_runtime(
        runtime,
        GrantPolicy(),
        engineering_skills_root=default_skills_root(ROOT),
    )
    assert first.target_agent_count == second.target_agent_count == 21
    assert first.skill_engineering_skill_count == second.skill_engineering_skill_count == 5
    with sqlite3.connect(database) as connection:
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM runtime_agents"
            ).fetchone()[0]
            == 22
        )
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM runtime_skills"
            ).fetchone()[0]
            == 32
        )
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM runtime_providers"
            ).fetchone()[0]
            == 6
        )


def test_ai_capability_contract_cannot_exist_without_governed_adapter(
    tmp_path: Path,
) -> None:
    _, runtime = _runtime(tmp_path)
    with pytest.raises(
        P0RuntimeCompositionError,
        match="without a governed adapter",
    ):
        compose_p0_runtime(
            runtime,
            GrantPolicy(),
            engineering_skills_root=default_skills_root(ROOT),
            ai_provider_capabilities={
                "provider-a": frozenset({"workflow.plan"})
            },
        )


def test_ai_provider_cannot_claim_independent_verification_authority(
    tmp_path: Path,
) -> None:
    _, runtime = _runtime(tmp_path)
    with pytest.raises(
        P0RuntimeCompositionError,
        match="exceeds canonical governed execution",
    ):
        compose_p0_runtime(
            runtime,
            GrantPolicy(),
            engineering_skills_root=default_skills_root(ROOT),
            ai_adapter=object(),  # type: ignore[arg-type]
            ai_provider_capabilities={
                "provider-a": frozenset({"evidence.verify"})
            },
        )
