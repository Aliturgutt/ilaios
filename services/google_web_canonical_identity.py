"""Bind verified Google Web OAuth callbacks to canonical ILAIOS accounts.

Provider verification remains owned by ``GoogleWebOAuthService`` and canonical
User/Tenant creation or lookup remains owned by ``CentralIdentityService``.
This composition accepts no caller-selected user or tenant authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from services.central_identity import (
    CanonicalAccount,
    CentralIdentityError,
    CentralIdentityService,
    IdentityProvider,
)
from services.google_web_oauth import GoogleWebOAuthService


class GoogleWebCanonicalIdentityError(CentralIdentityError):
    """Verified Google callback could not be bound to canonical Identity."""


@dataclass(frozen=True, slots=True)
class GoogleWebCanonicalSignIn:
    """Canonical account result; provider credentials/tokens are never exposed."""

    user_id: str
    tenant_id: str


class GoogleWebCanonicalIdentityFlow:
    """Compose provider verification with incumbent canonical account authority."""

    def __init__(
        self,
        *,
        oauth: GoogleWebOAuthService,
        identity: CentralIdentityService,
    ) -> None:
        self._oauth = oauth
        self._identity = identity

    def complete(
        self,
        *,
        state: str,
        code: str,
        now: datetime,
    ) -> GoogleWebCanonicalSignIn:
        verified = self._oauth.complete(state=state, code=code, now=now)
        if verified.provider is not IdentityProvider.GOOGLE:
            raise GoogleWebCanonicalIdentityError(
                "Google Web OAuth returned non-Google identity"
            )
        account = self._identity.sign_in(verified)
        _validate_account(account)
        return GoogleWebCanonicalSignIn(
            user_id=account.user_id,
            tenant_id=account.tenant_id,
        )


def _validate_account(account: CanonicalAccount) -> None:
    if not account.enabled:
        raise GoogleWebCanonicalIdentityError("canonical account is disabled")
    if not account.user_id.strip() or not account.tenant_id.strip():
        raise GoogleWebCanonicalIdentityError(
            "canonical account coordinates are unavailable"
        )
