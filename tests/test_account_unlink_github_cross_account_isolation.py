from __future__ import annotations

from datetime import datetime, timezone

import pytest
import requests

from services.account_unlink_github import GitHubAccountUnlinkService
from services.central_identity import (
    CentralIdentityError,
    IdentityLink,
    IdentityProvider,
    InMemoryCentralIdentityStore,
    VerifiedExternalIdentity,
)
from services.github_oauth import (
    GITHUB_EMAILS_ENDPOINT,
    GITHUB_USER_ENDPOINT,
    GitHubOAuthEnvironment,
    GitHubOAuthService,
)

NOW = datetime(2026, 8, 26, 17, 20, tzinfo=timezone.utc)
REDIRECT = "https://app.ilaios.com/auth/github/unlink/callback"


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
    def __init__(self) -> None:
        self.provider_calls = 0

    def post(self, url: str, *, data: object, headers: object, timeout: int) -> _Response:
        self.provider_calls += 1
        return _Response({"access_token": "provider-token", "token_type": "bearer"})

    def get(self, url: str, *, headers: object, timeout: int) -> _Response:
        self.provider_calls += 1
        if url == GITHUB_USER_ENDPOINT:
            return _Response({"id": 98952443, "login": "mutable-login"})
        if url == GITHUB_EMAILS_ENDPOINT:
            return _Response(
                [{"email": "owner@example.com", "primary": True, "verified": True}]
            )
        raise AssertionError(f"unexpected GET {url}")


class _UnlinkAuthority:
    def unlink_identity(
        self,
        *,
        authenticated_user_id: str,
        authenticated_tenant_id: str,
        identity: VerifiedExternalIdentity,
        reauthenticated_identity: VerifiedExternalIdentity,
    ) -> IdentityLink:
        return IdentityLink(
            provider=identity.provider,
            subject=identity.subject,
            user_id=authenticated_user_id,
            tenant_id=authenticated_tenant_id,
            verified_email=identity.email if identity.email_verified else None,
            issuer=identity.issuer,
        )


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


def test_cross_account_probe_cannot_consume_target_or_pending_state() -> None:
    store = InMemoryCentralIdentityStore()
    victim = store.create_account_with_link(
        VerifiedExternalIdentity(
            provider=IdentityProvider.GOOGLE,
            subject="victim-google",
            email="victim@example.com",
            email_verified=True,
        )
    )
    store.add_link(
        victim,
        VerifiedExternalIdentity(
            provider=IdentityProvider.GITHUB,
            subject="98952443",
            email="owner@example.com",
            email_verified=True,
        ),
    )
    attacker = store.create_account_with_link(
        VerifiedExternalIdentity(
            provider=IdentityProvider.GOOGLE,
            subject="attacker-google",
            email="attacker@example.com",
            email_verified=True,
        )
    )
    provider_session = _Session()
    service = GitHubAccountUnlinkService(
        github_oauth=GitHubOAuthService(
            _environment(),
            request_session=provider_session,
        ),
        identity_store=store,
        account_unlink=_UnlinkAuthority(),
    )

    target = next(
        item
        for item in service.prepare_targets(
            authenticated_user_id=victim.user_id,
            authenticated_tenant_id=victim.tenant_id,
            now=NOW,
        )
        if item.provider is IdentityProvider.GOOGLE
    )

    with pytest.raises(CentralIdentityError, match="another canonical account"):
        service.start(
            target_reference=target.reference,
            authenticated_user_id=attacker.user_id,
            authenticated_tenant_id=attacker.tenant_id,
            recent_authentication_verified=True,
            redirect_uri=REDIRECT,
            now=NOW,
        )
    assert provider_session.provider_calls == 0

    start = service.start(
        target_reference=target.reference,
        authenticated_user_id=victim.user_id,
        authenticated_tenant_id=victim.tenant_id,
        recent_authentication_verified=True,
        redirect_uri=REDIRECT,
        now=NOW,
    )

    with pytest.raises(CentralIdentityError, match="another account"):
        service.complete(
            state=start.state,
            code="oauth-code",
            authenticated_user_id=attacker.user_id,
            authenticated_tenant_id=attacker.tenant_id,
            recent_authentication_verified=True,
            now=NOW,
        )
    assert provider_session.provider_calls == 0

    result = service.complete(
        state=start.state,
        code="oauth-code",
        authenticated_user_id=victim.user_id,
        authenticated_tenant_id=victim.tenant_id,
        recent_authentication_verified=True,
        now=NOW,
    )
    assert result.status == "unlinked"
    assert result.provider is IdentityProvider.GOOGLE
    assert provider_session.provider_calls > 0
