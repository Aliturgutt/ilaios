"""Tests for bounded Personal Operations review and governed mutation execution."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from services.evidence import EvidenceStore
from services.identity import (
    AccessRequest,
    ApprovalRecord,
    AuthorizationEngine,
    AuthorizationRule,
    IdentityKind,
    Principal,
)
from services.integrations.personal_operations import (
    ConnectorReceipt,
    register_personal_operations_connectors,
)
from services.personal_operations_factory import (
    ExternalExecutionContext,
    PersonalOperationsError,
    PersonalOperationsFactory,
)
from services.runtime.grants import BlastRadiusBudget, ExecutionGrant, GrantPolicy
from src.core.audit_engine import AuditEngine
from src.core.bootstrap_validator import BootstrapValidator
from src.core.immutable_context import ExecutionContext
from src.core.tool_gateway import ToolGateway


NOW = datetime(2026, 9, 8, 20, 0, tzinfo=timezone.utc)


def _steps() -> tuple[tuple[str, str, str, str], ...]:
    return (
        ("step-1", "checklist_draft", "project://ilaios", "Review release evidence"),
        ("step-2", "reminder_draft", "local://owner", "Check pending approval"),
    )


def _email_steps() -> tuple[tuple[str, str, str, str], ...]:
    return (("step-1", "send_email", "user@example.com", '{"subject":"Hello","body":"Body"}'),)


class _NoopBootstrapValidator(BootstrapValidator):
    def validate_git_identity(self) -> Path:
        return self.repo_path


class _MailConnector:
    def __init__(self, *, fail: bool = False) -> None:
        self.calls = 0
        self.fail = fail

    def send_email(
        self,
        *,
        target_account: str,
        recipient: str,
        subject: str,
        body: str,
        idempotency_key: str,
    ) -> ConnectorReceipt:
        del recipient, subject, body, idempotency_key
        self.calls += 1
        if self.fail:
            raise RuntimeError("provider unavailable")
        return ConnectorReceipt("gmail", "message-123", NOW, target_account, "success")


def _gateway(tmp_path: Path) -> ToolGateway:
    context = ExecutionContext(tmp_path, "test", "0" * 40, "https://example.invalid/repo.git")
    return ToolGateway(context, validator=_NoopBootstrapValidator(tmp_path))


def _principal(tenant: str = "tenant-a") -> Principal:
    return Principal(
        "user-1",
        tenant,
        IdentityKind.HUMAN,
        frozenset({"owner"}),
        frozenset(),
        frozenset({"mfa"}),
    )


def _authorization(*, expires_at: datetime | None = None, tenant: str = "tenant-a") -> AuthorizationEngine:
    approval = ApprovalRecord(
        "mutation-approval-1",
        tenant,
        "personal-operations.execute",
        "user-1",
        "approver-2",
        expires_at or NOW + timedelta(minutes=10),
    )
    return AuthorizationEngine(
        (AuthorizationRule("personal-operations.execute", frozenset({"owner"})),),
        (approval,),
    )


def _execution_context(
    *,
    tenant: str = "tenant-a",
    resource_tenant: str = "tenant-a",
    target_account: str = "account@example.com",
    grant_expires_at: datetime | None = None,
    approval_id: str | None = "mutation-approval-1",
) -> ExternalExecutionContext:
    principal = _principal(tenant)
    access = AccessRequest(
        tenant,
        resource_tenant,
        "personal-operations.execute",
        frozenset({("target_account", target_account)}),
        high_risk=True,
        approval_id=approval_id,
    )
    grant = ExecutionGrant(
        "grant-1",
        principal.principal_id,
        frozenset({"personal-operations.execute"}),
        frozenset({f"plan-1:{target_account}"}),
        grant_expires_at or NOW + timedelta(minutes=10),
        BlastRadiusBudget(max_side_effects=3, max_resources=1),
    )
    return ExternalExecutionContext(principal, access, grant, target_account, NOW)


def _approved_factory(tmp_path: Path) -> PersonalOperationsFactory:
    factory = PersonalOperationsFactory(tmp_path / "personal-operations.sqlite3")
    factory.propose("plan-1", objective="Send approved email", steps=_email_steps())
    factory.approve_for_review("plan-1", approver="reviewer-1")
    return factory


def test_plan_is_deterministic_and_review_projection_contains_hashed_payloads() -> None:
    first = PersonalOperationsFactory()
    first_plan = first.propose("plan-1", objective="Prepare bounded operational follow-up.", steps=_steps())
    approved = first.approve_for_review("plan-1", approver="human-owner")
    projection = first.review_projection("plan-1")

    second = PersonalOperationsFactory()
    second_plan = second.propose("plan-1", objective="Prepare bounded operational follow-up.", steps=_steps())

    assert first_plan.plan_sha256 == second_plan.plan_sha256
    assert approved.approved_for_review is True
    assert approved.external_applied is False
    assert projection["external_applied"] is False
    assert projection["steps"][0]["step_id"] == "step-1"
    assert len(projection["steps"][0]["payload_sha256"]) == 64


def test_unsupported_action_and_duplicate_step_ids_fail_closed() -> None:
    factory = PersonalOperationsFactory()
    with pytest.raises(PersonalOperationsError, match="unsupported personal operation action"):
        factory.propose(
            "unsafe-plan",
            objective="Unsafe external action",
            steps=(("step-1", "delete_account", "external://account", "delete now"),),
        )
    with pytest.raises(PersonalOperationsError, match="step_id must be unique"):
        factory.propose(
            "duplicate-plan",
            objective="Duplicate steps",
            steps=(("step-1", "note_draft", "local://notes", "one"), ("step-1", "note_draft", "local://notes", "two")),
        )


def test_review_approval_is_not_external_mutation_approval(tmp_path: Path) -> None:
    factory = _approved_factory(tmp_path)
    with pytest.raises(PersonalOperationsError, match="governed external execution dependencies"):
        factory.apply_external("plan-1")


def test_governed_send_email_uses_tool_gateway_and_persists_evidence(tmp_path: Path) -> None:
    factory = _approved_factory(tmp_path)
    connector = _MailConnector()
    gateway = _gateway(tmp_path)
    register_personal_operations_connectors(gateway, mail=connector)
    audit = AuditEngine()
    evidence = EvidenceStore(tmp_path / "evidence")
    grants = GrantPolicy()

    result = factory.apply_external(
        "plan-1",
        context=_execution_context(),
        gateway=gateway,
        authorization=_authorization(),
        grants=grants,
        audit=audit,
        evidence=evidence,
    )

    assert connector.calls == 1
    assert result.receipts[0].provider_id == "message-123"
    assert result.receipts[0].target_account == "account@example.com"
    assert evidence.verify()[0].action == "personal_operations.send_email"
    assert audit.get_records(component="personal_operations", action="send_email", status="success")
    assert factory.review_projection("plan-1")["external_applied"] is True


def test_duplicate_execution_is_idempotent_and_does_not_call_provider_twice(tmp_path: Path) -> None:
    factory = _approved_factory(tmp_path)
    connector = _MailConnector()
    gateway = _gateway(tmp_path)
    register_personal_operations_connectors(gateway, mail=connector)
    evidence = EvidenceStore(tmp_path / "evidence")

    for _ in range(2):
        factory.apply_external(
            "plan-1",
            context=_execution_context(),
            gateway=gateway,
            authorization=_authorization(),
            grants=GrantPolicy(),
            audit=AuditEngine(),
            evidence=evidence,
        )

    assert connector.calls == 1
    assert len(evidence.verify()) == 1


@pytest.mark.parametrize(
    ("context", "authorization", "match"),
    [
        (_execution_context(approval_id=None), _authorization(), "explicit independent mutation approval"),
        (_execution_context(resource_tenant="tenant-b"), _authorization(), "cross-tenant access denied"),
        (_execution_context(grant_expires_at=NOW), _authorization(), "grant is expired"),
        (_execution_context(), _authorization(expires_at=NOW), "valid independent approval is required"),
    ],
)
def test_external_execution_fail_closed_gates(
    tmp_path: Path,
    context: ExternalExecutionContext,
    authorization: AuthorizationEngine,
    match: str,
) -> None:
    factory = _approved_factory(tmp_path)
    gateway = _gateway(tmp_path)
    register_personal_operations_connectors(gateway, mail=_MailConnector())
    with pytest.raises((PersonalOperationsError, PermissionError), match=match):
        factory.apply_external(
            "plan-1",
            context=context,
            gateway=gateway,
            authorization=authorization,
            grants=GrantPolicy(),
            audit=AuditEngine(),
            evidence=EvidenceStore(tmp_path / "evidence"),
        )


def test_missing_connector_and_provider_failure_do_not_mark_plan_applied(tmp_path: Path) -> None:
    factory = _approved_factory(tmp_path)
    gateway = _gateway(tmp_path)
    with pytest.raises(ValueError, match="not registered"):
        factory.apply_external(
            "plan-1",
            context=_execution_context(),
            gateway=gateway,
            authorization=_authorization(),
            grants=GrantPolicy(),
            audit=AuditEngine(),
            evidence=EvidenceStore(tmp_path / "missing-evidence"),
        )
    assert factory.review_projection("plan-1")["external_applied"] is False

    failed = _approved_factory(tmp_path / "provider")
    failed_gateway = _gateway(tmp_path)
    register_personal_operations_connectors(failed_gateway, mail=_MailConnector(fail=True))
    with pytest.raises(RuntimeError, match="provider unavailable"):
        failed.apply_external(
            "plan-1",
            context=_execution_context(),
            gateway=failed_gateway,
            authorization=_authorization(),
            grants=GrantPolicy(),
            audit=AuditEngine(),
            evidence=EvidenceStore(tmp_path / "provider-evidence"),
        )
    assert failed.review_projection("plan-1")["external_applied"] is False
