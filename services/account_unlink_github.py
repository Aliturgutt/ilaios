"""Trusted GitHub reauthentication adapter for canonical account unlinking.

This module does not verify GitHub credentials itself and does not create a new
identity authority. It composes the existing ``GitHubOAuthService`` with the
canonical ``AccountLifecycleService`` unlink boundary.

Security properties:
- target provider subjects/emails are never accepted from client input;
- unlink targets are selected from the authenticated account's canonical links
  and represented to the caller only by short-lived opaque references;
- GitHub reauthentication is completed server-side by the existing provider
  verifier and yields a ``VerifiedExternalIdentity``;
- the target reference and OAuth state are single-use and short-lived;
- authenticated user/tenant binding and recent-auth proof are required both
  before starting and before completing the sensitive unlink operation;
- the canonical lifecycle service remains authoritative for distinct-identity,
  same-account/same-tenant, and last-usable-login enforcement.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Protocol

from services.central_identity import (
    CanonicalAccount,
    CentralIdentityError,
    CentralIdentityStore,
    IdentityLink,
    IdentityProvider,
    VerifiedExternalIdentity,
)
from services.github_oauth import GitHubAuthStart, GitHubOAuthService

_TARGET_LIFETIME = timedelta(minutes=5)


class AccountUnlinkAuthority(Protocol):
    """Canonical account-unlink authority consumed by this adapter."""

    def unlink_identity(
        self,
        *,
        authenticated_user_id: str,
        authenticated_tenant_id: str,
        identity: VerifiedExternalIdentity,
        reauthenticated_identity: VerifiedExternalIdentity,
    ) -> IdentityLink: ...


@dataclass(frozen=True, slots=True)
class GitHubUnlinkTarget:
    """Opaque unlink target safe to project to an authenticated client."""

    reference: str
    provider: IdentityProvider
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class GitHubUnlinkResult:
    status: str
    provider: IdentityProvider


@dataclass(frozen=True, slots=True)
class _TargetFlow:
    reference: str
    user_id: str
    tenant_id: str
    identity: VerifiedExternalIdentity
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class _PendingUnlink:
    state: str
    user_id: str
    tenant_id: str
    identity: VerifiedExternalIdentity
    expires_at: datetime


class GitHubAccountUnlinkService:
    """Bind opaque canonical unlink targets to server-verified GitHub reauth."""

    def __init__(
        self,
        *,
        github_oauth: GitHubOAuthService,
        identity_store: CentralIdentityStore,
        account_unlink: AccountUnlinkAuthority,
    ) -> None:
        self._github_oauth = github_oauth
        self._identity_store = identity_store
        self._account_unlink = account_unlink
        self._targets: dict[str, _TargetFlow] = {}
        self._pending: dict[str, _PendingUnlink] = {}

    def prepare_targets(
        self,
        *,
        authenticated_user_id: str,
        authenticated_tenant_id: str,
        now: datetime | None = None,
    ) -> tuple[GitHubUnlinkTarget, ...]:
        """Issue short-lived opaque references for this account's current links."""

        current = _utc(now)
        self._purge(current)
        user_id, tenant_id, account = self._require_account(
            authenticated_user_id=authenticated_user_id,
            authenticated_tenant_id=authenticated_tenant_id,
        )
        links = tuple(self._identity_store.list_links(account.user_id))
        if len(links) < 2:
            raise CentralIdentityError("cannot remove the last usable login identity")

        targets: list[GitHubUnlinkTarget] = []
        expires_at = current + _TARGET_LIFETIME
        for link in links:
            if link.user_id != user_id or link.tenant_id != tenant_id:
                raise CentralIdentityError("identity link tenant mismatch")
            reference = secrets.token_urlsafe(32)
            identity = _identity_from_link(link)
            self._targets[reference] = _TargetFlow(
                reference=reference,
                user_id=user_id,
                tenant_id=tenant_id,
                identity=identity,
                expires_at=expires_at,
            )
            targets.append(
                GitHubUnlinkTarget(
                    reference=reference,
                    provider=identity.provider,
                    expires_at=expires_at,
                )
            )
        return tuple(targets)

    def start(
        self,
        *,
        target_reference: str,
        authenticated_user_id: str,
        authenticated_tenant_id: str,
        recent_authentication_verified: bool,
        redirect_uri: str,
        now: datetime | None = None,
    ) -> GitHubAuthStart:
        """Consume one opaque target reference and start distinct GitHub reauth."""

        current = _utc(now)
        self._purge(current)
        if recent_authentication_verified is not True:
            raise CentralIdentityError("recent authentication is required")
        user_id, tenant_id, _ = self._require_account(
            authenticated_user_id=authenticated_user_id,
            authenticated_tenant_id=authenticated_tenant_id,
        )
        reference = target_reference.strip()
        target = self._targets.pop(reference, None)
        if target is None or target.expires_at <= current:
            raise CentralIdentityError("unlink target reference is invalid or expired")
        if target.user_id != user_id or target.tenant_id != tenant_id:
            raise CentralIdentityError("unlink target belongs to another canonical account")

        start = self._github_oauth.start(redirect_uri, current)
        expires_at = min(target.expires_at, start.expires_at)
        self._pending[start.state] = _PendingUnlink(
            state=start.state,
            user_id=user_id,
            tenant_id=tenant_id,
            identity=target.identity,
            expires_at=expires_at,
        )
        return start

    def complete(
        self,
        *,
        state: str,
        code: str,
        authenticated_user_id: str,
        authenticated_tenant_id: str,
        recent_authentication_verified: bool,
        now: datetime | None = None,
    ) -> GitHubUnlinkResult:
        """Complete GitHub proof and delegate unlink to canonical lifecycle policy."""

        current = _utc(now)
        self._purge(current)
        if recent_authentication_verified is not True:
            raise CentralIdentityError("recent authentication is required")
        user_id, tenant_id, _ = self._require_account(
            authenticated_user_id=authenticated_user_id,
            authenticated_tenant_id=authenticated_tenant_id,
        )
        pending = self._pending.pop(state, None)
        if pending is None or pending.expires_at <= current:
            raise CentralIdentityError("unlink reauthentication state is invalid or expired")
        if pending.user_id != user_id or pending.tenant_id != tenant_id:
            raise CentralIdentityError("unlink reauthentication belongs to another account")

        reauthenticated = self._github_oauth.complete(
            state=state,
            code=code,
            now=current,
        )
        removed = self._account_unlink.unlink_identity(
            authenticated_user_id=user_id,
            authenticated_tenant_id=tenant_id,
            identity=pending.identity,
            reauthenticated_identity=reauthenticated,
        )
        return GitHubUnlinkResult(status="unlinked", provider=removed.provider)

    def _require_account(
        self,
        *,
        authenticated_user_id: str,
        authenticated_tenant_id: str,
    ) -> tuple[str, str, CanonicalAccount]:
        user_id = authenticated_user_id.strip()
        tenant_id = authenticated_tenant_id.strip()
        if not user_id or not tenant_id:
            raise CentralIdentityError("authenticated user and tenant are required")
        account = self._identity_store.get_account(user_id)
        if account is None or not account.enabled:
            raise CentralIdentityError("authenticated account is unavailable")
        if account.tenant_id != tenant_id:
            raise CentralIdentityError("authenticated tenant mismatch")
        return user_id, tenant_id, account

    def _purge(self, now: datetime) -> None:
        expired_targets = [
            reference
            for reference, target in self._targets.items()
            if target.expires_at <= now
        ]
        for reference in expired_targets:
            self._targets.pop(reference, None)
        expired_states = [
            state for state, pending in self._pending.items() if pending.expires_at <= now
        ]
        for state in expired_states:
            self._pending.pop(state, None)


def _identity_from_link(link: IdentityLink) -> VerifiedExternalIdentity:
    return VerifiedExternalIdentity(
        provider=link.provider,
        subject=link.subject,
        email=link.verified_email,
        email_verified=link.verified_email is not None,
        issuer=link.issuer,
    ).normalized()


def _utc(value: datetime | None) -> datetime:
    current = value or datetime.now(timezone.utc)
    if current.tzinfo is None:
        raise CentralIdentityError("unlink timestamps must be timezone-aware")
    return current.astimezone(timezone.utc)
