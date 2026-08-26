from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
import requests

from services.account_recovery_github import GitHubAccountRecoveryService
from services.central_identity import (
    CanonicalAccount,
    CentralIdentityError,
    IdentityProvider,
    VerifiedExternalIdentity,
)
from services.github_oauth import (
    GITHUB_EMAILS_ENDPOINT,
    GITHUB_USER_ENDPOINT,
    GitHubOAuthEnvironment,
    GitHubOAuthError,
    GitHubOAuthService,
)

NOW = datetime(2026, 8, 26, 5, 0, tzinfo=timezone.utc)
REDIRECT = "https://app.ilaios.com/auth/github/callback"


def _environment() -> GitHubOAuthEnvironment:
    return GitHubOAuthEnvironment.from_environment(
        {
            "ILAIOS_GITHUB_PRODUCTION_CLIENT_ID": "github-prod-client",
            "ILAIOS_GITHUB_PRODUCTION_CLIENT_SECRET": "github-prod-secret",
            "ILAIOS_GITHUB_DEVELOPMENT_CLIENT_ID": "github-dev-client",
            "ILAIOS_GITHUB_DEVELOPMENT_CLIENT_SECRET": "github-dev-secret",
            "ILAIOS_GITHUB_PRODUCTION_REDIRECTS": REDIRECT,
        }
    )


class _Response:
    def __init__(self, payload: object, *, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def json(self) -> object:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"status={self.status_code}")


class _Session:
    def __init__(self, *, github_user_id: object = 98952443) -> None:
        self.github_user_id = github_user_id
        self.provider_calls = 0

    def post(self, url: str, *, data: object, headers: object, timeout: int) -> _Response:
        self.provider_calls += 1
        return _Response({"access_token": "provider-token", "token_type": "bearer"})

    def get(self, url: str, *, headers: object, timeout: int) -> _Response:
        self.provider_calls += 1
        if url == GITHUB_USER_ENDPOINT:
            return _Response({"id": self.github_user_id, "login": "mutable-login"})
        if url == GITHUB_EMAILS_ENDPOINT:
            return _Response(
                [{"email": "Primary@Example.com", "primary": True, "verified": True}]
            )
        raise AssertionError(f"unexpected GET {url}")


class _RecoveryAuthority:
    def __init__(self, *, enabled: bool = True, tenant_id: str = "tenant-1") -> None:
        self.enabled = enabled
        self.tenant_id = tenant_id
        self.identities: list[VerifiedExternalIdentity] = []

    def recover_existing_account(
        self, identity: VerifiedExternalIdentity
    ) -> CanonicalAccount:
        self.identities.append(identity)
        if identity.key() != (IdentityProvider.GITHUB, "", "98952443"):
            raise CentralIdentityError("recovery identity is not linked")
        if not self.enabled:
            raise CentralIdentityError("recovery account is unavailable")
        if self.tenant_id != "tenant-1":
            raise CentralIdentityError("recovery identity tenant mismatch")
        return CanonicalAccount(user_id="user-1", tenant_id="tenant-1")


def _service(
    *,
    session: _Session | None = None,
    recovery: _RecoveryAuthority | None = None,
) -> tuple[GitHubAccountRecoveryService, _Session, _RecoveryAuthority]:
    provider_session = session or _Session()
    recovery_authority = recovery or _RecoveryAuthority()
    github_oauth = GitHubOAuthService(
        _environment(),
        request_session=provider_session,
    )
    return (
        GitHubAccountRecoveryService(
            github_oauth=github_oauth,
            account_recovery=recovery_authority,
        ),
        provider_session,
        recovery_authority,
    )


def test_recovery_uses_server_verified_immutable_github_identity() -> None:
    service, _, recovery = _service()
    start = service.start(REDIRECT, NOW)
    result = service.complete(state=start.state, code="oauth-code", now=NOW)

    assert result.status == "recovered"
    assert result.user_id == "user-1"
    assert result.tenant_id == "tenant-1"
    assert recovery.identities == [
        VerifiedExternalIdentity(
            provider=IdentityProvider.GITHUB,
            subject="98952443",
            email="primary@example.com",
            email_verified=True,
        )
    ]


def test_recovery_rejects_client_selected_or_invalid_provider_subject() -> None:
    service, _, recovery = _service(session=_Session(github_user_id="98952443"))
    start = service.start(REDIRECT, NOW)

    with pytest.raises(GitHubOAuthError, match="invalid immutable user ID"):
        service.complete(state=start.state, code="oauth-code", now=NOW)
    assert recovery.identities == []


def test_recovery_state_is_one_use_and_provider_proof_cannot_be_replayed() -> None:
    service, _, _ = _service()
    start = service.start(REDIRECT, NOW)
    service.complete(state=start.state, code="oauth-code", now=NOW)

    with pytest.raises(GitHubOAuthError, match="state is invalid or expired"):
        service.complete(state=start.state, code="replayed-code", now=NOW)


def test_recovery_expired_state_fails_before_provider_or_account_lookup() -> None:
    service, provider_session, recovery = _service()
    start = service.start(REDIRECT, NOW)

    with pytest.raises(GitHubOAuthError, match="state is invalid or expired"):
        service.complete(
            state=start.state,
            code="oauth-code",
            now=NOW + timedelta(minutes=6),
        )
    assert provider_session.provider_calls == 0
    assert recovery.identities == []


def test_recovery_propagates_unknown_disabled_and_cross_tenant_denials() -> None:
    unknown_service, _, unknown = _service(session=_Session(github_user_id=42))
    unknown_start = unknown_service.start(REDIRECT, NOW)
    with pytest.raises(CentralIdentityError, match="not linked"):
        unknown_service.complete(state=unknown_start.state, code="oauth-code", now=NOW)
    assert unknown.identities[0].subject == "42"

    disabled_service, _, _ = _service(recovery=_RecoveryAuthority(enabled=False))
    disabled_start = disabled_service.start(REDIRECT, NOW)
    with pytest.raises(CentralIdentityError, match="unavailable"):
        disabled_service.complete(state=disabled_start.state, code="oauth-code", now=NOW)

    tenant_service, _, _ = _service(recovery=_RecoveryAuthority(tenant_id="tenant-2"))
    tenant_start = tenant_service.start(REDIRECT, NOW)
    with pytest.raises(CentralIdentityError, match="tenant mismatch"):
        tenant_service.complete(state=tenant_start.state, code="oauth-code", now=NOW)
