"""Executable SF-4 governance lineage and bypass tests."""

from __future__ import annotations

import subprocess
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from services.cloud import DeploymentProfile, TenantBoundary, TenantPolicy
from services.governance.gates import (
    FinancialLedger,
    HumanApprovalStore,
    PricingRegistry,
    SecurityFinanceGate,
)
from services.identity import (
    AccessRequest,
    AuthorizationEngine,
    AuthorizationRule,
    IdentityKind,
    Principal,
)
from services.runtime.grants import BlastRadiusBudget, ExecutionGrant, GrantPolicy
from services.software_factory import (
    Change,
    ChangeOperation,
    ChangeSet,
    ExecutionPolicy,
    FactoryGovernanceContext,
    GovernedSoftwareFactory,
    RepositoryRef,
    SoftwareFactory,
    SoftwareFactoryError,
    SoftwareFactoryRequest,
)
from src.core.audit_engine import AuditEngine
from src.core.evidence_chain import EvidenceChain


class _Policy:
    def __init__(self, allowed: bool = True) -> None:
        self.allowed = allowed

    def permits(self, principal: Principal, request: SoftwareFactoryRequest) -> bool:
        return self.allowed


def _request(tmp_path: Path, request_id: str = "sf-governed") -> SoftwareFactoryRequest:
    repository = tmp_path / "repository"
    (repository / "src").mkdir(parents=True)
    (repository / "src" / "base.py").write_text("value = 1\n", encoding="utf-8")
    subprocess.run(("git", "init", "-q"), cwd=repository, check=True)
    subprocess.run(("git", "config", "user.email", "factory@example.invalid"), cwd=repository, check=True)
    subprocess.run(("git", "config", "user.name", "Factory Test"), cwd=repository, check=True)
    subprocess.run(("git", "add", "."), cwd=repository, check=True)
    subprocess.run(("git", "commit", "-qm", "base"), cwd=repository, check=True)
    sha = subprocess.run(("git", "rev-parse", "HEAD"), cwd=repository, check=True,
                         capture_output=True, text=True).stdout.strip()
    return SoftwareFactoryRequest(
        request_id,
        RepositoryRef(repository.resolve(), sha),
        ExecutionPolicy(frozenset({"src"})),
        ChangeSet((Change(ChangeOperation.CREATE, "src/new.py", b"created = True\n"),)),
    )


def _lineage(tmp_path: Path, request: SoftwareFactoryRequest, *, policy: _Policy | None = None,
             roles: frozenset[str] = frozenset({"engineer"}), quota: int = 5,
             side_effects: int = 2) -> tuple[
                 GovernedSoftwareFactory, FactoryGovernanceContext, AuditEngine, EvidenceChain
             ]:
    now = datetime(2026, 8, 14, tzinfo=timezone.utc)
    principal = Principal("actor-1", "tenant-1", IdentityKind.HUMAN, roles, frozenset(), frozenset({"mfa"}))
    access = AccessRequest("tenant-1", "tenant-1", "software-factory.execute")
    grant = ExecutionGrant("grant-1", "actor-1", frozenset({"software-factory.execute"}),
                           frozenset({request.request_id}), now + timedelta(minutes=5),
                           BlastRadiusBudget(side_effects, 1))
    tenants = TenantBoundary()
    tenants.register(TenantPolicy("tenant-1", "eu", DeploymentProfile.SHARED, quota, "billing-1"))
    authorization = AuthorizationEngine((AuthorizationRule("software-factory.execute", frozenset({"engineer"})),))
    approvals = HumanApprovalStore(tmp_path / "governance.sqlite3")
    finance = SecurityFinanceGate(approvals, PricingRegistry({}), FinancialLedger(tmp_path / "governance.sqlite3", hard_cap_minor=0))
    audit, evidence = AuditEngine(), EvidenceChain()
    gateway = GovernedSoftwareFactory(
        SoftwareFactory(tmp_path / "workspaces", tmp_path / "proposals"), tenants,
        authorization, policy or _Policy(), finance, GrantPolicy(), audit, evidence,
    )
    context = FactoryGovernanceContext(principal, access, grant, "eu", "low", now)
    return gateway, context, audit, evidence


def test_governed_factory_executes_only_after_all_canonical_gates(tmp_path: Path) -> None:
    request = _request(tmp_path)
    gateway, context, audit, evidence = _lineage(tmp_path, request)
    job = gateway.submit(request, context)
    assert job.request_id == request.request_id
    latest = audit.get_latest()
    assert latest is not None and latest.status == "success"
    assert evidence.verify_integrity() and len(evidence.get_records()) == 1


def test_missing_actor_unauthorized_actor_and_missing_tenant_are_denied(tmp_path: Path) -> None:
    request = _request(tmp_path)
    gateway, context, _, _ = _lineage(tmp_path, request)
    with pytest.raises(SoftwareFactoryError, match="resolved actor"):
        gateway.submit(request, replace(context, principal=replace(context.principal, principal_id="")))
    gateway, context, _, _ = _lineage(tmp_path, request, roles=frozenset({"viewer"}))
    with pytest.raises(PermissionError, match="deny by default"):
        gateway.submit(request, context)
    gateway, context, _, _ = _lineage(tmp_path / "tenant", _request(tmp_path / "tenant"), quota=1)
    with pytest.raises(PermissionError, match="unknown or blocked tenant"):
        gateway.submit(request, replace(context, principal=replace(context.principal, tenant_id="missing")))


def test_denied_policy_invalid_risk_and_exceeded_resource_budget_block(tmp_path: Path) -> None:
    request = _request(tmp_path)
    gateway, context, _, _ = _lineage(tmp_path, request, policy=_Policy(False))
    with pytest.raises(SoftwareFactoryError, match="policy denied"):
        gateway.submit(request, context)
    risk_request = _request(tmp_path / "risk")
    gateway, context, _, _ = _lineage(tmp_path / "risk", risk_request)
    with pytest.raises(PermissionError, match="unknown risk"):
        gateway.submit(risk_request, replace(context, risk="forged-pass"))
    budget_request = _request(tmp_path / "budget")
    gateway, context, _, _ = _lineage(tmp_path / "budget", budget_request, side_effects=0)
    with pytest.raises(PermissionError, match="side-effect budget exhausted"):
        gateway.submit(budget_request, context)


def test_direct_factory_execution_bypass_is_blocked(tmp_path: Path) -> None:
    request = _request(tmp_path)
    with pytest.raises(SoftwareFactoryError, match="bypass is forbidden"):
        SoftwareFactory(tmp_path / "workspaces", tmp_path / "proposals").submit(request)
