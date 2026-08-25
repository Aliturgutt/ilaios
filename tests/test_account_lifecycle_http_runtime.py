from __future__ import annotations

from datetime import datetime, timedelta, timezone

from services.account_lifecycle_http_runtime import (
    AccountLifecycleHttpRequest,
    AccountLifecycleHttpRuntime,
)
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


NOW = datetime(2026, 8, 25, 15, 0, tzinfo=timezone.utc)


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
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def delete_account(
        self,
        *,
        user_id: str,
        recent_authentication_verified: bool,
        deletion_confirmation_verified: bool,
        occurred_at: str,
    ) -> tuple[int, int, int]:
        self.calls.append(
            {
                "user_id": user_id,
                "recent_authentication_verified": recent_authentication_verified,
                "deletion_confirmation_verified": deletion_confirmation_verified,
                "occurred_at": occurred_at,
            }
        )
        return 2, 3, 4


def _runtime(
    *,
    verifier: _Verifier | None = None,
    authorization_tenant: str = "tenant-1",
) -> tuple[AccountLifecycleHttpRuntime, _AccountDeletion, SessionRegistry]:
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
        tenant_id=authorization_tenant,
        kind=IdentityKind.HUMAN,
        roles=frozenset({"Owner"}),
        attributes=frozenset(),
        authentication_methods=frozenset({"mfa"}),
    )
    sessions.issue("session-1", principal, NOW, timedelta(minutes=30))
    authorization = AuthorizationEngine(
        (
            AuthorizationRule(
                action="identity.account.delete",
                roles=frozenset({"Owner"}),
                identity_kinds=frozenset({IdentityKind.HUMAN}),
            ),
        )
    )
    deletion = _AccountDeletion()
    runtime = AccountLifecycleHttpRuntime(
        authentication=boundary,
        sessions=sessions,
        authorization=authorization,
        account_deletion=deletion,
    )
    return runtime, deletion, sessions


def _request(
    *,
    path: str = "/api/account/delete",
    method: str = "DELETE",
    encoded_token: str = "token",
    session_id: str = "session-1",
    body: dict[str, object] | None = None,
    recent_authentication_verified: bool = True,
) -> AccountLifecycleHttpRequest:
    return AccountLifecycleHttpRequest(
        path=path,
        method=method,
        encoded_token=encoded_token,
        session_id=session_id,
        body={"confirm": True} if body is None else body,
        recent_authentication_verified=recent_authentication_verified,
    )


def test_account_delete_http_wiring_delegates_only_canonical_principal() -> None:
    runtime, deletion, _ = _runtime()

    response = runtime.handle(_request(), now=NOW)

    assert response.status_code == 200
    assert response.body == {
        "status": "deleted",
        "revoked_memberships": 2,
        "revoked_sessions": 3,
        "deleted_identities": 4,
    }
    assert deletion.calls == [
        {
            "user_id": "user-1",
            "recent_authentication_verified": True,
            "deletion_confirmation_verified": True,
            "occurred_at": NOW.isoformat(),
        }
    ]
    assert "user-1" not in repr(response.body)
    assert "session-1" not in repr(response.body)


def test_account_delete_http_wiring_is_unauthenticated_default_deny() -> None:
    runtime, deletion, _ = _runtime()

    response = runtime.handle(_request(encoded_token=""), now=NOW)

    assert response.status_code == 403
    assert response.body == {"error": "IDENTITY_DENIED"}
    assert deletion.calls == []


def test_account_delete_http_wiring_binds_session_to_authenticated_principal() -> None:
    runtime, deletion, _ = _runtime(verifier=_Verifier(subject="attacker"))

    response = runtime.handle(_request(), now=NOW)

    assert response.status_code == 403
    assert response.body == {"error": "IDENTITY_DENIED"}
    assert deletion.calls == []


def test_account_delete_http_wiring_denies_cross_tenant_session_binding() -> None:
    runtime, deletion, _ = _runtime(verifier=_Verifier(tenant_id="tenant-2"))

    response = runtime.handle(_request(), now=NOW)

    assert response.status_code == 403
    assert response.body == {"error": "IDENTITY_DENIED"}
    assert deletion.calls == []


def test_account_delete_http_wiring_requires_recent_auth_and_confirmation() -> None:
    runtime, deletion, _ = _runtime()

    recent_auth_denied = runtime.handle(
        _request(recent_authentication_verified=False),
        now=NOW,
    )
    confirmation_denied = runtime.handle(
        _request(body={"confirm": False}),
        now=NOW,
    )

    assert recent_auth_denied.status_code == 403
    assert recent_auth_denied.body == {"error": "IDENTITY_DENIED"}
    assert confirmation_denied.status_code == 409
    assert confirmation_denied.body == {"error": "ACCOUNT_DELETE_DENIED"}
    assert deletion.calls == []


def test_account_delete_http_wiring_rejects_client_identity_override_fields() -> None:
    runtime, deletion, _ = _runtime()

    response = runtime.handle(
        _request(body={"confirm": True, "user_id": "victim", "tenant_id": "tenant-2"}),
        now=NOW,
    )

    assert response.status_code == 400
    assert response.body == {"error": "INVALID_REQUEST"}
    assert deletion.calls == []


def test_account_delete_http_wiring_requires_exact_route_and_method() -> None:
    runtime, deletion, _ = _runtime()

    for request in (
        _request(path="/api/account/delete/extra"),
        _request(method="POST"),
        _request(path="/api/account/export", method="POST"),
    ):
        response = runtime.handle(request, now=NOW)
        assert response.status_code == 404
        assert response.body["error"] in {
            "LIFECYCLE_ROUTE_NOT_FOUND",
            "LIFECYCLE_ROUTE_NOT_WIRED",
        }
    assert deletion.calls == []
