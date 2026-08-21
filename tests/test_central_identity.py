from __future__ import annotations

import pytest

from services.central_identity import (
    CentralIdentityError,
    CentralIdentityService,
    IdentityProvider,
    InMemoryCentralIdentityStore,
    VerifiedExternalIdentity,
)


def _identity(
    provider: IdentityProvider,
    subject: str,
    *,
    email: str | None = None,
    verified: bool = False,
) -> VerifiedExternalIdentity:
    return VerifiedExternalIdentity(
        provider=provider,
        subject=subject,
        email=email,
        email_verified=verified,
    )


def test_repeated_provider_login_returns_same_canonical_account() -> None:
    service = CentralIdentityService(InMemoryCentralIdentityStore())

    first = service.sign_in(
        _identity(
            IdentityProvider.GOOGLE,
            "google-sub-1",
            email="User@Example.com",
            verified=True,
        )
    )
    second = service.sign_in(
        _identity(
            IdentityProvider.GOOGLE,
            "google-sub-1",
            email="user@example.com",
            verified=True,
        )
    )

    assert second == first


def test_authenticated_account_can_link_microsoft_github_and_email() -> None:
    service = CentralIdentityService(InMemoryCentralIdentityStore())
    account = service.sign_in(
        _identity(IdentityProvider.GOOGLE, "google-sub-1")
    )

    service.link_identity(
        authenticated_user_id=account.user_id,
        authenticated_tenant_id=account.tenant_id,
        identity=_identity(IdentityProvider.MICROSOFT, "ms-sub-1"),
    )
    service.link_identity(
        authenticated_user_id=account.user_id,
        authenticated_tenant_id=account.tenant_id,
        identity=_identity(IdentityProvider.GITHUB, "gh-user-1"),
    )
    service.link_identity(
        authenticated_user_id=account.user_id,
        authenticated_tenant_id=account.tenant_id,
        identity=_identity(
            IdentityProvider.EMAIL,
            "User@Example.com",
            email="user@example.com",
            verified=True,
        ),
    )

    providers = {link.provider for link in service.linked_identities(account.user_id)}
    assert providers == {
        IdentityProvider.EMAIL,
        IdentityProvider.GITHUB,
        IdentityProvider.GOOGLE,
        IdentityProvider.MICROSOFT,
    }


def test_same_verified_email_does_not_automatically_merge_accounts() -> None:
    service = CentralIdentityService(InMemoryCentralIdentityStore())

    google_account = service.sign_in(
        _identity(
            IdentityProvider.GOOGLE,
            "google-sub-1",
            email="person@example.com",
            verified=True,
        )
    )
    github_account = service.sign_in(
        _identity(
            IdentityProvider.GITHUB,
            "github-sub-1",
            email="person@example.com",
            verified=True,
        )
    )

    assert github_account.user_id != google_account.user_id
    assert github_account.tenant_id != google_account.tenant_id


def test_identity_linked_to_another_account_is_rejected() -> None:
    service = CentralIdentityService(InMemoryCentralIdentityStore())
    first = service.sign_in(_identity(IdentityProvider.GOOGLE, "google-sub-1"))
    second = service.sign_in(_identity(IdentityProvider.GOOGLE, "google-sub-2"))

    service.link_identity(
        authenticated_user_id=first.user_id,
        authenticated_tenant_id=first.tenant_id,
        identity=_identity(IdentityProvider.GITHUB, "github-sub-1"),
    )

    with pytest.raises(
        CentralIdentityError,
        match="already linked to another account",
    ):
        service.link_identity(
            authenticated_user_id=second.user_id,
            authenticated_tenant_id=second.tenant_id,
            identity=_identity(IdentityProvider.GITHUB, "github-sub-1"),
        )


def test_cross_tenant_link_attempt_is_rejected() -> None:
    service = CentralIdentityService(InMemoryCentralIdentityStore())
    account = service.sign_in(_identity(IdentityProvider.GOOGLE, "google-sub-1"))

    with pytest.raises(CentralIdentityError, match="authenticated tenant mismatch"):
        service.link_identity(
            authenticated_user_id=account.user_id,
            authenticated_tenant_id="tnt_other",
            identity=_identity(IdentityProvider.MICROSOFT, "ms-sub-1"),
        )


def test_email_sign_in_requires_verified_email() -> None:
    service = CentralIdentityService(InMemoryCentralIdentityStore())

    with pytest.raises(CentralIdentityError, match="requires verified email"):
        service.sign_in(
            _identity(
                IdentityProvider.EMAIL,
                "person@example.com",
                email="person@example.com",
                verified=False,
            )
        )


def test_email_subject_must_match_verified_email() -> None:
    service = CentralIdentityService(InMemoryCentralIdentityStore())

    with pytest.raises(CentralIdentityError, match="subject must equal"):
        service.sign_in(
            _identity(
                IdentityProvider.EMAIL,
                "attacker@example.com",
                email="person@example.com",
                verified=True,
            )
        )


def test_account_linking_is_idempotent_for_same_user() -> None:
    service = CentralIdentityService(InMemoryCentralIdentityStore())
    account = service.sign_in(_identity(IdentityProvider.GOOGLE, "google-sub-1"))
    external = _identity(IdentityProvider.APPLE, "apple-sub-1")

    first = service.link_identity(
        authenticated_user_id=account.user_id,
        authenticated_tenant_id=account.tenant_id,
        identity=external,
    )
    second = service.link_identity(
        authenticated_user_id=account.user_id,
        authenticated_tenant_id=account.tenant_id,
        identity=external,
    )

    assert second == first
