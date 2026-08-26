from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
import requests

from services.account_unlink_github import GitHubAccountUnlinkService
from services.central_identity import (
    CanonicalAccount,
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
    GitHubOAuthError,
    GitHubOAuthService,
)

NOW = datetime(2026, 8, 26, 14, 0, tzinfo=timezone.utc)
REDIRECT = "https://app.ilaios.com/auth/github/unlink/callback"


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


class _UnlinkAuthority:
    def __init__(self) -> None:
        self.calls: list[
            tuple[str, str, VerifiedExternalIdentity, VerifiedExternalIdentity]
        ] = []

    def unlink_identity(
        self,
        *,
        authenticated_user_id: str,
        authenticated_tenant_id: str,
        identity: VerifiedExternalIdentity,
        reauthenticated_identity: VerifiedExternalIdentity,
    ) -> IdentityLink:
        self.calls.append(
            (
                authenticated_user_id,
                authenticated_tenant_id,
                identity,
                reauthenticated_identity,
            )
        )
        if identity.key() == reauthenticated_identity.key():
            raise CentralIdentityError(
                "unlink requires a different re-authenticated identity"
            )
        return IdentityLink(
            provider=identity.provider,
            subject=identity.subject,
            user_id=authenticated_user_id,
            tenant_id=authenticated_tenant_id,
            verified_email=identity.email if identity.email_verified else None,
            issuer=identity.issuer,
        )


def _store() -> tuple[InMemoryCentralIdentityStore, CanonicalAccount]:
    store = InMemoryCentralIdentityStore()
    google = VerifiedExternalIdentity(
        provider=IdentityProvider.GOOGLE,
        subject="google-target-immutable",
        email="user@example.com",
        email_verified=True,
    )
    account = store.create_account_with_link(google)
    store.add_link(
        account,
        VerifiedExternalIdentity(
            provider=IdentityProvider.GITHUB,
            subject="98952443",
            email="primary@example.com",
            email_verified=True,
        ),
    )
    return store, account


def _service(
    *,
    session: _Session | None = None,
) -> tuple[
    GitHubAccountUnlinkService,
    _Session,
    _UnlinkAuthority,
    CanonicalAccount,
]:
    store, account = _store()
    provider_session = session or _Session()
    unlink = _UnlinkAuthority()
    service = GitHubAccountUnlinkService(
        github_oauth=GitHubOAuthService(
            _environment(),
            request_session=provider_session,
        ),
        identity_store=store,
        account_unlink=unlink,
    )
    return service, provider_session, unlink, account


def _google_reference(service: GitHubAccountUnlinkService, account: CanonicalAccount) -> str:
    targets = service.prepare_targets(
        authenticated_user_id=account.user_id,
        authenticated_tenant_id=account.tenant_id,
        now=NOW,
    )
    google_targets = [
        target for target in targets if target.provider is IdentityProvider.GOOGLE
    ]
    assert len(google_targets) == 1
    target = google_targets[0]
    assert not hasattr(target, "subject")
    assert not hasattr(target, "email")
    return target.reference


def test_unlink_uses_opaque_target_and_server_verified_distinct_github_identity() -> None:
    service, _, unlink, account = _service()
    reference = _google_reference(service, account)

    start = service.start(
        target_reference=reference,
        authenticated_user_id=account.user_id,
        authenticated_tenant_id=account.tenant_id,
        recent_authentication_verified=True,
        redirect_uri=REDIRECT,
        now=NOW,
    )
    result = service.complete(
        state=start.state,
        code="oauth-code",
        authenticated_user_id=account.user_id,
        authenticated_tenant_id=account.tenant_id,
        recent_authentication_verified=True,
        now=NOW,
    )

    assert result.status == "unlinked"
    assert result.provider is IdentityProvider.GOOGLE
    assert len(unlink.calls) == 1
    user_id, tenant_id, target, reauth = unlink.calls[0]
    assert (user_id, tenant_id) == (account.user_id, account.tenant_id)
    assert target.key() == (IdentityProvider.GOOGLE, "", "google-target-immutable")
    assert reauth.key() == (IdentityProvider.GITHUB, "", "98952443")


def test_target_reference_is_single_use_and_bound_to_canonical_account() -> None:
    service, provider_session, _, account = _service()
    reference = _google_reference(service, account)

    with pytest.raises(CentralIdentityError, match="another canonical account"):
        service.start(
            target_reference=reference,
            authenticated_user_id=account.user_id,
            authenticated_tenant_id="tenant-other",
            recent_authentication_verified=True,
            redirect_uri=REDIRECT,
            now=NOW,
        )

    assert provider_session.provider_calls == 0
    with pytest.raises(CentralIdentityError, match="invalid or expired"):
        service.start(
            target_reference=reference,
            authenticated_user_id=account.user_id,
            authenticated_tenant_id=account.tenant_id,
            recent_authentication_verified=True,
            redirect_uri=REDIRECT,
            now=NOW,
        )


def test_recent_auth_is_required_before_start_and_complete() -> None:
    service, provider_session, _, account = _service()
    reference = _google_reference(service, account)

    with pytest.raises(CentralIdentityError, match="recent authentication"):
        service.start(
            target_reference=reference,
            authenticated_user_id=account.user_id,
            authenticated_tenant_id=account.tenant_id,
            recent_authentication_verified=False,
            redirect_uri=REDIRECT,
            now=NOW,
        )
    assert provider_session.provider_calls == 0

    reference = _google_reference(service, account)
    start = service.start(
        target_reference=reference,
        authenticated_user_id=account.user_id,
        authenticated_tenant_id=account.tenant_id,
        recent_authentication_verified=True,
        redirect_uri=REDIRECT,
        now=NOW,
    )
    with pytest.raises(CentralIdentityError, match="recent authentication"):
        service.complete(
            state=start.state,
            code="oauth-code",
            authenticated_user_id=account.user_id,
            authenticated_tenant_id=account.tenant_id,
            recent_authentication_verified=False,
            now=NOW,
        )
    assert provider_session.provider_calls == 0


def test_pending_state_is_account_bound_one_use_and_expires_before_provider_call() -> None:
    service, provider_session, _, account = _service()
    reference = _google_reference(service, account)
    start = service.start(
        target_reference=reference,
        authenticated_user_id=account.user_id,
        authenticated_tenant_id=account.tenant_id,
        recent_authentication_verified=True,
        redirect_uri=REDIRECT,
        now=NOW,
    )

    with pytest.raises(CentralIdentityError, match="another account"):
        service.complete(
            state=start.state,
            code="oauth-code",
            authenticated_user_id=account.user_id,
            authenticated_tenant_id="tenant-other",
            recent_authentication_verified=True,
            now=NOW,
        )
    assert provider_session.provider_calls == 0

    with pytest.raises(CentralIdentityError, match="invalid or expired"):
        service.complete(
            state=start.state,
            code="oauth-code",
            authenticated_user_id=account.user_id,
            authenticated_tenant_id=account.tenant_id,
            recent_authentication_verified=True,
            now=NOW,
        )

    reference = _google_reference(service, account)
    expired_start = service.start(
        target_reference=reference,
        authenticated_user_id=account.user_id,
        authenticated_tenant_id=account.tenant_id,
        recent_authentication_verified=True,
        redirect_uri=REDIRECT,
        now=NOW,
    )
    with pytest.raises(CentralIdentityError, match="invalid or expired"):
        service.complete(
            state=expired_start.state,
            code="oauth-code",
            authenticated_user_id=account.user_id,
            authenticated_tenant_id=account.tenant_id,
            recent_authentication_verified=True,
            now=NOW + timedelta(minutes=6),
        )
    assert provider_session.provider_calls == 0


def test_same_github_identity_reauth_is_denied_by_canonical_unlink_authority() -> None:
    service, _, unlink, account = _service()
    targets = service.prepare_targets(
        authenticated_user_id=account.user_id,
        authenticated_tenant_id=account.tenant_id,
        now=NOW,
    )
    github_reference = next(
        target.reference
        for target in targets
        if target.provider is IdentityProvider.GITHUB
    )
    start = service.start(
        target_reference=github_reference,
        authenticated_user_id=account.user_id,
        authenticated_tenant_id=account.tenant_id,
        recent_authentication_verified=True,
        redirect_uri=REDIRECT,
        now=NOW,
    )

    with pytest.raises(CentralIdentityError, match="different re-authenticated identity"):
        service.complete(
            state=start.state,
            code="oauth-code",
            authenticated_user_id=account.user_id,
            authenticated_tenant_id=account.tenant_id,
            recent_authentication_verified=True,
            now=NOW,
        )
    assert len(unlink.calls) == 1


def test_invalid_github_immutable_id_never_reaches_unlink_authority() -> None:
    service, _, unlink, account = _service(session=_Session(github_user_id="98952443"))
    reference = _google_reference(service, account)
    start = service.start(
        target_reference=reference,
        authenticated_user_id=account.user_id,
        authenticated_tenant_id=account.tenant_id,
        recent_authentication_verified=True,
        redirect_uri=REDIRECT,
        now=NOW,
    )

    with pytest.raises(GitHubOAuthError, match="invalid immutable user ID"):
        service.complete(
            state=start.state,
            code="oauth-code",
            authenticated_user_id=account.user_id,
            authenticated_tenant_id=account.tenant_id,
            recent_authentication_verified=True,
            now=NOW,
        )
    assert unlink.calls == []
