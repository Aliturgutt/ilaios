from __future__ import annotations

from datetime import datetime, timezone

import pytest

from services.account_unlink_github import (
    CentralIdentityOwnedReferenceResolver,
    GitHubAccountUnlinkService,
    identity_link_reference_sha256,
)
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
    def __init__(self, payload: object) -> None:
        self._payload = payload

    def json(self) -> object:
        return self._payload

    def raise_for_status(self) -> None:
        return None


class _Session:
    def __init__(self, *, github_user_id: int = 98952443) -> None:
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
                [{"email": "Github@Example.com", "primary": True, "verified": True}]
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
            raise CentralIdentityError("unlink requires a different re-authenticated identity")
        return IdentityLink(
            provider=identity.provider,
            subject=identity.subject,
            user_id=authenticated_user_id,
            tenant_id=authenticated_tenant_id,
            verified_email=identity.email,
            issuer=identity.issuer,
        )


def _target_identity() -> VerifiedExternalIdentity:
    return VerifiedExternalIdentity(
        provider=IdentityProvider.GOOGLE,
        subject="google-subject-1",
        email="owner@example.com",
        email_verified=True,
    )


def _github_identity() -> VerifiedExternalIdentity:
    return VerifiedExternalIdentity(
        provider=IdentityProvider.GITHUB,
        subject="98952443",
        email="github@example.com",
        email_verified=True,
    )


def _service() -> tuple[
    GitHubAccountUnlinkService,
    _Session,
    _UnlinkAuthority,
    InMemoryCentralIdentityStore,
    IdentityLink,
]:
    store = InMemoryCentralIdentityStore()
    target = _target_identity()
    account = store.create_account_with_link(target)
    target_link = store.find_link(target)
    assert target_link is not None
    store.add_link(account, _github_identity())

    provider_session = _Session()
    unlink_authority = _UnlinkAuthority()
    github_oauth = GitHubOAuthService(
        _environment(),
        request_session=provider_session,
    )
    service = GitHubAccountUnlinkService(
        github_oauth=github_oauth,
        reference_resolver=CentralIdentityOwnedReferenceResolver(store),
        account_unlink=unlink_authority,
    )
    return service, provider_session, unlink_authority, store, target_link


def test_unlink_uses_owned_opaque_target_reference_and_verified_github_reauth() -> None:
    service, _, unlink_authority, _, target_link = _service()
    start = service.start(REDIRECT, NOW)

    result = service.complete(
        authenticated_user_id=target_link.user_id,
        authenticated_tenant_id=target_link.tenant_id,
        target_identity_reference_sha256=identity_link_reference_sha256(target_link),
        state=start.state,
        code="oauth-code",
        now=NOW,
    )

    assert result.status == "unlinked"
    assert result.provider == "google"
    assert unlink_authority.calls == [
        (
            target_link.user_id,
            target_link.tenant_id,
            _target_identity(),
            _github_identity(),
        )
    ]


def test_unlink_rejects_malformed_target_reference_before_provider_call() -> None:
    service, provider_session, unlink_authority, _, target_link = _service()
    start = service.start(REDIRECT, NOW)

    with pytest.raises(CentralIdentityError, match="reference is invalid"):
        service.complete(
            authenticated_user_id=target_link.user_id,
            authenticated_tenant_id=target_link.tenant_id,
            target_identity_reference_sha256="not-a-digest",
            state=start.state,
            code="oauth-code",
            now=NOW,
        )

    assert provider_session.provider_calls == 0
    assert unlink_authority.calls == []


def test_unlink_denies_cross_account_target_reference_before_provider_call() -> None:
    service, provider_session, unlink_authority, store, target_link = _service()
    other_identity = VerifiedExternalIdentity(
        provider=IdentityProvider.GOOGLE,
        subject="other-google-subject",
    )
    store.create_account_with_link(other_identity)
    other_link = store.find_link(other_identity)
    assert other_link is not None
    start = service.start(REDIRECT, NOW)

    with pytest.raises(CentralIdentityError, match="not uniquely owned"):
        service.complete(
            authenticated_user_id=target_link.user_id,
            authenticated_tenant_id=target_link.tenant_id,
            target_identity_reference_sha256=identity_link_reference_sha256(other_link),
            state=start.state,
            code="oauth-code",
            now=NOW,
        )

    assert provider_session.provider_calls == 0
    assert unlink_authority.calls == []


def test_unlink_reauthentication_state_is_one_use() -> None:
    service, _, _, _, target_link = _service()
    reference = identity_link_reference_sha256(target_link)
    start = service.start(REDIRECT, NOW)
    service.complete(
        authenticated_user_id=target_link.user_id,
        authenticated_tenant_id=target_link.tenant_id,
        target_identity_reference_sha256=reference,
        state=start.state,
        code="oauth-code",
        now=NOW,
    )

    with pytest.raises(GitHubOAuthError, match="state is invalid or expired"):
        service.complete(
            authenticated_user_id=target_link.user_id,
            authenticated_tenant_id=target_link.tenant_id,
            target_identity_reference_sha256=reference,
            state=start.state,
            code="replayed-code",
            now=NOW,
        )


def test_unlink_rejects_same_identity_as_target_and_reauthentication() -> None:
    store = InMemoryCentralIdentityStore()
    github = _github_identity()
    account = store.create_account_with_link(github)
    email_identity = VerifiedExternalIdentity(
        provider=IdentityProvider.EMAIL,
        subject="recovery@example.com",
        email="recovery@example.com",
        email_verified=True,
    )
    store.add_link(account, email_identity)
    github_link = store.find_link(github)
    assert github_link is not None

    provider_session = _Session()
    unlink_authority = _UnlinkAuthority()
    service = GitHubAccountUnlinkService(
        github_oauth=GitHubOAuthService(_environment(), request_session=provider_session),
        reference_resolver=CentralIdentityOwnedReferenceResolver(store),
        account_unlink=unlink_authority,
    )
    start = service.start(REDIRECT, NOW)

    with pytest.raises(CentralIdentityError, match="different re-authenticated identity"):
        service.complete(
            authenticated_user_id=github_link.user_id,
            authenticated_tenant_id=github_link.tenant_id,
            target_identity_reference_sha256=identity_link_reference_sha256(github_link),
            state=start.state,
            code="oauth-code",
            now=NOW,
        )

    assert len(unlink_authority.calls) == 1
