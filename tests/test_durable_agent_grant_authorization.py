"""Durable grant compatibility with the canonical agent PermissionFirewall."""

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from services.agent_governance import AgentInvocation, AgentSecurityError, PermissionFirewall
from services.agent_registry import ORCHESTRATOR_ID, registration_for
from services.control_plane.migrations import migrate_database
from services.runtime import BlastRadiusBudget, DurableGrantPolicy, ExecutionGrant
from services.runtime.grants import GrantError

NOW = datetime(2026, 8, 18, 12, 0, tzinfo=timezone.utc)
PLANNER_ID = "ilaios.agent.core.planner.v1"


def _policy(tmp_path: Path) -> DurableGrantPolicy:
    database = tmp_path / "state.sqlite3"
    migrate_database(database)
    return DurableGrantPolicy(database)


def _grant() -> ExecutionGrant:
    return ExecutionGrant(
        "grant-planner",
        PLANNER_ID,
        frozenset({"workflow.read"}),
        frozenset({PLANNER_ID}),
        NOW + timedelta(minutes=5),
        BlastRadiusBudget(2, 1),
    )


def _invocation() -> AgentInvocation:
    return AgentInvocation(
        "invoke-planner",
        ORCHESTRATOR_ID,
        PLANNER_ID,
        "workflow.plan",
        "workflow.read",
        "governed_task",
        "proposal",
        "Plan the bounded authorized task.",
        security_scan_passed=True,
    )


def test_durable_grant_reconstructs_exact_persisted_contract(tmp_path: Path) -> None:
    policy = _policy(tmp_path)
    grant = _grant()
    policy.register(grant)
    loaded = policy.get(grant.grant_id)
    assert loaded == grant


def test_permission_firewall_uses_durable_authority_and_consumes_budget(tmp_path: Path) -> None:
    policy = _policy(tmp_path)
    grant = _grant()
    policy.register(grant)
    manifest = registration_for(PLANNER_ID).manifest
    firewall = PermissionFirewall((manifest,), policy)

    first = firewall.admit(_invocation(), policy.get(grant.grant_id), NOW)
    second = firewall.admit(_invocation(), policy.get(grant.grant_id), NOW)
    assert first.agent_id == second.agent_id == PLANNER_ID
    with pytest.raises(AgentSecurityError, match="grant denied"):
        firewall.admit(_invocation(), policy.get(grant.grant_id), NOW)


def test_durable_authorize_ignores_forged_in_memory_scope_and_rechecks_database(tmp_path: Path) -> None:
    policy = _policy(tmp_path)
    persisted = _grant()
    policy.register(persisted)
    forged = ExecutionGrant(
        persisted.grant_id,
        "ilaios.agent.engineering.core.v1",
        frozenset({"repository.read"}),
        frozenset({"ilaios.agent.engineering.core.v1"}),
        NOW + timedelta(hours=1),
        BlastRadiusBudget(99, 99),
    )
    with pytest.raises(GrantError, match="subject mismatch"):
        policy.authorize(
            forged,
            subject_id="ilaios.agent.engineering.core.v1",
            action="repository.read",
            resource="ilaios.agent.engineering.core.v1",
            now=NOW,
        )
