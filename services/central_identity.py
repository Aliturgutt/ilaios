"""Central commercial identity account-linking boundary.

This module keeps external sign-in providers separate from the canonical ILAIOS
user/tenant identity. Provider adapters must cryptographically verify their own
credentials before constructing ``VerifiedExternalIdentity``.

Security properties:
- provider identities are keyed by provider + immutable provider subject;
- verified email is display/recovery metadata, never an automatic merge key;
- account linking requires an already authenticated canonical user/tenant;
- identities already linked to another user fail closed;
- supported provider types are explicit and provider-neutral at the core.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol


class CentralIdentityError(PermissionError):
    """Central identity resolution or linking failed closed."""


class IdentityProvider(str, Enum):
    GOOGLE = "google"
    MICROSOFT = "microsoft"
    GITHUB = "github"
    APPLE = "apple"
    EMAIL = "email"
    ENTERPRISE_OIDC = "enterprise_oidc"


@dataclass(frozen=True, slots=True)
class VerifiedExternalIdentity:
    """Identity produced only after provider-side verification succeeds."""

    provider: IdentityProvider
    subject: str
    email: str | None = None
    email_verified: bool = False
    issuer: str | None = None

    def normalized(self) -> VerifiedExternalIdentity:
        subject = self.subject.strip()
        if not subject:
            raise CentralIdentityError("provider subject is required")
        email = self.email.strip().casefold() if self.email is not None else None
        if email == "":
            email = None
        if self.provider is IdentityProvider.EMAIL:
            if email is None or not self.email_verified:
                raise CentralIdentityError("email sign-in requires verified email")
            if subject.casefold() != email:
                raise CentralIdentityError(
                    "email provider subject must equal the verified email"
                )
            subject = email
        return VerifiedExternalIdentity(
            provider=self.provider,
            subject=subject,
            email=email,
            email_verified=self.email_verified,
            issuer=self.issuer.strip() if self.issuer else None,
        )


@dataclass(frozen=True, slots=True)
class CanonicalAccount:
    user_id: str
    tenant_id: str
    enabled: bool = True


@dataclass(frozen=True, slots=True)
class IdentityLink:
    provider: IdentityProvider
    subject: str
    user_id: str
    tenant_id: str
    verified_email: str | None = None
    issuer: str | None = None


class CentralIdentityStore(Protocol):
    """Persistence boundary; production adapters must enforce atomic uniqueness."""

    def find_link(
        self, provider: IdentityProvider, subject: str
    ) -> IdentityLink | None: ...

    def get_account(self, user_id: str) -> CanonicalAccount | None: ...

    def create_account_with_link(
        self, identity: VerifiedExternalIdentity
    ) -> CanonicalAccount: ...

    def add_link(
        self, account: CanonicalAccount, identity: VerifiedExternalIdentity
    ) -> IdentityLink: ...

    def list_links(self, user_id: str) -> tuple[IdentityLink, ...]: ...


class CentralIdentityService:
    """Resolve every client/provider into one canonical user + tenant identity."""

    def __init__(self, store: CentralIdentityStore) -> None:
        self._store = store

    def sign_in(self, identity: VerifiedExternalIdentity) -> CanonicalAccount:
        verified = identity.normalized()
        existing = self._store.find_link(verified.provider, verified.subject)
        if existing is None:
            return self._store.create_account_with_link(verified)
        account = self._store.get_account(existing.user_id)
        if account is None:
            raise CentralIdentityError("identity link references missing account")
        if account.tenant_id != existing.tenant_id:
            raise CentralIdentityError("identity link tenant mismatch")
        if not account.enabled:
            raise CentralIdentityError("account is disabled")
        return account

    def link_identity(
        self,
        *,
        authenticated_user_id: str,
        authenticated_tenant_id: str,
        identity: VerifiedExternalIdentity,
    ) -> IdentityLink:
        """Link a new provider only from an already authenticated account."""

        user_id = authenticated_user_id.strip()
        tenant_id = authenticated_tenant_id.strip()
        if not user_id or not tenant_id:
            raise CentralIdentityError("authenticated user and tenant are required")
        account = self._store.get_account(user_id)
        if account is None or not account.enabled:
            raise CentralIdentityError("authenticated account is unavailable")
        if account.tenant_id != tenant_id:
            raise CentralIdentityError("authenticated tenant mismatch")

        verified = identity.normalized()
        existing = self._store.find_link(verified.provider, verified.subject)
        if existing is not None:
            if existing.user_id != user_id or existing.tenant_id != tenant_id:
                raise CentralIdentityError(
                    "external identity is already linked to another account"
                )
            return existing
        return self._store.add_link(account, verified)

    def linked_identities(self, user_id: str) -> tuple[IdentityLink, ...]:
        account = self._store.get_account(user_id.strip())
        if account is None or not account.enabled:
            raise CentralIdentityError("account is unavailable")
        return self._store.list_links(account.user_id)


class InMemoryCentralIdentityStore:
    """Deterministic reference store for tests and local integration only."""

    def __init__(self) -> None:
        self._accounts: dict[str, CanonicalAccount] = {}
        self._links: dict[tuple[IdentityProvider, str], IdentityLink] = {}
        self._next_account = 1

    def find_link(
        self, provider: IdentityProvider, subject: str
    ) -> IdentityLink | None:
        return self._links.get((provider, subject))

    def get_account(self, user_id: str) -> CanonicalAccount | None:
        return self._accounts.get(user_id)

    def create_account_with_link(
        self, identity: VerifiedExternalIdentity
    ) -> CanonicalAccount:
        key = (identity.provider, identity.subject)
        if key in self._links:
            raise CentralIdentityError("external identity is already linked")
        sequence = self._next_account
        self._next_account += 1
        account = CanonicalAccount(
            user_id=f"usr_{sequence:08d}", tenant_id=f"tnt_{sequence:08d}"
        )
        self._accounts[account.user_id] = account
        self._links[key] = _link_for(account, identity)
        return account

    def add_link(
        self, account: CanonicalAccount, identity: VerifiedExternalIdentity
    ) -> IdentityLink:
        key = (identity.provider, identity.subject)
        if key in self._links:
            raise CentralIdentityError("external identity is already linked")
        stored = self._accounts.get(account.user_id)
        if stored != account:
            raise CentralIdentityError("canonical account changed during linking")
        link = _link_for(account, identity)
        self._links[key] = link
        return link

    def list_links(self, user_id: str) -> tuple[IdentityLink, ...]:
        return tuple(
            sorted(
                (link for link in self._links.values() if link.user_id == user_id),
                key=lambda link: (link.provider.value, link.subject),
            )
        )


def _link_for(
    account: CanonicalAccount, identity: VerifiedExternalIdentity
) -> IdentityLink:
    return IdentityLink(
        provider=identity.provider,
        subject=identity.subject,
        user_id=account.user_id,
        tenant_id=account.tenant_id,
        verified_email=identity.email if identity.email_verified else None,
        issuer=identity.issuer,
    )
