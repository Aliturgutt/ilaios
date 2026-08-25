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


NOW = datetime(2026, 8, 25, 20, 0, tzinfo=timezone.utc)


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
        raise AssertionError("account deletion must not be called by revoke-all")


class _AccountSessions:
    def __init__(self, *, fail: bool = False) -> None:
        self.calls: list[dict[str, object]] = []
        self._fail = fail

    def logout_session(
        self,
        *,
        authenticated_user_id: str,
        authenticated_tenant_id: str,
        session_id: str,
    ) -> bool:
        raise AssertionError("logout must not be called by revoke-all")

    def revoke_all_sessions(
        self,
        *,
        authenticated_user_id: str,
        authenticated_tenant_id: str,
        recent_authentication_verified: bool,
    ) -> int:
        if self._fail:
            raise CentralIdentityError("revoke-all denied")
        self.calls.append(
            {
                "authenticated_user_id": authenticated_user_id,
                "authenticated_tenant_id": authenticated_tenant_id,
                "recent_authentication_verified": recent_authentication_verified,
            }
        )
        return 3


def _runtime(
    *,
    verifier: _Verifier | None = None,
    account_sessions: _AccountSessions | None = None,
    bind_account_sessions: bool = True,
) -> tuple[AccountLifecycleHttpRuntime, _AccountSessions]:
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
                action="identity.session.revoke_all",
                roles=frozenset({"Owner"}),
                identity_kinds=frozenset({IdentityKind.HUMAN}),
            ),
        )
    )
    session_lifecycle = account_sessions or _AccountSessions()
    runtime = AccountLifecycleHttpRuntime(
        authentication=boundary,
        sessions=sessions,
        authorization=authorization,
        account_deletion=_AccountDeletion(),
        account_sessions=session_lifecycle if bind_account_sessions else None,
    )
    return runtime, session_lifecycle


def _request(
    *,
    encoded_token: str = "token",
    body: dict[str, object] | None = None,
    recent_authentication_verified: bool = True,
) -> AccountLifecycleHttpRequest:
    return AccountLifecycleHttpRequest(
        path="/api/account/sessions/revoke-all",
        method="POST",
        encoded_token=encoded_token,
        session_id="session-1",
        body={} if body is None else body,
        recent_authentication_verified=recent_authentication_verified,
    )


def test_revoke_all_http_wiring_uses_only_canonical_bound_account() -> None:
    runtime, account_sessions = _runtime()
    response = runtime.handle(_request(), now=NOW)

    assert response.status_code == 200
    assert response.body == {"status": "sessions_revoked", "revoked_sessions": 3}
    assert account_sessions.calls == [
        {
            "authenticated_user_id": "user-1",
            "authenticated_tenant_id": "tenant-1",
            "recent_authentication_verified": True,
        }
    ]
    assert "user-1" not in repr(response.body)
    assert "tenant-1" not in repr(response.body)
    assert "session-1" not in repr(response.body)


def test_revoke_all_http_wiring_requires_recent_authentication() -> None:
    runtime, account_sessions = _runtime()
    response = runtime.handle(
        _request(recent_authentication_verified=False),
        now=NOW,
    )

    assert response.status_code == 403
    assert response.body == {"error": "IDENTITY_DENIED"}
    assert account_sessions.calls == []


def test_revoke_all_http_wiring_rejects_client_authority_fields() -> None:
    runtime, account_sessions = _runtime()
    response = runtime.handle(
        _request(body={"user_id": "victim", "tenant_id": "tenant-2"}),
        now=NOW,
    )

    assert response.status_code == 400
    assert response.body == {"error": "INVALID_REQUEST"}
    assert account_sessions.calls == []


def test_revoke_all_http_wiring_denies_auth_or_session_mismatch() -> None:
    runtime, account_sessions = _runtime(verifier=_Verifier(subject="attacker"))
    response = runtime.handle(_request(), now=NOW)

    assert response.status_code == 403
    assert response.body == {"error": "IDENTITY_DENIED"}
    assert account_sessions.calls == []


def test_revoke_all_http_wiring_fails_closed_when_service_denies() -> None:
    denied = _AccountSessions(fail=True)
    runtime, account_sessions = _runtime(account_sessions=denied)
    response = runtime.handle(_request(), now=NOW)

    assert response.status_code == 409
    assert response.body == {"error": "ACCOUNT_REVOKE_ALL_DENIED"}
    assert account_sessions.calls == []


def test_revoke_all_http_wiring_requires_bound_session_authority() -> None:
    runtime, account_sessions = _runtime(bind_account_sessions=False)
    response = runtime.handle(_request(), now=NOW)

    assert response.status_code == 404
    assert response.body == {"error": "LIFECYCLE_ROUTE_NOT_WIRED"}
    assert account_sessions.calls == []
