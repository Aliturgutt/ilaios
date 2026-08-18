"""End-to-end governance tests for external Agent Skills runtime activation."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from services.agent_skills_compat import load_agent_skill
from services.agent_skills_runtime import (
    AgentSkillsProductionRuntime,
    AgentSkillsRuntimeError,
    ExternalSkillExecutionRequest,
)
from services.cloud import DeploymentProfile, TenantBoundary, TenantPolicy
from services.governance.runtime import GovernedRuntimeGateway
from services.identity import (
    AuthorizationEngine,
    AuthorizationRule,
    IdentityKind,
    Principal,
)
from services.runtime import GovernedRuntime
from src.core.evidence_chain import EvidenceChain
from src.core.immutable_context import ExecutionContext
from src.core.tool_gateway import ToolGateway


CAPABILITY = "text.transform"
AGENT_ID = "ilaios.agent.external-skill-test.v1"
PROVIDER_ID = "test.external-provider"
ADAPTER_KIND = "test-external-agent-skills"


def _runtime_database(path: Path) -> None:
    with sqlite3.connect(path) as connection:
        connection.executescript(
            """
            CREATE TABLE runtime_agents (
                agent_id TEXT PRIMARY KEY,
                authorities_json TEXT NOT NULL
            );
            CREATE TABLE runtime_skills (
                skill_id TEXT PRIMARY KEY,
                digest TEXT NOT NULL,
                authorities_json TEXT NOT NULL,
                content BLOB NOT NULL
            );
            CREATE TABLE runtime_providers (
                provider_id TEXT PRIMARY KEY,
                capabilities_json TEXT NOT NULL,
                deterministic INTEGER NOT NULL,
                enabled INTEGER NOT NULL,
                adapter_kind TEXT NOT NULL
            );
            CREATE TABLE runtime_routes (
                sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT NOT NULL,
                skill_id TEXT NOT NULL,
                provider_id TEXT NOT NULL,
                capability TEXT NOT NULL,
                input_sha256 TEXT NOT NULL,
                output_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            """
        )


def _package(tmp_path: Path, *, with_script: bool = False) -> Path:
    root = tmp_path / "portable-transform"
    root.mkdir()
    (root / "SKILL.md").write_text(
        """---
name: portable-transform
description: Transforms bounded text when explicitly selected for governed execution.
allowed-tools: Bash(echo:*)
---
Return an uppercase transformation of the supplied text.
""",
        encoding="utf-8",
    )
    if with_script:
        scripts = root / "scripts"
        scripts.mkdir()
        (scripts / "danger.sh").write_text("echo should-not-run\n", encoding="utf-8")
    return root


def _configured(
    tmp_path: Path,
) -> tuple[AgentSkillsProductionRuntime, GovernedRuntimeGateway, EvidenceChain]:
    database = tmp_path / "runtime.sqlite3"
    _runtime_database(database)

    observed_skill: list[dict[str, object]] = []

    def external_adapter(payload: dict[str, object]) -> dict[str, object]:
        skill = payload.get("_ilaios_skill")
        assert isinstance(skill, dict)
        observed_skill.append(skill)
        skill_sha256 = skill.get("sha256")
        assert isinstance(skill_sha256, str)
        text = payload.get("text")
        assert isinstance(text, str)
        return {
            "text": text.upper(),
            "skill_sha256": skill_sha256,
            "script_executed": False,
        }

    runtime = GovernedRuntime(
        database, external_adapters={ADAPTER_KIND: external_adapter}
    )
    runtime.register_agent(AGENT_ID, frozenset({CAPABILITY}))
    runtime.register_provider(
        PROVIDER_ID,
        frozenset({CAPABILITY}),
        adapter_kind=ADAPTER_KIND,
        deterministic=False,
    )
    governed = GovernedRuntimeGateway(database, runtime, hard_cap_minor=1_000)

    tenants = TenantBoundary()
    tenants.register(
        TenantPolicy(
            tenant_id="tenant-a",
            region="eu-west",
            profile=DeploymentProfile.SHARED,
            request_quota=20,
            billing_account="acct-a",
        )
    )
    authorization = AuthorizationEngine(
        (
            AuthorizationRule(
                action="skill.execute.external",
                roles=frozenset({"operator"}),
            ),
        )
    )
    principal = Principal(
        principal_id="user-a",
        tenant_id="tenant-a",
        kind=IdentityKind.HUMAN,
        roles=frozenset({"operator"}),
        attributes=frozenset(),
        authentication_methods=frozenset({"mfa"}),
    )
    assert principal.tenant_id == "tenant-a"

    validator = MagicMock()
    tool_gateway = ToolGateway(
        ExecutionContext(
            tmp_path,
            "test",
            "deadbeef",
            "https://github.com/Aliturgutt/ilaios.git",
        ),
        validator,
    )
    evidence = EvidenceChain()
    bridge = AgentSkillsProductionRuntime(
        runtime=runtime,
        governed_gateway=governed,
        tool_gateway=tool_gateway,
        authorization=authorization,
        tenants=tenants,
        evidence_chain=evidence,
    )
    return bridge, governed, evidence


def _request(
    tmp_path: Path,
    package_root: Path,
    *,
    risk: str = "low",
    tenant: str = "tenant-a",
) -> ExternalSkillExecutionRequest:
    package = load_agent_skill(package_root)
    return ExternalSkillExecutionRequest(
        request_id=f"req-{risk}-{tenant}",
        principal=Principal(
            principal_id="user-a",
            tenant_id=tenant,
            kind=IdentityKind.HUMAN,
            roles=frozenset({"operator"}),
            attributes=frozenset(),
            authentication_methods=frozenset({"mfa"}),
        ),
        resource_tenant_id=tenant,
        region="eu-west",
        package_root=package_root,
        expected_package_sha256=package.package_sha256,
        agent_id=AGENT_ID,
        capability=CAPABILITY,
        payload={"text": "governed"},
        risk=risk,
    )


def test_external_skill_executes_through_governed_runtime_and_evidence_chain(
    tmp_path: Path,
) -> None:
    package_root = _package(tmp_path)
    bridge, governed, evidence = _configured(tmp_path)
    request = _request(tmp_path, package_root)

    admission = bridge.submit(request, now=datetime.now(timezone.utc))
    assert admission["status"] == "admitted"
    assert admission["script_execution_authorized"] is False

    receipt = bridge.execute(request)
    assert receipt.tenant_id == "tenant-a"
    assert receipt.provider_id == PROVIDER_ID
    assert receipt.admission_proven is True
    assert receipt.approval_proven is False
    assert receipt.output["text"] == "GOVERNED"
    assert receipt.output["script_executed"] is False
    state = governed.state()
    work = state["work"]
    assert isinstance(work, list)
    assert work[0]["status"] == "executed"
    assert len(evidence.get_records()) == 1
    assert evidence.verify_integrity() is True
    assert receipt.evidence_chain_hash == evidence.get_records()[0].chain_hash


def test_high_risk_external_skill_requires_independent_durable_approval(
    tmp_path: Path,
) -> None:
    package_root = _package(tmp_path)
    bridge, governed, _ = _configured(tmp_path)
    request = _request(tmp_path, package_root, risk="high")

    admission = bridge.submit(request, now=datetime.now(timezone.utc))
    assert admission["status"] == "pending_approval"
    with pytest.raises(PermissionError):
        bridge.execute(request)

    governed.decide(request.request_id, "approver-b", "approved")
    receipt = bridge.execute(request)
    assert receipt.admission_proven is True
    assert receipt.approval_proven is True


def test_cross_tenant_external_skill_execution_fails_closed(tmp_path: Path) -> None:
    package_root = _package(tmp_path)
    bridge, _, _ = _configured(tmp_path)
    package = load_agent_skill(package_root)
    request = ExternalSkillExecutionRequest(
        request_id="req-cross-tenant",
        principal=Principal(
            principal_id="user-a",
            tenant_id="tenant-a",
            kind=IdentityKind.HUMAN,
            roles=frozenset({"operator"}),
            attributes=frozenset(),
            authentication_methods=frozenset({"mfa"}),
        ),
        resource_tenant_id="tenant-b",
        region="eu-west",
        package_root=package_root,
        expected_package_sha256=package.package_sha256,
        agent_id=AGENT_ID,
        capability=CAPABILITY,
        payload={"text": "blocked"},
    )
    with pytest.raises(AgentSkillsRuntimeError, match="cross-tenant"):
        bridge.submit(request, now=datetime.now(timezone.utc))


def test_package_digest_drift_blocks_activation(tmp_path: Path) -> None:
    package_root = _package(tmp_path)
    bridge, _, _ = _configured(tmp_path)
    request = _request(tmp_path, package_root)
    (package_root / "SKILL.md").write_text(
        (package_root / "SKILL.md").read_text(encoding="utf-8") + "\nMutated.\n",
        encoding="utf-8",
    )
    with pytest.raises(AgentSkillsRuntimeError, match="digest changed"):
        bridge.submit(request, now=datetime.now(timezone.utc))


def test_bundled_script_is_never_authorized_or_executed_by_instruction_bridge(
    tmp_path: Path,
) -> None:
    package_root = _package(tmp_path, with_script=True)
    bridge, _, _ = _configured(tmp_path)
    request = _request(tmp_path, package_root)

    admission = bridge.submit(request, now=datetime.now(timezone.utc))
    assert admission["contains_scripts"] is True
    assert admission["script_execution_authorized"] is False
    receipt = bridge.execute(request)
    assert receipt.output["script_executed"] is False
