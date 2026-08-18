"""Canonical runtime proofs for explicitly admitted Skill Engineering packages."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from services.agent_governance import AgentInvocation
from services.control_plane.migrations import migrate_database
from services.named_agent_executor import NamedAgentExecutor
from services.runtime import BlastRadiusBudget, ExecutionGrant, GovernedRuntime, GrantPolicy
from services.skill_engineering_catalog import default_skill_engineering_root
from services.skill_engineering_runtime import (
    SKILL_ENGINEERING_RUNTIME_BINDINGS,
    SkillEngineeringRuntimeError,
    ensure_skill_engineering_runtime_skills,
    runtime_binding_for,
)
from services.skill_taxonomy import resolve_logical_skill

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_RUNTIME_SKILLS = {
    "skill-create",
    "skill-validate",
    "skill-evaluate",
    "skill-benchmark",
    "skill-regression",
}


def test_core_skill_engineering_runtime_bindings_match_canonical_taxonomy() -> None:
    assert {binding.skill_id for binding in SKILL_ENGINEERING_RUNTIME_BINDINGS} == (
        EXPECTED_RUNTIME_SKILLS
    )
    for binding in SKILL_ENGINEERING_RUNTIME_BINDINGS:
        assert resolve_logical_skill(binding.logical_id).backing_skill_ids == (
            binding.skill_id,
        )


def test_core_skill_engineering_packages_execute_through_canonical_runtime(
    tmp_path: Path,
) -> None:
    database = tmp_path / "runtime.sqlite3"
    migrate_database(database)

    def adapter(payload: dict[str, object]) -> dict[str, object]:
        skill = payload.get("_ilaios_skill")
        assert isinstance(skill, dict)
        return {
            "accepted": True,
            "skill_id": skill["skill_id"],
            "instruction_digest": skill["sha256"],
        }

    runtime = GovernedRuntime(
        database,
        external_adapters={"skill-engineering-test": adapter},
    )
    grants = GrantPolicy()
    executor = NamedAgentExecutor(runtime, grants)
    for binding in SKILL_ENGINEERING_RUNTIME_BINDINGS:
        executor.ensure_agent(binding.owner_agent_id)

    digests = ensure_skill_engineering_runtime_skills(
        executor,
        default_skill_engineering_root(ROOT),
    )
    assert set(digests) == EXPECTED_RUNTIME_SKILLS

    provider_capabilities = frozenset(
        binding.capability for binding in SKILL_ENGINEERING_RUNTIME_BINDINGS
    )
    executor.ensure_provider(
        "provider.skill-engineering.test",
        provider_capabilities,
        adapter_kind="skill-engineering-test",
        deterministic=False,
    )

    now = datetime.now(timezone.utc)
    for index, binding in enumerate(SKILL_ENGINEERING_RUNTIME_BINDINGS, start=1):
        invocation = AgentInvocation(
            invocation_id=f"skill-engineering-runtime-test-{index}",
            caller_id="ilaios.agent.core.orchestrator.v1",
            target_id=binding.owner_agent_id,
            capability=binding.capability,
            permission=binding.permission,
            input_class="governed_task",
            requested_output_class="proposal",
            prompt=f"Execute bounded {binding.logical_id} verification only.",
            contains_secret=False,
            external_egress=True,
            dlp_approved=True,
            security_scan_passed=True,
        )
        grant = ExecutionGrant(
            grant_id=f"skill-engineering-runtime-test-grant-{index}",
            subject_id=binding.owner_agent_id,
            actions=frozenset({binding.permission}),
            resources=frozenset({binding.owner_agent_id}),
            expires_at=now + timedelta(minutes=5),
            budget=BlastRadiusBudget(max_side_effects=1, max_resources=1),
        )
        result = executor.execute(
            invocation,
            grant,
            skill_id=binding.skill_id,
            payload={"task": f"bounded {binding.skill_id} test"},
            now=now,
            preferred_provider_id="provider.skill-engineering.test",
        )
        assert result.route["skill_id"] == binding.skill_id
        assert result.route["agent_id"] == binding.owner_agent_id
        assert result.route["capability"] == binding.capability
        assert result.route["provider_id"] == "provider.skill-engineering.test"
        assert result.route["output"]["accepted"] is True
        assert result.route["output"]["skill_id"] == binding.skill_id
        assert result.route["output"]["instruction_digest"] == digests[binding.skill_id]


def test_unmapped_skill_engineering_nodes_have_no_runtime_authority() -> None:
    for skill_id in (
        "skill-lint",
        "skill-security-scan",
        "skill-compatibility",
        "skill-promote",
    ):
        with pytest.raises(
            SkillEngineeringRuntimeError,
            match="has no runtime admission",
        ):
            runtime_binding_for(skill_id)
