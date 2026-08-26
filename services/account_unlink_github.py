"""Trusted GitHub reauthentication adapter for canonical account unlinking.

The browser/client never supplies a raw provider subject, email, or canonical user
identifier as unlink authority. A target identity is selected by an opaque
SHA-256 reference resolved only against links already owned by the authenticated
canonical user/tenant. GitHub reauthentication is completed server-side through
the incumbent ``GitHubOAuthService`` and the resulting immutable provider
identity is passed to the existing ``AccountLifecycleService`` unlink policy.
"""

from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from services.central_identity import (
    CentralIdentityError,
    CentralIdentityStore,
    IdentityLink,
    VerifiedExternalIdentity,
)
from services.github_oauth import GitHubAuthStart, GitHubOAuthService


class AccountUnlinkAuthority(Protocol):
    """Canonical sensitive unlink authority."""

    def unlink_identity(
        self,
        *,
        authenticated_user_id: str,
        authenticated_tenant_id: str,
        identity: VerifiedExternalIdentity,
        reauthenticated_identity: VerifiedExternalIdentity,
    ) -> IdentityLink: ...


class OwnedIdentityReferenceResolver(Protocol):
    """Resolve an opaque target reference inside one canonical account only."""

    def resolve_owned_identity(
        self,
        *,
        user_id: str,
        tenant_id: str,
        reference_sha256: str,
    ) -> VerifiedExternalIdentity: ...


@dataclass(frozen=True, slots=True)
class GitHubAccountUnlinkResult:
    status: str
    provider: str


class CentralIdentityOwnedReferenceResolver:
    """Resolve link references without accepting raw external identity authority."""

    def __init__(self, identity_store: CentralIdentityStore) -> None:
        self._identity_store = identity_store

    def resolve_owned_identity(
        self,
        *,
        user_id: str,
        tenant_id: str,
        reference_sha256: str,
    ) -> VerifiedExternalIdentity:
        canonical_user_id = user_id.strip()
        canonical_tenant_id = tenant_id.strip()
        reference = reference_sha256.strip().casefold()
        if not canonical_user_id or not canonical_tenant_id:
            raise CentralIdentityError("authenticated user and tenant are required")
        if len(reference) != 64 or any(char not in "0123456789abcdef" for char in reference):
            raise CentralIdentityError("identity link reference is invalid")

        account = self._identity_store.get_account(canonical_user_id)
        if account is None or not account.enabled:
            raise CentralIdentityError("authenticated account is unavailable")
        if account.tenant_id != canonical_tenant_id:
            raise CentralIdentityError("authenticated tenant mismatch")

        matches: list[VerifiedExternalIdentity] = []
        for link in self._identity_store.list_links(canonical_user_id):
            if link.tenant_id != canonical_tenant_id:
                raise CentralIdentityError("identity link tenant mismatch")
            identity = _verified_identity_from_link(link)
            if hmac.compare_digest(_identity_reference_sha256(identity), reference):
                matches.append(identity)

        if len(matches) != 1:
            raise CentralIdentityError("identity link reference is not uniquely owned")
        return matches[0]


class GitHubAccountUnlinkService:
    """Unlink one owned identity only after a distinct trusted GitHub reauthentication."""

    def __init__(
        self,
        *,
        github_oauth: GitHubOAuthService,
        reference_resolver: OwnedIdentityReferenceResolver,
        account_unlink: AccountUnlinkAuthority,
    ) -> None:
        self._github_oauth = github_oauth
        self._reference_resolver = reference_resolver
        self._account_unlink = account_unlink

    def start(
        self,
        redirect_uri: str,
        now: datetime | None = None,
    ) -> GitHubAuthStart:
        return self._github_oauth.start(redirect_uri, now)

    def complete(
        self,
        *,
        authenticated_user_id: str,
        authenticated_tenant_id: str,
        target_identity_reference_sha256: str,
        state: str,
        code: str,
        now: datetime | None = None,
    ) -> GitHubAccountUnlinkResult:
        user_id = authenticated_user_id.strip()
        tenant_id = authenticated_tenant_id.strip()
        target = self._reference_resolver.resolve_owned_identity(
            user_id=user_id,
            tenant_id=tenant_id,
            reference_sha256=target_identity_reference_sha256,
        )
        reauthenticated = self._github_oauth.complete(state=state, code=code, now=now)
        removed = self._account_unlink.unlink_identity(
            authenticated_user_id=user_id,
            authenticated_tenant_id=tenant_id,
            identity=target,
            reauthenticated_identity=reauthenticated,
        )
        return GitHubAccountUnlinkResult(
            status="unlinked",
            provider=removed.provider.value,
        )


def identity_link_reference_sha256(link: IdentityLink) -> str:
    """Return the opaque stable reference exposed to trusted account-management UI."""

    return _identity_reference_sha256(_verified_identity_from_link(link))


def _verified_identity_from_link(link: IdentityLink) -> VerifiedExternalIdentity:
    return VerifiedExternalIdentity(
        provider=link.provider,
        subject=link.subject,
        email=link.verified_email,
        email_verified=link.verified_email is not None,
        issuer=link.issuer,
    ).normalized()


def _identity_reference_sha256(identity: VerifiedExternalIdentity) -> str:
    provider, issuer_namespace, subject = identity.key()
    material = "\x1f".join((provider.value, issuer_namespace, subject)).encode("utf-8")
    return hashlib.sha256(material).hexdigest()
