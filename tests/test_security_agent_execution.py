"""P0 Security named-agent execution through defensive local providers."""

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from services.agent_governance import AgentInvocation
from services.agent_registry import ORCHESTRATOR_ID, SECURITY_VERIFIER_ID
from services.control_plane.migrations import migrate_database
from services.named_agent_executor import NamedAgentExecutor
from services.runtime import BlastRadiusBudget, ExecutionGrant, GovernedRuntime, GrantPolicy
from services.runtime.security_agent_adapters import (
    SecurityAgentAdapterError,
    SecurityAgentRuntimeAdapters,
)
from services.security_agent_execution import (
    DefensiveSecurityAgentExecutor,
    security_local_provider_specs,
)

NOW = datetime(2026, 8, 18, 10, 0, tzinfo=timezone.utc)
CODESEC_ID = "ilaios.agent.security.codesec.v1"
WEB_API_ID = "ilaios.agent.security.web-api.v1"


def _grant(agent_id: str, permission: str) -> ExecutionGrant:
    return ExecutionGrant(
        f"grant-{agent_id}",
        agent_id,
        frozenset({permission}),
        frozenset({agent_id}),
        NOW + timedelta(minutes=5),
        BlastRadiusBudget(1, 1),
    )


def _invocation(agent_id: str, capability: str, permission: str) -> AgentInvocation:
    return AgentInvocation(
        f"invoke-{agent_id}",
        ORCHESTRATOR_ID,
        agent_id,
        capability,
        permission,
        "governed_task",
        "proposal",
        "Analyze only the explicitly authorized defensive scope.",
        security_scan_passed=True,
    )


def _executor(tmp_path: Path) -> tuple[DefensiveSecurityAgentExecutor, NamedAgentExecutor]:
    database = tmp_path / "security-runtime.sqlite3"
    migrate_database(database)
    adapters = SecurityAgentRuntimeAdapters()
    runtime = GovernedRuntime(database, external_adapters=adapters.runtime_adapters())
    named = NamedAgentExecutor(runtime, GrantPolicy())
    for agent_id in (CODESEC_ID, WEB_API_ID, SECURITY_VERIFIER_ID):
        named.provision_agent(agent_id)
    named.provision_skill(
        "ilaios.skill.security.sast.v1",
        b"first-party deterministic repository security analysis",
        frozenset({"security.sast"}),
    )
    named.provision_skill(
        "ilaios.skill.security.web-api.v1",
        b"first-party non-destructive local observation analysis",
        frozenset({"security.web-api"}),
    )
    named.provision_skill(
        "ilaios.skill.security.verify.v1",
        b"first-party independent security report verification",
        frozenset({"security.verify"}),
    )
    for provider_id, adapter_kind, capability in security_local_provider_specs():
        named.provision_provider(
            provider_id,
            frozenset({capability}),
            adapter_kind=adapter_kind,
            deterministic=True,
        )
    return DefensiveSecurityAgentExecutor(named), named


def test_codesec_report_is_persisted_then_verified_by_distinct_security_verifier(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repo"
    repository.mkdir()
    (repository / "safe.py").write_text("value = 1\n", encoding="utf-8")
    executor, named = _executor(tmp_path)

    producer = executor.execute_specialist(
        _invocation(CODESEC_ID, "security.sast", "repository.read"),
        _grant(CODESEC_ID, "repository.read"),
        skill_id="ilaios.skill.security.sast.v1",
        payload={"scope_id": "repo-scope", "repository_root": str(repository)},
        now=NOW,
    )
    assert producer.route["provider_id"] == "ilaios.security.local.codesec"
    assert producer.route["deterministic_first"] is True
    assert producer.route["output"]["passed"] is True
    assert producer.route["output"]["finding_count"] == 0
    assert producer.verifier_id == SECURITY_VERIFIER_ID

    verifier_invocation = _invocation(
        SECURITY_VERIFIER_ID,
        "security.verify",
        "evidence.read",
    )
    verified = executor.independently_verify(
        producer,
        verifier_invocation,
        _grant(SECURITY_VERIFIER_ID, "evidence.read"),
        skill_id="ilaios.skill.security.verify.v1",
        now=NOW,
    )
    assert verified.passed is True
    assert verified.producer.admission.agent_id == CODESEC_ID
    assert verified.verifier.admission.agent_id == SECURITY_VERIFIER_ID
    assert len(verified.producer_evidence_digest) == 64
    assert len(verified.verifier_evidence_digest) == 64
    assert [route["agent_id"] for route in named.routes()] == [
        CODESEC_ID,
        SECURITY_VERIFIER_ID,
    ]


def test_codesec_blocking_finding_is_not_promoted_by_verifier(tmp_path: Path) -> None:
    repository = tmp_path / "repo-blocking"
    repository.mkdir()
    (repository / "unsafe.py").write_text("result = eval(user_input)\n", encoding="utf-8")
    executor, _ = _executor(tmp_path)
    producer = executor.execute_specialist(
        _invocation(CODESEC_ID, "security.sast", "repository.read"),
        _grant(CODESEC_ID, "repository.read"),
        skill_id="ilaios.skill.security.sast.v1",
        payload={"scope_id": "unsafe-scope", "repository_root": str(repository)},
        now=NOW,
    )
    assert producer.route["output"]["passed"] is False
    assert producer.route["output"]["blocking_finding_count"] >= 1

    verified = executor.independently_verify(
        producer,
        _invocation(SECURITY_VERIFIER_ID, "security.verify", "evidence.read"),
        _grant(SECURITY_VERIFIER_ID, "evidence.read"),
        skill_id="ilaios.skill.security.verify.v1",
        now=NOW,
    )
    assert verified.passed is False


def test_web_api_agent_cannot_turn_observation_analysis_into_external_scan(tmp_path: Path) -> None:
    repository = tmp_path / "repo-web"
    repository.mkdir()
    executor, named = _executor(tmp_path)
    with pytest.raises(SecurityAgentAdapterError, match="outside defensive scope"):
        executor.execute_specialist(
            _invocation(WEB_API_ID, "security.web-api", "authorized-target.read"),
            _grant(WEB_API_ID, "authorized-target.read"),
            skill_id="ilaios.skill.security.web-api.v1",
            payload={
                "scope_id": "web-scope",
                "repository_root": str(repository),
                "target_url": "https://example.com/private",
                "status_code": 200,
                "headers": {},
            },
            now=NOW,
        )
    assert named.routes() == ()
