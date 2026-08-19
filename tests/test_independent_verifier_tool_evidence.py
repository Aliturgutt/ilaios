from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from services.agent_registry import INDEPENDENT_VERIFIER_ID
from services.ai_governance import Scope, ScopeKind
from services.control_plane.migrations import migrate_database
from services.independent_verifier_execution import (
    INDEPENDENT_VERIFIER_PROVIDER_ID,
    IndependentVerifierExecutionError,
    IndependentVerifierExecutor,
)
from services.p0_runtime_composition import compose_p0_runtime
from services.runtime import BlastRadiusBudget, ExecutionGrant, GovernedRuntime, GrantPolicy
from services.runtime.browser_tool_adapter import BROWSER_AGENT_ID, BROWSER_TOOL_NAME
from services.runtime.security_agent_adapters import SecurityAgentRuntimeAdapters


def _grant(now: datetime) -> ExecutionGrant:
    return ExecutionGrant(
        grant_id="tool-evidence-verifier-grant",
        subject_id=INDEPENDENT_VERIFIER_ID,
        actions=frozenset({"evidence.read"}),
        resources=frozenset({INDEPENDENT_VERIFIER_ID}),
        expires_at=now + timedelta(minutes=5),
        budget=BlastRadiusBudget(max_side_effects=1, max_resources=1),
    )


def _executor(tmp_path: Path) -> IndependentVerifierExecutor:
    database = tmp_path / "runtime.sqlite3"
    migrate_database(database)
    runtime = GovernedRuntime(
        database,
        external_adapters=SecurityAgentRuntimeAdapters().runtime_adapters(),
    )
    composition = compose_p0_runtime(
        runtime,
        GrantPolicy(),
        engineering_skills_root=Path.cwd() / "tools" / "software-factory" / "skills",
    )
    return IndependentVerifierExecutor(composition.named_executor)


def test_attests_exact_governed_browser_tool_evidence(tmp_path: Path) -> None:
    now = datetime(2026, 8, 19, tzinfo=timezone.utc)
    verifier = _executor(tmp_path)
    result = verifier.verify_governed_tool_evidence(
        producer_agent_id=BROWSER_AGENT_ID,
        evidence_digest="a" * 64,
        binding_digest="b" * 64,
        tool_name=BROWSER_TOOL_NAME,
        grant=_grant(now),
        tenant_id="tenant-web-cert",
        scopes=(Scope(ScopeKind.TENANT, "tenant-web-cert"),),
        now=now,
    )
    assert result.passed is True
    assert result.producer_agent_id == BROWSER_AGENT_ID
    assert result.producer_evidence_digest == "a" * 64
    assert result.provider_id == INDEPENDENT_VERIFIER_PROVIDER_ID


def test_rejects_malformed_tool_evidence_digest(tmp_path: Path) -> None:
    now = datetime(2026, 8, 19, tzinfo=timezone.utc)
    verifier = _executor(tmp_path)
    with pytest.raises(IndependentVerifierExecutionError, match="governed tool evidence digest"):
        verifier.verify_governed_tool_evidence(
            producer_agent_id=BROWSER_AGENT_ID,
            evidence_digest="not-a-digest",
            binding_digest="b" * 64,
            tool_name=BROWSER_TOOL_NAME,
            grant=_grant(now),
            tenant_id="tenant-web-cert",
            scopes=(Scope(ScopeKind.TENANT, "tenant-web-cert"),),
            now=now,
        )


def test_independent_verifier_cannot_attest_itself(tmp_path: Path) -> None:
    now = datetime(2026, 8, 19, tzinfo=timezone.utc)
    verifier = _executor(tmp_path)
    with pytest.raises(IndependentVerifierExecutionError, match="cannot verify itself"):
        verifier.verify_governed_tool_evidence(
            producer_agent_id=INDEPENDENT_VERIFIER_ID,
            evidence_digest="a" * 64,
            binding_digest="b" * 64,
            tool_name=BROWSER_TOOL_NAME,
            grant=_grant(now),
            tenant_id="tenant-web-cert",
            scopes=(Scope(ScopeKind.TENANT, "tenant-web-cert"),),
            now=now,
        )
