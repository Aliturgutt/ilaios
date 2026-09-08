"""Tests for bounded Commerce/Growth Factory governance and execution gates."""

from datetime import datetime, timedelta, timezone

import pytest

from services.commerce_growth_factory import (
    CommerceGrowthError,
    CommerceGrowthFactory,
    GrowthExecutionRequest,
)
from services.identity import (
    ApprovalRecord,
    AuthorizationEngine,
    AuthorizationRule,
    IdentityError,
    IdentityKind,
    Principal,
)
from src.core.audit_engine import AuditEngine
from src.core.evidence_chain import EvidenceChain


def _factory() -> CommerceGrowthFactory:
    factory = CommerceGrowthFactory()
    factory.register_source(
        "market-evidence",
        locator="fixture://commerce/market-evidence",
        content=b"bounded market evidence",
        trusted=True,
    )
    return factory


def _approved_email_plan(factory: CommerceGrowthFactory, plan_id: str = "plan-1") -> None:
    factory.propose(
        plan_id,
        objective="Send approved outreach.",
        audience="Prospects",
        channels=("email_draft",),
        source_ids=("market-evidence",),
    )
    factory.approve_for_review(plan_id, approver="review-owner")


def _principal() -> Principal:
    return Principal(
        principal_id="requester-1",
        tenant_id="tenant-1",
        kind=IdentityKind.HUMAN,
        roles=frozenset({"owner"}),
        attributes=frozenset(),
        authentication_methods=frozenset({"mfa"}),
    )


def _authorization(now: datetime) -> AuthorizationEngine:
    return AuthorizationEngine(
        rules=(
            AuthorizationRule(
                action="commerce_growth.execute",
                roles=frozenset({"owner"}),
            ),
        ),
        approvals=(
            ApprovalRecord(
                approval_id="approval-1",
                tenant_id="tenant-1",
                action="commerce_growth.execute",
                requester_id="requester-1",
                approver_id="independent-approver",
                expires_at=now + timedelta(minutes=5),
            ),
        ),
    )


class _Gateway:
    def __init__(self, *, target_account: str = "account-1") -> None:
        self.target_account = target_account
        self.calls: list[tuple[str, dict[str, str]]] = []

    def dispatch(self, tool_name: str, *args: object, **kwargs: object) -> object:
        payload = kwargs["payload"]
        assert isinstance(payload, dict)
        normalized = {str(key): str(value) for key, value in payload.items()}
        self.calls.append((tool_name, normalized))
        return {
            "outcome": "success",
            "provider_receipt_id": "provider-receipt-1",
            "provider_timestamp": "2026-09-09T00:00:00Z",
            "target_account": self.target_account,
            "idempotency_key": normalized["idempotency_key"],
        }


def _request(*, execution_id: str = "exec-1", idempotency_key: str = "idem-1") -> GrowthExecutionRequest:
    return GrowthExecutionRequest(
        execution_id=execution_id,
        provider="test-provider",
        provider_action="send_email_campaign",
        target_account="account-1",
        idempotency_key=idempotency_key,
    )


def test_growth_plan_is_deterministic_and_review_projection_preserves_provenance() -> None:
    first = _factory()
    first_plan = first.propose(
        "plan-1",
        objective="Explain a verified product capability.",
        audience="Technical founders",
        channels=("content_draft", "sales_enablement"),
        source_ids=("market-evidence",),
    )
    approved = first.approve_for_review("plan-1", approver="human-owner")
    projection = first.review_projection("plan-1")

    second = _factory()
    second_plan = second.propose(
        "plan-1",
        objective="Explain a verified product capability.",
        audience="Technical founders",
        channels=("content_draft", "sales_enablement"),
        source_ids=("market-evidence",),
    )

    assert first_plan.plan_sha256 == second_plan.plan_sha256
    assert approved.approved_for_review is True
    assert approved.external_applied is False
    assert projection["plan_sha256"] == approved.plan_sha256
    assert projection["paid_spend_cents"] == 0
    assert projection["sources"][0]["source_id"] == "market-evidence"
    assert len(projection["sources"][0]["content_sha256"]) == 64


def test_paid_spend_and_unsupported_channels_fail_closed() -> None:
    factory = _factory()
    with pytest.raises(CommerceGrowthError, match="paid spend"):
        factory.propose(
            "paid-plan",
            objective="Paid acquisition",
            audience="Prospects",
            channels=("content_draft",),
            source_ids=("market-evidence",),
            paid_spend_cents=1,
        )
    with pytest.raises(CommerceGrowthError, match="unsupported growth channels"):
        factory.propose(
            "unsupported-plan",
            objective="Unsupported channel",
            audience="Prospects",
            channels=("ad_network",),
            source_ids=("market-evidence",),
        )


def test_unknown_untrusted_and_duplicate_sources_fail_closed() -> None:
    factory = _factory()
    factory.register_source(
        "untrusted",
        locator="fixture://commerce/untrusted",
        content=b"untrusted evidence",
        trusted=False,
    )
    with pytest.raises(CommerceGrowthError, match="unknown sources"):
        factory.propose(
            "missing-plan",
            objective="Missing evidence",
            audience="Prospects",
            channels=("email_draft",),
            source_ids=("missing",),
        )
    with pytest.raises(CommerceGrowthError, match="sources must be trusted"):
        factory.propose(
            "untrusted-plan",
            objective="Untrusted evidence",
            audience="Prospects",
            channels=("email_draft",),
            source_ids=("untrusted",),
        )
    with pytest.raises(CommerceGrowthError, match="duplicates"):
        factory.propose(
            "duplicate-plan",
            objective="Duplicate evidence",
            audience="Prospects",
            channels=("email_draft",),
            source_ids=("market-evidence", "market-evidence"),
        )


def test_external_execution_requires_explicit_governance_dependencies() -> None:
    factory = _factory()
    _approved_email_plan(factory)
    with pytest.raises(CommerceGrowthError, match="external execution requires"):
        factory.apply_external("plan-1")


def test_external_execution_uses_authorization_tool_gateway_audit_and_evidence() -> None:
    factory = _factory()
    _approved_email_plan(factory)
    now = datetime(2026, 9, 9, tzinfo=timezone.utc)
    gateway = _Gateway()
    audit = AuditEngine()
    evidence = EvidenceChain()

    receipt = factory.apply_external(
        "plan-1",
        request=_request(),
        principal=_principal(),
        authorization=_authorization(now),
        approval_id="approval-1",
        tool_gateway=gateway,
        audit=audit,
        evidence=evidence,
        now=now,
    )

    assert gateway.calls[0][0] == "commerce_growth.execute"
    assert gateway.calls[0][1]["tenant_id"] == "tenant-1"
    assert gateway.calls[0][1]["target_account"] == "account-1"
    assert receipt.provider_receipt_id == "provider-receipt-1"
    assert receipt.evidence_hash == evidence.get_records()[0].data_hash
    assert evidence.verify_integrity() is True
    latest_audit = audit.get_latest()
    assert latest_audit is not None
    assert latest_audit.status == "success"
    assert factory.execution_receipt("exec-1") == receipt


def test_execution_requires_independent_unconsumed_approval() -> None:
    factory = _factory()
    _approved_email_plan(factory)
    now = datetime(2026, 9, 9, tzinfo=timezone.utc)
    with pytest.raises(IdentityError, match="valid independent approval"):
        factory.apply_external(
            "plan-1",
            request=_request(),
            principal=_principal(),
            authorization=_authorization(now),
            approval_id="missing-approval",
            tool_gateway=_Gateway(),
            audit=AuditEngine(),
            evidence=EvidenceChain(),
            now=now,
        )


def test_provider_receipt_mismatch_fails_closed_and_is_audited() -> None:
    factory = _factory()
    _approved_email_plan(factory)
    now = datetime(2026, 9, 9, tzinfo=timezone.utc)
    audit = AuditEngine()
    with pytest.raises(CommerceGrowthError, match="external provider execution failed closed"):
        factory.apply_external(
            "plan-1",
            request=_request(),
            principal=_principal(),
            authorization=_authorization(now),
            approval_id="approval-1",
            tool_gateway=_Gateway(target_account="wrong-account"),
            audit=audit,
            evidence=EvidenceChain(),
            now=now,
        )
    latest_audit = audit.get_latest()
    assert latest_audit is not None
    assert latest_audit.status == "failure"


def test_provider_action_must_match_approved_plan_channel() -> None:
    factory = _factory()
    _approved_email_plan(factory)
    now = datetime(2026, 9, 9, tzinfo=timezone.utc)
    with pytest.raises(CommerceGrowthError, match="provider action is not allowed"):
        factory.apply_external(
            "plan-1",
            request=GrowthExecutionRequest(
                execution_id="exec-1",
                provider="test-provider",
                provider_action="publish_social",
                target_account="account-1",
                idempotency_key="idem-1",
            ),
            principal=_principal(),
            authorization=_authorization(now),
            approval_id="approval-1",
            tool_gateway=_Gateway(),
            audit=AuditEngine(),
            evidence=EvidenceChain(),
            now=now,
        )
