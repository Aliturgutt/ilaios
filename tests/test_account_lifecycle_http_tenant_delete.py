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


NOW = datetime(2026, 8, 25, 21, 30, tzinfo=timezone.utc)


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
        raise AssertionError("account deletion must not be called by tenant delete")


class _TenantDeletion:
    def __init__(self, *, fail: bool = False) -> None:
        self.calls: list[dict[str, object]] = []
        self._fail = fail

    def delete_tenant(
        self,
        *,
        actor_user_id: str,
        tenant_id: str,
        recent_authentication_verified: bool,
        deletion_confirmation_verified: bool,
        occurred_at: str,
    ) -> tuple[int, int, int, int]:
        if self._fail:
            raise CentralIdentityError("tenant delete denied")
        self.calls.append(
            {
                "actor_user_id": actor_user_id,
                "tenant_id": tenant_id,
                "recent_authentication_verified": recent_authentication_verified,
                "deletion_confirmation_verified": deletion_confirmation_verified,
                "occurred_at": occurred_at,
            }
        )
        return 3, 4, 2, 1


def _runtime(
    *,
    verifier: _Verifier | None = None,
    tenant_deletion: _TenantDeletion | None = None,
    bind_tenant_deletion: bool = True,
) -> tuple[AccountLifecycleHttpRuntime, _TenantDeletion]:
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
                action="identity.tenant.delete",
                roles=frozenset({"Owner"}),
                identity_kinds=frozenset({IdentityKind.HUMAN}),
            ),
        )
    )
    tenant_service = tenant_deletion or _TenantDeletion()
    runtime = AccountLifecycleHttpRuntime(
        authentication=boundary,
        sessions=sessions,
        authorization=authorization,
        account_deletion=_AccountDeletion(),
        tenant_deletion=tenant_service if bind_tenant_deletion else None,
    )
    return runtime, tenant_service


def _request(
    *,
    encoded_token: str = "token",
    session_id: str = "session-1",
    body: dict[str, object] | None = None,
    recent_authentication_verified: bool = True,
    path: str = "/api/tenant/delete",
    method: str = "DELETE",
) -> AccountLifecycleHttpRequest:
    return AccountLifecycleHttpRequest(
        path=path,
        method=method,
        encoded_token=encoded_token,
        session_id=session_id,
        body={"confirm": True} if body is None else body,
        recent_authentication_verified=recent_authentication_verified,
    )


def test_tenant_delete_http_wiring_uses_only_canonical_principal_and_tenant() -> None:
    runtime, tenant_deletion = _runtime()
    response = runtime.handle(_request(), now=NOW)

    assert response.status_code == 200
    assert response.body == {
        "status": "tenant_deleted",
        "revoked_memberships": 3,
        "revoked_sessions": 4,
        "revoked_entitlements": 2,
        "disabled_users": 1,
    }
    assert tenant_deletion.calls == [
        {
            "actor_user_id": "user-1",
            "tenant_id": "tenant-1",
            "recent_authentication_verified": True,
            "deletion_confirmation_verified": True,
            "occurred_at": NOW.isoformat(),
        }
    ]
    assert "user-1" not in repr(response.body)
    assert "tenant-1" not in repr(response.body)
    assert "session-1" not in repr(response.body)


def test_tenant_delete_http_wiring_requires_auth_bound_session_and_recent_auth() -> None:
    runtime, tenant_deletion = _runtime()
    unauthenticated = runtime.handle(_request(encoded_token=""), now=NOW)
    stale_auth = runtime.handle(
        _request(recent_authentication_verified=False),
        now=NOW,
    )

    assert unauthenticated.status_code == 403
    assert stale_auth.status_code == 403
    assert unauthenticated.body == {"error": "IDENTITY_DENIED"}
    assert stale_auth.body == {"error": "IDENTITY_DENIED"}
    assert tenant_deletion.calls == []


def test_tenant_delete_http_wiring_denies_cross_principal_or_tenant_session_binding() -> None:
    attacker_runtime, attacker_deletion = _runtime(verifier=_Verifier(subject="attacker"))
    tenant_runtime, tenant_deletion = _runtime(verifier=_Verifier(tenant_id="tenant-2"))

    attacker = attacker_runtime.handle(_request(), now=NOW)
    cross_tenant = tenant_runtime.handle(_request(), now=NOW)

    assert attacker.status_code == 403
    assert cross_tenant.status_code == 403
    assert attacker_deletion.calls == []
    assert tenant_deletion.calls == []


def test_tenant_delete_http_wiring_requires_explicit_confirmation() -> None:
    runtime, tenant_deletion = _runtime()
    response = runtime.handle(_request(body={"confirm": False}), now=NOW)

    assert response.status_code == 409
    assert response.body == {"error": "TENANT_DELETE_DENIED"}
    assert tenant_deletion.calls == []


def test_tenant_delete_http_wiring_rejects_client_authority_overrides() -> None:
    runtime, tenant_deletion = _runtime()
    response = runtime.handle(
        _request(
            body={
                "confirm": True,
                "tenant_id": "tenant-2",
                "actor_user_id": "attacker",
            }
        ),
        now=NOW,
    )

    assert response.status_code == 400
    assert response.body == {"error": "INVALID_REQUEST"}
    assert tenant_deletion.calls == []


def test_tenant_delete_http_wiring_requires_exact_route_and_method() -> None:
    runtime, tenant_deletion = _runtime()
    wrong_method = runtime.handle(_request(method="POST"), now=NOW)
    wrong_path = runtime.handle(_request(path="/api/tenant/delete/extra"), now=NOW)

    assert wrong_method.status_code == 404
    assert wrong_path.status_code == 404
    assert tenant_deletion.calls == []


def test_tenant_delete_http_wiring_fails_closed_when_service_denies() -> None:
    denied = _TenantDeletion(fail=True)
    runtime, tenant_deletion = _runtime(tenant_deletion=denied)
    response = runtime.handle(_request(), now=NOW)

    assert response.status_code == 409
    assert response.body == {"error": "TENANT_DELETE_DENIED"}
    assert tenant_deletion.calls == []


def test_tenant_delete_http_wiring_requires_bound_authority() -> None:
    runtime, tenant_deletion = _runtime(bind_tenant_deletion=False)
    response = runtime.handle(_request(), now=NOW)

    assert response.status_code == 404
    assert response.body == {"error": "LIFECYCLE_ROUTE_NOT_WIRED"}
    assert tenant_deletion.calls == []
