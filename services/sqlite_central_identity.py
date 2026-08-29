"""SQLite production persistence adapter for the canonical CentralIdentityStore.

This adapter uses the existing migration-v9 identity tables. It does not create a
parallel identity authority: CentralIdentityService remains the only account/linking
boundary and database uniqueness remains authoritative for provider subjects.
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from uuid import uuid4

from services.central_identity import (
    CanonicalAccount,
    CentralIdentityError,
    IdentityLink,
    IdentityProvider,
    VerifiedExternalIdentity,
)


class SQLiteCentralIdentityStore:
    """Durable CentralIdentityStore backed by the canonical control-plane DB."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._db = connection
        self._db.execute("PRAGMA foreign_keys = ON")

    def find_link(self, identity: VerifiedExternalIdentity) -> IdentityLink | None:
        verified = identity.normalized()
        provider, namespace, subject = verified.key()
        row = self._db.execute(
            """
            SELECT provider, issuer_namespace, provider_subject, user_id, tenant_id,
                   verified_email
              FROM identity_accounts
             WHERE provider = ? AND issuer_namespace = ? AND provider_subject = ?
            """,
            (provider.value, namespace, subject),
        ).fetchone()
        return None if row is None else self._row_to_link(row)

    def get_account(self, user_id: str) -> CanonicalAccount | None:
        row = self._db.execute(
            """
            SELECT u.user_id, m.tenant_id, u.enabled
              FROM identity_users AS u
              JOIN identity_memberships AS m ON m.user_id = u.user_id
             WHERE u.user_id = ? AND m.is_primary = 1 AND m.status = 'ACTIVE'
            """,
            (user_id.strip(),),
        ).fetchone()
        if row is None:
            return None
        return CanonicalAccount(user_id=row[0], tenant_id=row[1], enabled=bool(row[2]))

    def create_account_with_link(
        self, identity: VerifiedExternalIdentity
    ) -> CanonicalAccount:
        verified = identity.normalized()
        now = _now()
        account = CanonicalAccount(
            user_id=f"usr_{uuid4().hex}", tenant_id=f"tnt_{uuid4().hex}"
        )
        try:
            with self._db:
                if self.find_link(verified) is not None:
                    raise CentralIdentityError("external identity is already linked")
                self._db.execute(
                    "INSERT INTO identity_tenants (tenant_id, status, created_at, updated_at) VALUES (?, 'ACTIVE', ?, ?)",
                    (account.tenant_id, now, now),
                )
                self._db.execute(
                    "INSERT INTO identity_users (user_id, enabled, created_at, updated_at) VALUES (?, 1, ?, ?)",
                    (account.user_id, now, now),
                )
                self._db.execute(
                    """
                    INSERT INTO identity_memberships
                        (tenant_id, user_id, role, status, is_primary, created_at, updated_at)
                    VALUES (?, ?, 'OWNER', 'ACTIVE', 1, ?, ?)
                    """,
                    (account.tenant_id, account.user_id, now, now),
                )
                self._insert_link(account, verified, now)
        except sqlite3.IntegrityError as exc:
            raise CentralIdentityError("canonical identity persistence conflict") from exc
        return account

    def add_link(
        self, account: CanonicalAccount, identity: VerifiedExternalIdentity
    ) -> IdentityLink:
        verified = identity.normalized()
        stored = self.get_account(account.user_id)
        if stored != account:
            raise CentralIdentityError("canonical account changed during linking")
        try:
            with self._db:
                if self.find_link(verified) is not None:
                    raise CentralIdentityError("external identity is already linked")
                return self._insert_link(account, verified, _now())
        except sqlite3.IntegrityError as exc:
            raise CentralIdentityError("canonical identity persistence conflict") from exc

    def remove_link(
        self, account: CanonicalAccount, identity: VerifiedExternalIdentity
    ) -> IdentityLink:
        verified = identity.normalized()
        provider, namespace, subject = verified.key()
        with self._db:
            existing = self.find_link(verified)
            if existing is None:
                raise CentralIdentityError("external identity is not linked")
            if existing.user_id != account.user_id or existing.tenant_id != account.tenant_id:
                raise CentralIdentityError("external identity belongs to another account")
            count = self._db.execute(
                "SELECT COUNT(*) FROM identity_accounts WHERE user_id = ? AND tenant_id = ?",
                (account.user_id, account.tenant_id),
            ).fetchone()[0]
            if count <= 1:
                raise CentralIdentityError("cannot remove the last usable sign-in method")
            deleted = self._db.execute(
                """
                DELETE FROM identity_accounts
                 WHERE provider = ? AND issuer_namespace = ? AND provider_subject = ?
                   AND user_id = ? AND tenant_id = ?
                """,
                (provider.value, namespace, subject, account.user_id, account.tenant_id),
            ).rowcount
            if deleted != 1:
                raise CentralIdentityError("external identity changed during unlink")
        return existing

    def list_links(self, user_id: str) -> tuple[IdentityLink, ...]:
        rows = self._db.execute(
            """
            SELECT provider, issuer_namespace, provider_subject, user_id, tenant_id,
                   verified_email
              FROM identity_accounts
             WHERE user_id = ?
             ORDER BY provider, issuer_namespace, provider_subject
            """,
            (user_id.strip(),),
        ).fetchall()
        return tuple(self._row_to_link(row) for row in rows)

    def _insert_link(
        self,
        account: CanonicalAccount,
        identity: VerifiedExternalIdentity,
        now: str,
    ) -> IdentityLink:
        provider, namespace, subject = identity.key()
        verified_email = identity.email if identity.email_verified else None
        self._db.execute(
            """
            INSERT INTO identity_accounts
                (identity_account_id, provider, issuer_namespace, provider_subject,
                 user_id, tenant_id, verified_email, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"ida_{uuid4().hex}", provider.value, namespace, subject,
                account.user_id, account.tenant_id, verified_email, now, now,
            ),
        )
        return IdentityLink(
            provider=provider,
            subject=subject,
            user_id=account.user_id,
            tenant_id=account.tenant_id,
            verified_email=verified_email,
            issuer=identity.issuer,
        )

    @staticmethod
    def _row_to_link(row: tuple[object, ...]) -> IdentityLink:
        provider = IdentityProvider(str(row[0]))
        namespace = str(row[1])
        return IdentityLink(
            provider=provider,
            subject=str(row[2]),
            user_id=str(row[3]),
            tenant_id=str(row[4]),
            verified_email=None if row[5] is None else str(row[5]),
            issuer=namespace if provider in {IdentityProvider.MICROSOFT, IdentityProvider.ENTERPRISE_OIDC} else None,
        )


def _now() -> str:
    return datetime.now(UTC).isoformat()


__all__ = ["SQLiteCentralIdentityStore"]
