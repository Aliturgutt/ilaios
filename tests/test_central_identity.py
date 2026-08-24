from __future__ import annotations

import pytest

from services.central_identity import (
    CentralIdentityError,
    CentralIdentityService,
    IdentityProvider,
    InMemoryCentralIdentityStore,
    VerifiedExternalIdentity,
)

MICROSOFT_TEST_ISSUER = "https://login.microsoftonline.com/test-tenant/v2.0"


def _identity(
    provider: IdentityProvider,
    subject: str,
    *,
    email: str | None = None,
    verified: bool = False,
    issuer: str | None = None,
) -> VerifiedExternalIdentity:
    return VerifiedExternalIdentity(
        provider=provider,
        subject=subject,
        email=email,
        email_verified=verified,
        issuer=issuer,
    )


def _link(
    service: CentralIdentityService,
    *,
    user_id: str,
    tenant_id: str,
    identity: VerifiedExternalIdentity,
) -> None:
    service.link_identity(
        authenticated_user_id=user_id,
        authenticated_tenant_id=tenant_id,
        identity=identity,
        recent_authentication_verified=True,
    )


def test_repeated_provider_login_returns_same_canonical_account() -> None:
    service = CentralIdentityService(InMemoryCentralIdentityStore())
    first = service.sign_in(_identity(IdentityProvider.GOOGLE, "google-sub-1", email="User@Example.com", verified=True))
    second = service.sign_in(_identity(IdentityProvider.GOOGLE, "google-sub-1", email="user@example.com", verified=True))
    assert second == first


def test_authenticated_account_can_link_microsoft_github_and_email() -> None:
    service = CentralIdentityService(InMemoryCentralIdentityStore())
    account = service.sign_in(_identity(IdentityProvider.GOOGLE, "google-sub-1"))
    _link(service, user_id=account.user_id, tenant_id=account.tenant_id, identity=_identity(IdentityProvider.MICROSOFT, "ms-sub-1", issuer=MICROSOFT_TEST_ISSUER))
    _link(service, user_id=account.user_id, tenant_id=account.tenant_id, identity=_identity(IdentityProvider.GITHUB, "gh-user-1"))
    _link(service, user_id=account.user_id, tenant_id=account.tenant_id, identity=_identity(IdentityProvider.EMAIL, "User@Example.com", email="user@example.com", verified=True))
    providers = {link.provider for link in service.linked_identities(account.user_id)}
    assert providers == {IdentityProvider.EMAIL, IdentityProvider.GITHUB, IdentityProvider.GOOGLE, IdentityProvider.MICROSOFT}


def test_same_verified_email_does_not_automatically_merge_accounts() -> None:
    service = CentralIdentityService(InMemoryCentralIdentityStore())
    google_account = service.sign_in(_identity(IdentityProvider.GOOGLE, "google-sub-1", email="person@example.com", verified=True))
    github_account = service.sign_in(_identity(IdentityProvider.GITHUB, "github-sub-1", email="person@example.com", verified=True))
    assert github_account.user_id != google_account.user_id
    assert github_account.tenant_id != google_account.tenant_id


def test_identity_linked_to_another_account_is_rejected() -> None:
    service = CentralIdentityService(InMemoryCentralIdentityStore())
    first = service.sign_in(_identity(IdentityProvider.GOOGLE, "google-sub-1"))
    second = service.sign_in(_identity(IdentityProvider.GOOGLE, "google-sub-2"))
    _link(service, user_id=first.user_id, tenant_id=first.tenant_id, identity=_identity(IdentityProvider.GITHUB, "github-sub-1"))
    with pytest.raises(CentralIdentityError, match="already linked to another account"):
        _link(service, user_id=second.user_id, tenant_id=second.tenant_id, identity=_identity(IdentityProvider.GITHUB, "github-sub-1"))


def test_cross_tenant_link_attempt_is_rejected() -> None:
    service = CentralIdentityService(InMemoryCentralIdentityStore())
    account = service.sign_in(_identity(IdentityProvider.GOOGLE, "google-sub-1"))
    with pytest.raises(CentralIdentityError, match="authenticated tenant mismatch"):
        _link(service, user_id=account.user_id, tenant_id="tnt_other", identity=_identity(IdentityProvider.MICROSOFT, "ms-sub-1", issuer=MICROSOFT_TEST_ISSUER))


def test_email_sign_in_requires_verified_email() -> None:
    service = CentralIdentityService(InMemoryCentralIdentityStore())
    with pytest.raises(CentralIdentityError, match="requires verified email"):
        service.sign_in(_identity(IdentityProvider.EMAIL, "person@example.com", email="person@example.com", verified=False))


def test_email_subject_must_match_verified_email() -> None:
    service = CentralIdentityService(InMemoryCentralIdentityStore())
    with pytest.raises(CentralIdentityError, match="subject must equal"):
        service.sign_in(_identity(IdentityProvider.EMAIL, "attacker@example.com", email="person@example.com", verified=True))


def test_account_linking_is_idempotent_for_same_user() -> None:
    service = CentralIdentityService(InMemoryCentralIdentityStore())
    account = service.sign_in(_identity(IdentityProvider.GOOGLE, "google-sub-1"))
    external = _identity(IdentityProvider.APPLE, "apple-sub-1")
    service.link_identity(authenticated_user_id=account.user_id, authenticated_tenant_id=account.tenant_id, identity=external, recent_authentication_verified=True)
    first = service.linked_identities(account.user_id)[0:]
    service.link_identity(authenticated_user_id=account.user_id, authenticated_tenant_id=account.tenant_id, identity=external, recent_authentication_verified=True)
    second = service.linked_identities(account.user_id)[0:]
    assert second == first


def test_sensitive_link_requires_recent_authentication() -> None:
    service = CentralIdentityService(InMemoryCentralIdentityStore())
    account = service.sign_in(_identity(IdentityProvider.GOOGLE, "google-sub-1"))
    with pytest.raises(CentralIdentityError, match="recent authentication is required"):
        service.link_identity(
            authenticated_user_id=account.user_id,
            authenticated_tenant_id=account.tenant_id,
            identity=_identity(IdentityProvider.GITHUB, "gh-user-1"),
            recent_authentication_verified=False,
        )


def test_unlink_requires_recent_auth_and_preserves_last_sign_in_method() -> None:
    service = CentralIdentityService(InMemoryCentralIdentityStore())
    account = service.sign_in(_identity(IdentityProvider.GOOGLE, "google-sub-1"))
    github = _identity(IdentityProvider.GITHUB, "gh-user-1")
    _link(service, user_id=account.user_id, tenant_id=account.tenant_id, identity=github)
    with pytest.raises(CentralIdentityError, match="recent authentication is required"):
        service.unlink_identity(
            authenticated_user_id=account.user_id,
            authenticated_tenant_id=account.tenant_id,
            identity=github,
            recent_authentication_verified=False,
        )
    removed = service.unlink_identity(
        authenticated_user_id=account.user_id,
        authenticated_tenant_id=account.tenant_id,
        identity=github,
        recent_authentication_verified=True,
    )
    assert removed.provider is IdentityProvider.GITHUB
    with pytest.raises(CentralIdentityError, match="last usable sign-in method"):
        service.unlink_identity(
            authenticated_user_id=account.user_id,
            authenticated_tenant_id=account.tenant_id,
            identity=_identity(IdentityProvider.GOOGLE, "google-sub-1"),
            recent_authentication_verified=True,
        )


def test_cross_tenant_unlink_takeover_is_rejected() -> None:
    service = CentralIdentityService(InMemoryCentralIdentityStore())
    first = service.sign_in(_identity(IdentityProvider.GOOGLE, "google-sub-1"))
    second = service.sign_in(_identity(IdentityProvider.GOOGLE, "google-sub-2"))
    github = _identity(IdentityProvider.GITHUB, "gh-user-1")
    _link(service, user_id=first.user_id, tenant_id=first.tenant_id, identity=github)
    with pytest.raises(CentralIdentityError, match="belongs to another account"):
        service.unlink_identity(
            authenticated_user_id=second.user_id,
            authenticated_tenant_id=second.tenant_id,
            identity=github,
            recent_authentication_verified=True,
        )


def test_enterprise_oidc_requires_verified_issuer_namespace() -> None:
    service = CentralIdentityService(InMemoryCentralIdentityStore())
    with pytest.raises(CentralIdentityError, match="requires issuer"):
        service.sign_in(_identity(IdentityProvider.ENTERPRISE_OIDC, "shared-subject"))


def test_enterprise_oidc_same_subject_from_different_issuers_is_distinct() -> None:
    service = CentralIdentityService(InMemoryCentralIdentityStore())
    first = service.sign_in(_identity(IdentityProvider.ENTERPRISE_OIDC, "shared-subject", issuer="https://idp-a.example.com"))
    second = service.sign_in(_identity(IdentityProvider.ENTERPRISE_OIDC, "shared-subject", issuer="https://idp-b.example.com"))
    repeated = service.sign_in(_identity(IdentityProvider.ENTERPRISE_OIDC, "shared-subject", issuer="https://idp-a.example.com"))
    assert first.user_id != second.user_id
    assert first.tenant_id != second.tenant_id
    assert repeated == first
