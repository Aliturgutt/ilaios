"""Exact bounded proofs for IAM.I02."""

from datetime import datetime, timedelta, timezone

import pytest

from services.identity import (
    AccessRequest,
    ApprovalRecord,
    AuthenticationBoundary,
    AuthorizationEngine,
    AuthorizationRule,
    BreakGlassRecord,
    EmergencyAccessRegistry,
    IdentityError,
    IdentityKind,
    IdentityPolicy,
    Principal,
    RecoveryRecord,
    SessionRegistry,
    VerifiedOIDCClaims,
)

NOW = datetime(2026, 8, 9, tzinfo=timezone.utc)


class _Verifier:
    def __init__(self, claims: VerifiedOIDCClaims) -> None:
        self.claims = claims

    def verify(self, encoded_token: str) -> VerifiedOIDCClaims:
        assert encoded_token == "opaque-to-boundary"
        return self.claims


def _claims(**changes: object) -> VerifiedOIDCClaims:
    values: dict[str, object] = {
        "issuer": "https://id.example",
        "audience": "ilaios",
        "subject": "human-1",
        "tenant_id": "tenant-a",
        "issued_at": NOW,
        "expires_at": NOW + timedelta(minutes=5),
        "kind": IdentityKind.HUMAN,
        "roles": frozenset({"operator"}),
        "attributes": frozenset({("department", "security")}),
        "authentication_methods": frozenset({"mfa"}),
    }
    values.update(changes)
    return VerifiedOIDCClaims(**values)  # type: ignore[arg-type]


def _principal() -> Principal:
    return Principal(
        "human-1",
        "tenant-a",
        IdentityKind.HUMAN,
        frozenset({"operator"}),
        frozenset({("department", "security")}),
        frozenset({"mfa"}),
    )


def test_oidc_boundary_validates_federation_audience_expiry_and_short_lifetime() -> (
    None
):
    policy = IdentityPolicy(
        frozenset({"https://id.example"}), "ilaios", timedelta(minutes=10)
    )
    assert (
        AuthenticationBoundary(_Verifier(_claims()), policy)
        .authenticate("opaque-to-boundary", NOW)
        .principal_id
        == "human-1"
    )
    with pytest.raises(IdentityError, match="untrusted issuer"):
        AuthenticationBoundary(_Verifier(_claims(issuer="evil")), policy).authenticate(
            "opaque-to-boundary", NOW
        )
    with pytest.raises(IdentityError, match="lifetime"):
        AuthenticationBoundary(
            _Verifier(_claims(expires_at=NOW + timedelta(hours=1))), policy
        ).authenticate("opaque-to-boundary", NOW)


def test_tenant_rbac_abac_kind_and_default_deny() -> None:
    rule = AuthorizationRule(
        "deploy",
        frozenset({"operator"}),
        frozenset({("department", "security")}),
        frozenset({("classification", "internal")}),
        frozenset({IdentityKind.HUMAN}),
    )
    engine = AuthorizationEngine((rule,))
    request = AccessRequest(
        "tenant-a",
        "tenant-a",
        "deploy",
        frozenset({("classification", "internal")}),
        privileged=True,
    )
    engine.authorize(_principal(), request, NOW)
    with pytest.raises(IdentityError, match="cross-tenant"):
        engine.authorize(
            _principal(), AccessRequest("tenant-a", "tenant-b", "deploy"), NOW
        )
    service = Principal(
        "svc-1",
        "tenant-a",
        IdentityKind.SERVICE,
        frozenset({"operator"}),
        frozenset({("department", "security")}),
        frozenset(),
    )
    with pytest.raises(IdentityError, match="deny by default"):
        engine.authorize(service, AccessRequest("tenant-a", "tenant-a", "deploy"), NOW)


def test_high_risk_requires_separate_exact_unexpired_approval() -> None:
    rule = AuthorizationRule("delete", frozenset({"operator"}))
    approval = ApprovalRecord(
        "approval-1",
        "tenant-a",
        "delete",
        "human-1",
        "human-2",
        NOW + timedelta(minutes=5),
    )
    engine = AuthorizationEngine((rule,), (approval,))
    engine.authorize(
        _principal(),
        AccessRequest(
            "tenant-a", "tenant-a", "delete", high_risk=True, approval_id="approval-1"
        ),
        NOW,
    )
    with pytest.raises(IdentityError, match="independent approval"):
        engine.authorize(
            _principal(),
            AccessRequest("tenant-a", "tenant-a", "delete", high_risk=True),
            NOW,
        )


def test_sessions_are_short_lived_tenant_bound_and_revocable() -> None:
    registry = SessionRegistry(timedelta(minutes=15))
    session = registry.issue("session-1", _principal(), NOW, timedelta(minutes=5))
    assert registry.validate(session.session_id, "tenant-a", NOW) == session
    with pytest.raises(IdentityError, match="invalid or revoked"):
        registry.validate(session.session_id, "tenant-b", NOW)
    registry.revoke_principal("human-1")
    with pytest.raises(IdentityError, match="invalid or revoked"):
        registry.validate(session.session_id, "tenant-a", NOW)


def test_recovery_and_break_glass_require_independent_time_bound_records() -> None:
    registry = EmergencyAccessRegistry()
    registry.record_recovery(
        RecoveryRecord("recovery-1", "human-1", "human-2", NOW + timedelta(minutes=5))
    )
    record = BreakGlassRecord(
        "event-1",
        "human-1",
        "tenant-a",
        "identity provider outage",
        "human-2",
        NOW + timedelta(minutes=5),
    )
    registry.activate_break_glass(record, NOW)
    assert registry.active_break_glass("event-1", NOW) == record
    with pytest.raises(IdentityError, match="approver"):
        registry.activate_break_glass(
            BreakGlassRecord(
                "event-2",
                "human-1",
                "tenant-a",
                "outage",
                "human-1",
                NOW + timedelta(minutes=5),
            ),
            NOW,
        )
