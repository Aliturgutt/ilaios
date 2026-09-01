"""Bounded proofs for ORG.I08."""

from datetime import datetime, timedelta, timezone

import pytest

from services.governance.records import (
    AssuranceClaim,
    ExceptionRecord,
    GovernanceRecordError,
    GovernanceRegistry,
    LifecycleRecord,
    LifecycleStatus,
    RACIRecord,
    RiskRecord,
    RiskStatus,
)

NOW = datetime(2026, 8, 9, tzinfo=timezone.utc)


def test_raci_has_unique_accountability_and_independent_verifier() -> None:
    registry = GovernanceRegistry()
    record = RACIRecord(
        "tenant-isolation",
        "security-owner",
        frozenset({"platform-team"}),
        frozenset({"privacy"}),
        frozenset({"audit"}),
        "verifier-1",
        NOW,
        NOW + timedelta(days=90),
    )
    registry.register_raci(record)
    with pytest.raises(GovernanceRecordError, match="already"):
        registry.register_raci(record)


def test_risk_acceptance_and_exception_approval_separate_authority_and_expire() -> None:
    registry = GovernanceRegistry()
    registry.register_risk(
        RiskRecord("risk-1", "owner-1", "high", "mitigate", NOW + timedelta(days=10))
    )
    with pytest.raises(GovernanceRecordError, match="separate"):
        registry.accept_risk("risk-1", "owner-1")
    assert (
        registry.accept_risk("risk-1", "risk-authority").status is RiskStatus.ACCEPTED
    )
    exception = ExceptionRecord(
        "exception-1",
        "control-1",
        "requester-1",
        "approver-1",
        "migration",
        ("deny external access",),
        NOW + timedelta(days=2),
        NOW + timedelta(days=1),
    )
    registry.approve_exception(exception, NOW)
    registry.authorize_exception("exception-1", "control-1", NOW)
    with pytest.raises(GovernanceRecordError, match="active reviewed"):
        registry.authorize_exception(
            "exception-1", "control-1", NOW + timedelta(days=1)
        )


def test_deprecation_retirement_and_claims_require_durable_evidence() -> None:
    registry = GovernanceRegistry()
    with pytest.raises(GovernanceRecordError, match="replacement"):
        registry.register_lifecycle(
            LifecycleRecord("api-v1", "owner", LifecycleStatus.DEPRECATED, NOW)
        )
    registry.register_lifecycle(
        LifecycleRecord(
            "api-v1",
            "owner",
            LifecycleStatus.DEPRECATED,
            NOW + timedelta(days=1),
            "api-v2",
            NOW + timedelta(days=30),
        )
    )
    with pytest.raises(GovernanceRecordError, match="independent"):
        AssuranceClaim(
            "claim-1",
            "certified",
            "platform",
            "evidence-1",
            "self",
            NOW,
            False,
            "ISO-example",
        )
    registry.register_claim(
        AssuranceClaim(
            "claim-2",
            "control tested",
            "reference implementation",
            "evidence-2",
            "verifier-1",
            NOW,
            False,
        )
    )
