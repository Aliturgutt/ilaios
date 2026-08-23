"""Verified email magic-link / OTP boundary for commercial identity.

This module owns challenge generation and verification only. It does not send
email, create web sessions, or persist production data by itself. Production
adapters must implement ``EmailChallengeStore`` using the canonical identity
persistence authority.

Security properties:
- raw challenge secrets are returned only to the caller that will deliver them;
- only SHA-256 digests are stored;
- challenges are short-lived and single-use;
- issuance is rate-limited per normalized email;
- replay, expiry, malformed secrets, and email mismatch fail closed;
- a successful challenge produces a verified ``EMAIL`` external identity;
- email verification never auto-links to another provider account.
"""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Protocol

from services.central_identity import IdentityProvider, VerifiedExternalIdentity


class EmailAuthError(PermissionError):
    """Email authentication failed closed."""


@dataclass(frozen=True, slots=True)
class EmailChallenge:
    challenge_id: str
    email: str
    secret_digest: str
    issued_at: datetime
    expires_at: datetime
    consumed_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class IssuedEmailChallenge:
    challenge_id: str
    email: str
    secret: str
    expires_at: datetime


class EmailChallengeStore(Protocol):
    """Persistence boundary for single-use email challenges."""

    def recent_issue_count(self, email: str, since: datetime) -> int: ...

    def put(self, challenge: EmailChallenge) -> None: ...

    def consume(
        self,
        *,
        challenge_id: str,
        email: str,
        secret_digest: str,
        now: datetime,
    ) -> EmailChallenge | None: ...


class EmailAuthService:
    """Issue and verify bounded email sign-in challenges."""

    def __init__(
        self,
        store: EmailChallengeStore,
        *,
        ttl: timedelta = timedelta(minutes=10),
        rate_window: timedelta = timedelta(minutes=15),
        max_issues_per_window: int = 5,
    ) -> None:
        if ttl <= timedelta(0) or ttl > timedelta(minutes=30):
            raise ValueError("email challenge TTL must be within (0, 30 minutes]")
        if rate_window <= timedelta(0):
            raise ValueError("email challenge rate window must be positive")
        if max_issues_per_window < 1 or max_issues_per_window > 20:
            raise ValueError("email challenge rate limit is invalid")
        self._store = store
        self._ttl = ttl
        self._rate_window = rate_window
        self._max_issues_per_window = max_issues_per_window

    def issue(self, email: str, *, now: datetime | None = None) -> IssuedEmailChallenge:
        normalized = _normalize_email(email)
        current = _utc(now)
        since = current - self._rate_window
        if self._store.recent_issue_count(normalized, since) >= self._max_issues_per_window:
            raise EmailAuthError("email challenge rate limit exceeded")

        challenge_id = f"emc_{secrets.token_hex(16)}"
        secret = secrets.token_urlsafe(32)
        digest = _digest(secret)
        expires_at = current + self._ttl
        self._store.put(
            EmailChallenge(
                challenge_id=challenge_id,
                email=normalized,
                secret_digest=digest,
                issued_at=current,
                expires_at=expires_at,
            )
        )
        return IssuedEmailChallenge(
            challenge_id=challenge_id,
            email=normalized,
            secret=secret,
            expires_at=expires_at,
        )

    def verify(
        self,
        *,
        challenge_id: str,
        email: str,
        secret: str,
        now: datetime | None = None,
    ) -> VerifiedExternalIdentity:
        normalized = _normalize_email(email)
        normalized_id = challenge_id.strip()
        normalized_secret = secret.strip()
        if not normalized_id.startswith("emc_") or len(normalized_id) < 20:
            raise EmailAuthError("email challenge identifier is invalid")
        if len(normalized_secret) < 32 or len(normalized_secret) > 256:
            raise EmailAuthError("email challenge secret is invalid")

        consumed = self._store.consume(
            challenge_id=normalized_id,
            email=normalized,
            secret_digest=_digest(normalized_secret),
            now=_utc(now),
        )
        if consumed is None:
            raise EmailAuthError("email challenge is invalid, expired, or already used")

        return VerifiedExternalIdentity(
            provider=IdentityProvider.EMAIL,
            subject=normalized,
            email=normalized,
            email_verified=True,
        ).normalized()


class InMemoryEmailChallengeStore:
    """Deterministic reference store for tests and local integration only."""

    def __init__(self) -> None:
        self._challenges: dict[str, EmailChallenge] = {}

    def recent_issue_count(self, email: str, since: datetime) -> int:
        return sum(
            1
            for challenge in self._challenges.values()
            if challenge.email == email and challenge.issued_at >= since
        )

    def put(self, challenge: EmailChallenge) -> None:
        if challenge.challenge_id in self._challenges:
            raise EmailAuthError("email challenge identifier collision")
        self._challenges[challenge.challenge_id] = challenge

    def consume(
        self,
        *,
        challenge_id: str,
        email: str,
        secret_digest: str,
        now: datetime,
    ) -> EmailChallenge | None:
        challenge = self._challenges.get(challenge_id)
        if challenge is None:
            return None
        if challenge.consumed_at is not None:
            return None
        if challenge.email != email:
            return None
        if challenge.expires_at <= now:
            return None
        if not secrets.compare_digest(challenge.secret_digest, secret_digest):
            return None
        consumed = EmailChallenge(
            challenge_id=challenge.challenge_id,
            email=challenge.email,
            secret_digest=challenge.secret_digest,
            issued_at=challenge.issued_at,
            expires_at=challenge.expires_at,
            consumed_at=now,
        )
        self._challenges[challenge_id] = consumed
        return consumed


def _normalize_email(value: str) -> str:
    normalized = value.strip().casefold()
    if not normalized or len(normalized) > 254:
        raise EmailAuthError("email address is invalid")
    if normalized.count("@") != 1:
        raise EmailAuthError("email address is invalid")
    local, domain = normalized.split("@", 1)
    if not local or not domain or "." not in domain:
        raise EmailAuthError("email address is invalid")
    if any(character.isspace() for character in normalized):
        raise EmailAuthError("email address is invalid")
    return normalized


def _digest(secret: str) -> str:
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


def _utc(value: datetime | None) -> datetime:
    current = value or datetime.now(timezone.utc)
    if current.tzinfo is None or current.utcoffset() is None:
        raise EmailAuthError("email challenge time must be timezone-aware")
    return current.astimezone(timezone.utc)
