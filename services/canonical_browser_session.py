"""Canonical durable browser-session credential authority.

This module completes the incumbent canonical identity session persistence with
opaque browser credential issuance and verification. It does not create a second
identity, membership, role, or session store: identity_sessions remains the
durable session record and canonical membership projection remains authoritative.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from services.canonical_identity_principal import CanonicalIdentityPrincipalResolver
from services.central_identity import CanonicalAccount
from services.control_plane.migrations import migrate_database
from services.identity import IdentityError, Principal
from services.sqlite_central_identity import SQLiteCentralIdentityStore


class CanonicalBrowserSessionError(IdentityError):
    """Canonical browser session issuance or verification failed closed."""


@dataclass(frozen=True, slots=True)
class IssuedBrowserSession:
    session_id: str
    credential: str
    expires_at: datetime


class CanonicalBrowserSessionAuthority:
    """Issue, verify, and revoke durable opaque browser sessions."""

    def __init__(self, identity_database: Path, maximum_lifetime: timedelta) -> None:
        if maximum_lifetime <= timedelta(0):
            raise CanonicalBrowserSessionError("maximum session lifetime is invalid")
        self._identity_database = identity_database
        self._maximum_lifetime = maximum_lifetime
        if migrate_database(identity_database) < 9:
            raise CanonicalBrowserSessionError("canonical identity schema is unavailable")
        self._principal_resolver = CanonicalIdentityPrincipalResolver(identity_database)

    def issue(
        self,
        account: CanonicalAccount,
        now: datetime,
        lifetime: timedelta,
    ) -> IssuedBrowserSession:
        self._require_aware(now)
        if lifetime <= timedelta(0) or lifetime > self._maximum_lifetime:
            raise CanonicalBrowserSessionError("session lifetime violates policy")

        principal = self._principal_resolver.resolve(account)
        session_id = f"ses_{secrets.token_urlsafe(24)}"
        credential = secrets.token_urlsafe(48)
        expires_at = now + lifetime
        credential_hash = self._digest(credential)

        try:
            with sqlite3.connect(self._identity_database) as connection:
                connection.execute("PRAGMA foreign_keys = ON")
                connection.execute(
                    """
                    INSERT INTO identity_sessions
                        (session_id, user_id, tenant_id, credential_hash,
                         created_at, expires_at, revoked_at)
                    VALUES (?, ?, ?, ?, ?, ?, NULL)
                    """,
                    (
                        session_id,
                        principal.principal_id,
                        principal.tenant_id,
                        credential_hash,
                        now.isoformat(),
                        expires_at.isoformat(),
                    ),
                )
                connection.commit()
        except sqlite3.IntegrityError as exc:
            raise CanonicalBrowserSessionError(
                "canonical session persistence conflict"
            ) from exc

        return IssuedBrowserSession(
            session_id=session_id,
            credential=credential,
            expires_at=expires_at,
        )

    def verify(self, session_id: str, credential: str, now: datetime) -> Principal:
        self._require_aware(now)
        normalized_session_id = session_id.strip()
        normalized_credential = credential.strip()
        if not normalized_session_id or not normalized_credential:
            raise CanonicalBrowserSessionError("session is invalid or revoked")

        with sqlite3.connect(self._identity_database) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            row = connection.execute(
                """
                SELECT user_id, tenant_id, credential_hash, expires_at, revoked_at
                  FROM identity_sessions
                 WHERE session_id = ?
                """,
                (normalized_session_id,),
            ).fetchone()

            if row is None:
                raise CanonicalBrowserSessionError("session is invalid or revoked")

            user_id = str(row[0])
            tenant_id = str(row[1])
            stored_hash = str(row[2])
            expires_at = self._parse_timestamp(str(row[3]))
            revoked_at = row[4]

            if revoked_at is not None or expires_at <= now:
                raise CanonicalBrowserSessionError("session is invalid or revoked")
            if not hmac.compare_digest(
                self._digest(normalized_credential),
                stored_hash,
            ):
                raise CanonicalBrowserSessionError("session is invalid or revoked")

            account = SQLiteCentralIdentityStore(connection).get_account(user_id)

        if account is None or account.tenant_id != tenant_id or not account.enabled:
            raise CanonicalBrowserSessionError("session is invalid or revoked")

        return self._principal_resolver.resolve(account)

    def revoke(self, session_id: str, now: datetime) -> None:
        self._require_aware(now)
        normalized_session_id = session_id.strip()
        if not normalized_session_id:
            raise CanonicalBrowserSessionError("session is invalid or revoked")
        with sqlite3.connect(self._identity_database) as connection:
            connection.execute(
                """
                UPDATE identity_sessions
                   SET revoked_at = COALESCE(revoked_at, ?)
                 WHERE session_id = ?
                """,
                (now.isoformat(), normalized_session_id),
            )
            connection.commit()

    @staticmethod
    def _digest(credential: str) -> str:
        return hashlib.sha256(credential.encode("utf-8")).hexdigest()

    @staticmethod
    def _parse_timestamp(value: str) -> datetime:
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError as exc:
            raise CanonicalBrowserSessionError(
                "session is invalid or revoked"
            ) from exc
        CanonicalBrowserSessionAuthority._require_aware(parsed)
        return parsed

    @staticmethod
    def _require_aware(value: datetime) -> None:
        if value.tzinfo is None or value.utcoffset() is None:
            raise CanonicalBrowserSessionError(
                "timezone-aware session time is required"
            )


__all__ = [
    "CanonicalBrowserSessionAuthority",
    "CanonicalBrowserSessionError",
    "IssuedBrowserSession",
]
