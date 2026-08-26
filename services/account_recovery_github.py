"""Trusted GitHub OAuth callback adapter for pre-session account recovery.

This boundary reuses the canonical GitHub OAuth verifier. Client-supplied provider
subjects, usernames, and emails are never accepted as recovery authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from services.central_identity import CanonicalAccount, VerifiedExternalIdentity
from services.github_oauth import GitHubAuthStart, GitHubOAuthService


class AccountRecoveryAuthority(Protocol):
    """Canonical account recovery authority."""

    def recover_existing_account(
        self, identity: VerifiedExternalIdentity
    ) -> CanonicalAccount: ...


@dataclass(frozen=True, slots=True)
class GitHubAccountRecoveryResult:
    status: str
    user_id: str
    tenant_id: str


class GitHubAccountRecoveryService:
    """Recover an existing account only after server-side GitHub OAuth proof."""

    def __init__(
        self,
        *,
        github_oauth: GitHubOAuthService,
        account_recovery: AccountRecoveryAuthority,
    ) -> None:
        self._github_oauth = github_oauth
        self._account_recovery = account_recovery

    def start(
        self,
        redirect_uri: str,
        now: datetime | None = None,
    ) -> GitHubAuthStart:
        return self._github_oauth.start(redirect_uri, now)

    def complete(
        self,
        *,
        state: str,
        code: str,
        now: datetime | None = None,
    ) -> GitHubAccountRecoveryResult:
        identity = self._github_oauth.complete(state=state, code=code, now=now)
        account = self._account_recovery.recover_existing_account(identity)
        return GitHubAccountRecoveryResult(
            status="recovered",
            user_id=account.user_id,
            tenant_id=account.tenant_id,
        )
