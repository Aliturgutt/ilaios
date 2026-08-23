"""Verified email magic-link / OTP boundary for commercial identity.

This module owns challenge generation and verification only. It does not send
email or create web sessions. Production adapters must use the canonical
identity database and schema migration authority.

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
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
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


class SQLiteEmailChallengeStore:
    """SQLite adapter for the canonical identity database.

    Schema creation is deliberately *not* performed here. The authoritative
    control-plane migration chain must create ``identity_email_challenges``.
    Until that migration is present, construction fails closed instead of
    silently creating a parallel schema authority.
    """

    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path
        if not database_path.is_file():
            raise EmailAuthError("canonical identity database is unavailable")
        with self._connect() as connection:
            exists = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' "
                "AND name = 'identity_email_challenges'"
            ).fetchone()
        if exists is None:
            raise EmailAuthError("email challenge persistence schema is unavailable")

    def recent_issue_count(self, email: str, since: datetime) -> int:
        normalized_since = _sqlite_time(_utc(since))
        with self._connect() as connection:
            row = connection.execute(
                "SELECT COUNT(*) FROM identity_email_challenges "
                "WHERE email = ? AND issued_at >= ?",
                (email, normalized_since),
            ).fetchone()
        return int(row[0]) if row is not None else 0

    def put(self, challenge: EmailChallenge) -> None:
        if challenge.consumed_at is not None:
            raise EmailAuthError("new email challenge must not be pre-consumed")
        try:
            with self._connect() as connection:
                connection.execute(
                    "INSERT INTO identity_email_challenges "
                    "(challenge_id, email, secret_digest, issued_at, expires_at, consumed_at) "
                    "VALUES (?, ?, ?, ?, ?, NULL)",
                    (
                        challenge.challenge_id,
                        challenge.email,
                        challenge.secret_digest,
                        _sqlite_time(challenge.issued_at),
                        _sqlite_time(challenge.expires_at),
                    ),
                )
        except sqlite3.IntegrityError as error:
            raise EmailAuthError("email challenge persistence failed closed") from error

    def consume(
        self,
        *,
        challenge_id: str,
        email: str,
        secret_digest: str,
        now: datetime,
    ) -> EmailChallenge | None:
        current = _utc(now)
        current_text = _sqlite_time(current)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT challenge_id, email, secret_digest, issued_at, expires_at, consumed_at "
                "FROM identity_email_challenges WHERE challenge_id = ?",
                (challenge_id,),
            ).fetchone()
            if row is None:
                return None
            stored = _challenge_from_row(row)
            if stored.consumed_at is not None:
                return None
            if stored.email != email:
                return None
            if stored.expires_at <= current:
                return None
            if not secrets.compare_digest(stored.secret_digest, secret_digest):
                return None
            cursor = connection.execute(
                "UPDATE identity_email_challenges SET consumed_at = ? "
                "WHERE challenge_id = ? AND consumed_at IS NULL",
                (current_text, challenge_id),
            )
            if cursor.rowcount != 1:
                return None
        return EmailChallenge(
            challenge_id=stored.challenge_id,
            email=stored.email,
            secret_digest=stored.secret_digest,
            issued_at=stored.issued_at,
            expires_at=stored.expires_at,
            consumed_at=current,
        )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path)
        connection.execute("PRAGMA foreign_keys = ON")
        return connection


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


def _challenge_from_row(row: tuple[object, ...]) -> EmailChallenge:
    return EmailChallenge(
        challenge_id=str(row[0]),
        email=str(row[1]),
        secret_digest=str(row[2]),
        issued_at=_parse_sqlite_time(str(row[3])),
        expires_at=_parse_sqlite_time(str(row[4])),
        consumed_at=_parse_sqlite_time(str(row[5])) if row[5] is not None else None,
    )


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


def _sqlite_time(value: datetime) -> str:
    return _utc(value).isoformat().replace("+00:00", "Z")


def _parse_sqlite_time(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise EmailAuthError("persisted email challenge timestamp is invalid") from error
    return _utc(parsed)
