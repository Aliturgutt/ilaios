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


def _identity_policy() -> IdentityPolicy:
    return IdentityPolicy(
        frozenset({"https://id.example"}), "ilaios", timedelta(minutes=10)
    )


def test_oidc_boundary_validates_federation_audience_expiry_and_short_lifetime() -> None:
    policy = _identity_policy()
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
    with pytest.raises(IdentityError, match="invalid audience"):
        AuthenticationBoundary(
            _Verifier(_claims(audience="other-client")), policy
        ).authenticate("opaque-to-boundary", NOW)
    with pytest.raises(IdentityError, match="not currently valid"):
        AuthenticationBoundary(
            _Verifier(_claims(expires_at=NOW)), policy
        ).authenticate("opaque-to-boundary", NOW)
    with pytest.raises(IdentityError, match="not currently valid"):
        AuthenticationBoundary(
            _Verifier(_claims(issued_at=NOW + timedelta(seconds=1))), policy
        ).authenticate("opaque-to-boundary", NOW)
    with pytest.raises(IdentityError, match="subject and tenant"):
        AuthenticationBoundary(_Verifier(_claims(subject="")), policy).authenticate(
            "opaque-to-boundary", NOW
        )
    with pytest.raises(IdentityError, match="subject and tenant"):
        AuthenticationBoundary(_Verifier(_claims(subject="   ")), policy).authenticate(
            "opaque-to-boundary", NOW
        )
    with pytest.raises(IdentityError, match="subject and tenant"):
        AuthenticationBoundary(_Verifier(_claims(tenant_id="")), policy).authenticate(
            "opaque-to-boundary", NOW
        )
    with pytest.raises(IdentityError, match="subject and tenant"):
        AuthenticationBoundary(_Verifier(_claims(tenant_id="\t")), policy).authenticate(
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
    with pytest.raises(IdentityError, match="request tenant"):
        engine.authorize(
            _principal(), AccessRequest("tenant-b", "tenant-a", "deploy"), NOW
        )
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


def test_high_risk_requires_separate_exact_unexpired_single_use_approval() -> None:
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
    request = AccessRequest(
        "tenant-a", "tenant-a", "delete", high_risk=True, approval_id="approval-1"
    )
    engine.authorize(_principal(), request, NOW)
    with pytest.raises(IdentityError, match="independent approval"):
        engine.authorize(_principal(), request, NOW)


def test_high_risk_rejects_missing_expired_revoked_wrong_scope_and_self_approval() -> None:
    rule = AuthorizationRule("delete", frozenset({"operator"}))
    approvals = (
        ApprovalRecord(
            "expired",
            "tenant-a",
            "delete",
            "human-1",
            "human-2",
            NOW,
        ),
        ApprovalRecord(
            "revoked",
            "tenant-a",
            "delete",
            "human-1",
            "human-2",
            NOW + timedelta(minutes=5),
            revoked=True,
        ),
        ApprovalRecord(
            "wrong-tenant",
            "tenant-b",
            "delete",
            "human-1",
            "human-2",
            NOW + timedelta(minutes=5),
        ),
        ApprovalRecord(
            "wrong-action",
            "tenant-a",
            "deploy",
            "human-1",
            "human-2",
            NOW + timedelta(minutes=5),
        ),
        ApprovalRecord(
            "self",
            "tenant-a",
            "delete",
            "human-1",
            "human-1",
            NOW + timedelta(minutes=5),
        ),
    )
    engine = AuthorizationEngine((rule,), approvals)
    for approval_id in (None, "expired", "revoked", "wrong-tenant", "wrong-action", "self"):
        with pytest.raises(IdentityError, match="independent approval"):
            engine.authorize(
                _principal(),
                AccessRequest(
                    "tenant-a",
                    "tenant-a",
                    "delete",
                    high_risk=True,
                    approval_id=approval_id,
                ),
                NOW,
            )


def test_privileged_operation_requires_mfa() -> None:
    rule = AuthorizationRule("deploy", frozenset({"operator"}))
    engine = AuthorizationEngine((rule,))
    principal = Principal(
        "human-1",
        "tenant-a",
        IdentityKind.HUMAN,
        frozenset({"operator"}),
        frozenset(),
        frozenset(),
    )
    with pytest.raises(IdentityError, match="requires MFA"):
        engine.authorize(
            principal,
            AccessRequest("tenant-a", "tenant-a", "deploy", privileged=True),
            NOW,
        )


def test_sessions_are_short_lived_tenant_bound_unique_and_revocable() -> None:
    registry = SessionRegistry(timedelta(minutes=15))
    session = registry.issue("session-1", _principal(), NOW, timedelta(minutes=5))
    assert registry.validate(session.session_id, "tenant-a", NOW) == session
    with pytest.raises(IdentityError, match="session cannot be issued"):
        registry.issue("session-1", _principal(), NOW, timedelta(minutes=5))
    with pytest.raises(IdentityError, match="invalid or revoked"):
        registry.validate(session.session_id, "tenant-b", NOW)
    registry.revoke_session(session.session_id)
    with pytest.raises(IdentityError, match="invalid or revoked"):
        registry.validate(session.session_id, "tenant-a", NOW)


def test_session_boundary_rejects_blank_session_principal_and_tenant_identity() -> None:
    registry = SessionRegistry(timedelta(minutes=15))
    for session_id in ("", "   ", "\t"):
        with pytest.raises(IdentityError, match="session identity"):
            registry.issue(session_id, _principal(), NOW, timedelta(minutes=5))

    blank_principal = Principal(
        "   ",
        "tenant-a",
        IdentityKind.HUMAN,
        frozenset({"operator"}),
        frozenset(),
        frozenset({"mfa"}),
    )
    with pytest.raises(IdentityError, match="session identity"):
        registry.issue("session-blank-principal", blank_principal, NOW, timedelta(minutes=5))

    blank_tenant = Principal(
        "human-1",
        " ",
        IdentityKind.HUMAN,
        frozenset({"operator"}),
        frozenset(),
        frozenset({"mfa"}),
    )
    with pytest.raises(IdentityError, match="session identity"):
        registry.issue("session-blank-tenant", blank_tenant, NOW, timedelta(minutes=5))

    with pytest.raises(IdentityError, match="invalid or revoked"):
        registry.validate(" ", "tenant-a", NOW)
    with pytest.raises(IdentityError, match="invalid or revoked"):
        registry.validate("session-unknown", " ", NOW)
    with pytest.raises(IdentityError, match="principal identity"):
        registry.revoke_principal("   ")


def test_revoked_principal_cannot_reissue_or_validate_session() -> None:
    registry = SessionRegistry(timedelta(minutes=15))
    session = registry.issue("session-1", _principal(), NOW, timedelta(minutes=5))
    registry.revoke_principal("human-1")
    with pytest.raises(IdentityError, match="invalid or revoked"):
        registry.validate(session.session_id, "tenant-a", NOW)
    with pytest.raises(IdentityError, match="session cannot be issued"):
        registry.issue("session-2", _principal(), NOW, timedelta(minutes=5))


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
