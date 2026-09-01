"""Bounded end-to-end proof for canonical ILAIOS named-agent execution."""

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from services.agent_governance import AgentInvocation, AgentSecurityError
from services.agent_registry import (
    ORCHESTRATOR_ID,
    SECURITY_VERIFIER_ID,
    registration_for,
)
from services.control_plane.migrations import migrate_database
from services.named_agent_executor import NamedAgentExecutor
from services.runtime import BlastRadiusBudget, ExecutionGrant, GovernedRuntime, GrantPolicy

NOW = datetime(2026, 8, 12, tzinfo=timezone.utc)
CODESEC_ID = "ilaios.agent.security.codesec.v1"


def _grant(agent_id: str, permission: str) -> ExecutionGrant:
    return ExecutionGrant(
        f"grant-{agent_id}",
        agent_id,
        frozenset({permission}),
        frozenset({agent_id}),
        NOW + timedelta(minutes=5),
        BlastRadiusBudget(1, 1),
    )


def _invocation(
    *, agent_id: str, capability: str, permission: str, prompt: str
) -> AgentInvocation:
    return AgentInvocation(
        f"invoke-{agent_id}",
        ORCHESTRATOR_ID,
        agent_id,
        capability,
        permission,
        "governed_task",
        "proposal",
        prompt,
        security_scan_passed=True,
    )


def _executor(tmp_path: Path) -> NamedAgentExecutor:
    database = tmp_path / "runtime.sqlite3"
    migrate_database(database)
    grants = GrantPolicy()
    executor = NamedAgentExecutor(GovernedRuntime(database), grants)
    executor.provision_agent(CODESEC_ID)
    executor.provision_agent(SECURITY_VERIFIER_ID)
    executor.provision_skill(
        "ilaios.skill.security.sast-proof.v1",
        b"bounded deterministic security-analysis proof",
        frozenset({"security.sast"}),
    )
    executor.provision_skill(
        "ilaios.skill.security.verify-proof.v1",
        b"bounded deterministic independent-verification proof",
        frozenset({"security.verify"}),
    )
    executor.provision_provider(
        "local-deterministic-proof",
        frozenset({"security.sast", "security.verify"}),
        adapter_kind="canonical-json-sha256",
    )
    return executor


def test_named_security_agent_executes_then_independent_verifier_executes(
    tmp_path: Path,
) -> None:
    executor = _executor(tmp_path)

    producer = executor.execute(
        _invocation(
            agent_id=CODESEC_ID,
            capability="security.sast",
            permission="repository.read",
            prompt="Analyze the bounded authorized repository evidence.",
        ),
        _grant(CODESEC_ID, "repository.read"),
        skill_id="ilaios.skill.security.sast-proof.v1",
        payload={"repository": "authorized-fixture", "finding_count": 0},
        now=NOW,
    )

    assert producer.route["agent_id"] == CODESEC_ID
    assert producer.route["deterministic_first"] is True
    assert producer.verifier_id == SECURITY_VERIFIER_ID
    assert producer.verifier_id != producer.route["agent_id"]

    verifier = executor.execute(
        _invocation(
            agent_id=SECURITY_VERIFIER_ID,
            capability="security.verify",
            permission="evidence.read",
            prompt="Independently verify the producer route evidence.",
        ),
        _grant(SECURITY_VERIFIER_ID, "evidence.read"),
        skill_id="ilaios.skill.security.verify-proof.v1",
        payload={
            "producer_agent_id": producer.route["agent_id"],
            "producer_sequence": producer.route["sequence"],
            "producer_output": producer.route["output"],
        },
        now=NOW,
    )

    assert verifier.route["agent_id"] == SECURITY_VERIFIER_ID
    assert verifier.route["sequence"] == 2
    assert verifier.verifier_id != verifier.route["agent_id"]
    assert [route["agent_id"] for route in executor.routes()] == [
        CODESEC_ID,
        SECURITY_VERIFIER_ID,
    ]


def test_alias_or_unscanned_invocation_never_reaches_runtime(tmp_path: Path) -> None:
    executor = _executor(tmp_path)
    manifest = registration_for(CODESEC_ID).manifest

    alias_invocation = AgentInvocation(
        "invoke-alias",
        ORCHESTRATOR_ID,
        manifest.alias,
        "security.sast",
        "repository.read",
        "governed_task",
        "proposal",
        "Analyze bounded evidence.",
        security_scan_passed=True,
    )
    with pytest.raises(AgentSecurityError, match="target agent"):
        executor.execute(
            alias_invocation,
            _grant(CODESEC_ID, "repository.read"),
            skill_id="ilaios.skill.security.sast-proof.v1",
            payload={"repository": "authorized-fixture"},
            now=NOW,
        )

    unscanned = AgentInvocation(
        "invoke-unscanned",
        ORCHESTRATOR_ID,
        CODESEC_ID,
        "security.sast",
        "repository.read",
        "governed_task",
        "proposal",
        "Analyze bounded evidence.",
        security_scan_passed=False,
    )
    with pytest.raises(AgentSecurityError, match="security scan"):
        executor.execute(
            unscanned,
            _grant(CODESEC_ID, "repository.read"),
            skill_id="ilaios.skill.security.sast-proof.v1",
            payload={"repository": "authorized-fixture"},
            now=NOW,
        )

    assert executor.routes() == ()
