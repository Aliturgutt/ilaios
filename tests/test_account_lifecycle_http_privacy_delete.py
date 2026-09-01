from __future__ import annotations

from datetime import datetime, timedelta, timezone

from services.account_lifecycle_http_runtime import (
    AccountLifecycleHttpRequest,
    AccountLifecycleHttpRuntime,
)
from services.central_identity import CentralIdentityError
from services.identity import (
    AuthenticationBoundary,
    AuthorizationEngine,
    AuthorizationRule,
    IdentityKind,
    IdentityPolicy,
    Principal,
    SessionRegistry,
    VerifiedOIDCClaims,
)


NOW = datetime(2026, 8, 26, 2, 0, tzinfo=timezone.utc)
CUTOFF = "2026-08-25T00:00:00+00:00"


class _Verifier:
    def __init__(self, *, subject: str = "user-1", tenant_id: str = "tenant-1") -> None:
        self._subject = subject
        self._tenant_id = tenant_id

    def verify(self, encoded_token: str) -> VerifiedOIDCClaims:
        if encoded_token != "token":
            raise ValueError("invalid test token")
        return VerifiedOIDCClaims(
            issuer="https://issuer.example",
            audience="ilaios-web",
            subject=self._subject,
            tenant_id=self._tenant_id,
            expires_at=NOW + timedelta(minutes=30),
            issued_at=NOW - timedelta(minutes=1),
            kind=IdentityKind.HUMAN,
            roles=frozenset({"Owner"}),
            authentication_methods=frozenset({"mfa"}),
        )


class _AccountDeletion:
    def delete_account(
        self,
        *,
        user_id: str,
        recent_authentication_verified: bool,
        deletion_confirmation_verified: bool,
        occurred_at: str,
    ) -> tuple[int, int, int]:
        raise AssertionError("account deletion authority must not be called")


class _PrivacyRetention:
    def __init__(self, *, fail: bool = False) -> None:
        self.calls: list[dict[str, object]] = []
        self._fail = fail

    def purge_closed_account(
        self,
        *,
        user_id: str,
        retention_cutoff: str,
        privacy_deletion_confirmed: bool,
        occurred_at: str,
    ) -> tuple[int, int, int]:
        if self._fail:
            raise CentralIdentityError("privacy deletion denied")
        self.calls.append(
            {
                "user_id": user_id,
                "retention_cutoff": retention_cutoff,
                "privacy_deletion_confirmed": privacy_deletion_confirmed,
                "occurred_at": occurred_at,
            }
        )
        return 4, 2, 1


def _runtime(
    *,
    verifier: _Verifier | None = None,
    privacy_retention: _PrivacyRetention | None = None,
) -> tuple[AccountLifecycleHttpRuntime, _PrivacyRetention]:
    boundary = AuthenticationBoundary(
        verifier or _Verifier(),
        IdentityPolicy(
            trusted_issuers=frozenset({"https://issuer.example"}),
            audience="ilaios-web",
            maximum_session=timedelta(hours=1),
        ),
    )
    sessions = SessionRegistry(maximum_lifetime=timedelta(hours=1))
    principal = Principal(
        principal_id="user-1",
        tenant_id="tenant-1",
        kind=IdentityKind.HUMAN,
        roles=frozenset({"Owner"}),
        attributes=frozenset(),
        authentication_methods=frozenset({"mfa"}),
    )
    sessions.issue("session-1", principal, NOW, timedelta(minutes=30))
    authorization = AuthorizationEngine(
        (
            AuthorizationRule(
                action="identity.account.privacy_delete",
                roles=frozenset({"Owner"}),
                identity_kinds=frozenset({IdentityKind.HUMAN}),
            ),
        )
    )
    retention = privacy_retention or _PrivacyRetention()
    runtime = AccountLifecycleHttpRuntime(
        authentication=boundary,
        sessions=sessions,
        authorization=authorization,
        account_deletion=_AccountDeletion(),
        privacy_retention=retention,
    )
    return runtime, retention


def _request(
    *,
    encoded_token: str = "token",
    session_id: str = "session-1",
    body: dict[str, object] | None = None,
    recent_authentication_verified: bool = True,
    retention_cutoff: str | None = CUTOFF,
) -> AccountLifecycleHttpRequest:
    return AccountLifecycleHttpRequest(
        path="/api/account/privacy-delete",
        method="DELETE",
        encoded_token=encoded_token,
        session_id=session_id,
        body={"confirm": True} if body is None else body,
        recent_authentication_verified=recent_authentication_verified,
        retention_cutoff=retention_cutoff,
    )


def test_privacy_delete_delegates_canonical_user_and_trusted_retention_cutoff() -> None:
    runtime, retention = _runtime()
    response = runtime.handle(_request(), now=NOW)

    assert response.status_code == 200
    assert response.body == {
        "status": "privacy_deleted",
        "deleted_sessions": 4,
        "deleted_memberships": 2,
        "deleted_user": 1,
    }
    assert retention.calls == [
        {
            "user_id": "user-1",
            "retention_cutoff": CUTOFF,
            "privacy_deletion_confirmed": True,
            "occurred_at": NOW.isoformat(),
        }
    ]
    assert "user-1" not in repr(response.body)
    assert "session-1" not in repr(response.body)


def test_privacy_delete_is_unauthenticated_and_session_mismatch_default_deny() -> None:
    runtime, retention = _runtime()
    unauthenticated = runtime.handle(_request(encoded_token=""), now=NOW)
    assert unauthenticated.status_code == 403
    assert unauthenticated.body == {"error": "IDENTITY_DENIED"}

    mismatched_runtime, mismatched_retention = _runtime(
        verifier=_Verifier(subject="attacker")
    )
    mismatched = mismatched_runtime.handle(_request(), now=NOW)
    assert mismatched.status_code == 403
    assert mismatched.body == {"error": "IDENTITY_DENIED"}
    assert retention.calls == []
    assert mismatched_retention.calls == []


def test_privacy_delete_requires_recent_auth_confirmation_and_server_cutoff() -> None:
    runtime, retention = _runtime()

    recent_auth_denied = runtime.handle(
        _request(recent_authentication_verified=False), now=NOW
    )
    confirmation_denied = runtime.handle(_request(body={"confirm": False}), now=NOW)
    cutoff_missing = runtime.handle(_request(retention_cutoff=None), now=NOW)

    assert recent_auth_denied.status_code == 403
    assert recent_auth_denied.body == {"error": "IDENTITY_DENIED"}
    assert confirmation_denied.status_code == 409
    assert confirmation_denied.body == {"error": "PRIVACY_DELETE_DENIED"}
    assert cutoff_missing.status_code == 400
    assert cutoff_missing.body == {"error": "INVALID_REQUEST"}
    assert retention.calls == []


def test_privacy_delete_rejects_client_authority_and_cutoff_override_fields() -> None:
    runtime, retention = _runtime()
    for body in (
        {"confirm": True, "user_id": "victim"},
        {"confirm": True, "tenant_id": "tenant-2"},
        {"confirm": True, "retention_cutoff": "2099-01-01T00:00:00+00:00"},
        {"confirm": True, "session_id": "other-session"},
    ):
        response = runtime.handle(_request(body=body), now=NOW)
        assert response.status_code == 400
        assert response.body == {"error": "INVALID_REQUEST"}
    assert retention.calls == []


def test_privacy_delete_fails_closed_when_service_is_unbound_or_denies() -> None:
    boundary = AuthenticationBoundary(
        _Verifier(),
        IdentityPolicy(
            trusted_issuers=frozenset({"https://issuer.example"}),
            audience="ilaios-web",
            maximum_session=timedelta(hours=1),
        ),
    )
    sessions = SessionRegistry(maximum_lifetime=timedelta(hours=1))
    principal = Principal(
        principal_id="user-1",
        tenant_id="tenant-1",
        kind=IdentityKind.HUMAN,
        roles=frozenset({"Owner"}),
        attributes=frozenset(),
        authentication_methods=frozenset({"mfa"}),
    )
    sessions.issue("session-1", principal, NOW, timedelta(minutes=30))
    authorization = AuthorizationEngine(
        (
            AuthorizationRule(
                action="identity.account.privacy_delete",
                roles=frozenset({"Owner"}),
                identity_kinds=frozenset({IdentityKind.HUMAN}),
            ),
        )
    )
    unbound = AccountLifecycleHttpRuntime(
        authentication=boundary,
        sessions=sessions,
        authorization=authorization,
        account_deletion=_AccountDeletion(),
    )
    unbound_response = unbound.handle(_request(), now=NOW)
    assert unbound_response.status_code == 404
    assert unbound_response.body == {"error": "LIFECYCLE_ROUTE_NOT_WIRED"}

    denied_runtime, denied_retention = _runtime(
        privacy_retention=_PrivacyRetention(fail=True)
    )
    denied_response = denied_runtime.handle(_request(), now=NOW)
    assert denied_response.status_code == 409
    assert denied_response.body == {"error": "PRIVACY_DELETE_DENIED"}
    assert denied_retention.calls == []
