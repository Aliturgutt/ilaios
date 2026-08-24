"""Central commercial identity account-linking boundary.

This module keeps external sign-in providers separate from the canonical ILAIOS
user/tenant identity. Provider adapters must cryptographically verify their own
credentials before constructing ``VerifiedExternalIdentity``.

Security properties:
- provider identities are keyed by provider + immutable provider subject;
- enterprise OIDC and Microsoft OIDC subjects are additionally namespaced by verified issuer;
- verified email is display/recovery metadata, never an automatic merge key;
- account linking/unlinking requires an already authenticated canonical user/tenant;
- sensitive linking/unlinking requires recent-authentication proof from the caller;
- identities already linked to another user fail closed;
- removing the final usable sign-in method fails closed;
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
        issuer = self.issuer.strip() if self.issuer else None
        if self.provider is IdentityProvider.EMAIL:
            if email is None or not self.email_verified:
                raise CentralIdentityError("email sign-in requires verified email")
            if subject.casefold() != email:
                raise CentralIdentityError(
                    "email provider subject must equal the verified email"
                )
            subject = email
        if self.provider in {
            IdentityProvider.ENTERPRISE_OIDC,
            IdentityProvider.MICROSOFT,
        } and issuer is None:
            raise CentralIdentityError(
                f"{self.provider.value} identity requires issuer namespace"
            )
        return VerifiedExternalIdentity(
            provider=self.provider,
            subject=subject,
            email=email,
            email_verified=self.email_verified,
            issuer=issuer,
        )

    def key(self) -> tuple[IdentityProvider, str, str]:
        normalized = self.normalized()
        namespace = (
            normalized.issuer or ""
            if normalized.provider
            in {IdentityProvider.ENTERPRISE_OIDC, IdentityProvider.MICROSOFT}
            else ""
        )
        return (normalized.provider, namespace, normalized.subject)


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

    def find_link(self, identity: VerifiedExternalIdentity) -> IdentityLink | None: ...

    def get_account(self, user_id: str) -> CanonicalAccount | None: ...

    def create_account_with_link(
        self, identity: VerifiedExternalIdentity
    ) -> CanonicalAccount: ...

    def add_link(
        self, account: CanonicalAccount, identity: VerifiedExternalIdentity
    ) -> IdentityLink: ...

    def remove_link(
        self, account: CanonicalAccount, identity: VerifiedExternalIdentity
    ) -> IdentityLink: ...

    def list_links(self, user_id: str) -> tuple[IdentityLink, ...]: ...


class CentralIdentityService:
    """Resolve every client/provider into one canonical user + tenant identity."""

    def __init__(self, store: CentralIdentityStore) -> None:
        self._store = store

    def sign_in(self, identity: VerifiedExternalIdentity) -> CanonicalAccount:
        verified = identity.normalized()
        existing = self._store.find_link(verified)
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
        recent_authentication_verified: bool,
    ) -> IdentityLink:
        """Link a new provider only after recent authentication of the account."""

        account = self._require_authenticated_account(
            authenticated_user_id=authenticated_user_id,
            authenticated_tenant_id=authenticated_tenant_id,
            recent_authentication_verified=recent_authentication_verified,
        )
        verified = identity.normalized()
        existing = self._store.find_link(verified)
        if existing is not None:
            if existing.user_id != account.user_id or existing.tenant_id != account.tenant_id:
                raise CentralIdentityError(
                    "external identity is already linked to another account"
                )
            return existing
        return self._store.add_link(account, verified)

    def unlink_identity(
        self,
        *,
        authenticated_user_id: str,
        authenticated_tenant_id: str,
        identity: VerifiedExternalIdentity,
        recent_authentication_verified: bool,
    ) -> IdentityLink:
        """Remove one verified provider link while preserving a recovery path."""

        account = self._require_authenticated_account(
            authenticated_user_id=authenticated_user_id,
            authenticated_tenant_id=authenticated_tenant_id,
            recent_authentication_verified=recent_authentication_verified,
        )
        verified = identity.normalized()
        existing = self._store.find_link(verified)
        if existing is None:
            raise CentralIdentityError("external identity is not linked")
        if existing.user_id != account.user_id or existing.tenant_id != account.tenant_id:
            raise CentralIdentityError("external identity belongs to another account")
        return self._store.remove_link(account, verified)

    def linked_identities(self, user_id: str) -> tuple[IdentityLink, ...]:
        account = self._store.get_account(user_id.strip())
        if account is None or not account.enabled:
            raise CentralIdentityError("account is unavailable")
        return self._store.list_links(account.user_id)

    def _require_authenticated_account(
        self,
        *,
        authenticated_user_id: str,
        authenticated_tenant_id: str,
        recent_authentication_verified: bool,
    ) -> CanonicalAccount:
        user_id = authenticated_user_id.strip()
        tenant_id = authenticated_tenant_id.strip()
        if not user_id or not tenant_id:
            raise CentralIdentityError("authenticated user and tenant are required")
        if recent_authentication_verified is not True:
            raise CentralIdentityError("recent authentication is required")
        account = self._store.get_account(user_id)
        if account is None or not account.enabled:
            raise CentralIdentityError("authenticated account is unavailable")
        if account.tenant_id != tenant_id:
            raise CentralIdentityError("authenticated tenant mismatch")
        return account


class InMemoryCentralIdentityStore:
    """Deterministic reference store for tests and local integration only."""

    def __init__(self) -> None:
        self._accounts: dict[str, CanonicalAccount] = {}
        self._links: dict[tuple[IdentityProvider, str, str], IdentityLink] = {}
        self._next_account = 1

    def find_link(self, identity: VerifiedExternalIdentity) -> IdentityLink | None:
        return self._links.get(identity.key())

    def get_account(self, user_id: str) -> CanonicalAccount | None:
        return self._accounts.get(user_id)

    def create_account_with_link(
        self, identity: VerifiedExternalIdentity
    ) -> CanonicalAccount:
        verified = identity.normalized()
        key = verified.key()
        if key in self._links:
            raise CentralIdentityError("external identity is already linked")
        sequence = self._next_account
        self._next_account += 1
        account = CanonicalAccount(
            user_id=f"usr_{sequence:08d}", tenant_id=f"tnt_{sequence:08d}"
        )
        self._accounts[account.user_id] = account
        self._links[key] = _link_for(account, verified)
        return account

    def add_link(
        self, account: CanonicalAccount, identity: VerifiedExternalIdentity
    ) -> IdentityLink:
        verified = identity.normalized()
        key = verified.key()
        if key in self._links:
            raise CentralIdentityError("external identity is already linked")
        stored = self._accounts.get(account.user_id)
        if stored != account:
            raise CentralIdentityError("canonical account changed during linking")
        link = _link_for(account, verified)
        self._links[key] = link
        return link

    def remove_link(
        self, account: CanonicalAccount, identity: VerifiedExternalIdentity
    ) -> IdentityLink:
        verified = identity.normalized()
        key = verified.key()
        existing = self._links.get(key)
        if existing is None:
            raise CentralIdentityError("external identity is not linked")
        if existing.user_id != account.user_id or existing.tenant_id != account.tenant_id:
            raise CentralIdentityError("external identity belongs to another account")
        account_links = [
            link for link in self._links.values() if link.user_id == account.user_id
        ]
        if len(account_links) <= 1:
            raise CentralIdentityError("cannot remove the last usable sign-in method")
        del self._links[key]
        return existing

    def list_links(self, user_id: str) -> tuple[IdentityLink, ...]:
        return tuple(
            sorted(
                (link for link in self._links.values() if link.user_id == user_id),
                key=lambda link: (link.provider.value, link.issuer or "", link.subject),
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