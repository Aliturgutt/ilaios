"""SQLite persistence for the canonical commercial identity boundary.

This adapter reuses the authoritative control-plane migration chain. It stores
provider identities by provider + issuer namespace + immutable subject and never
uses email as an account merge key. Session credentials are persisted only as
SHA-256 digests; raw bearer/session material must remain outside this store.
"""

from __future__ import annotations

import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from services.central_identity import (
    CanonicalAccount,
    CentralIdentityError,
    IdentityLink,
    IdentityProvider,
    VerifiedExternalIdentity,
)
from services.control_plane.migrations import LATEST_SCHEMA_VERSION, migrate_database


@dataclass(frozen=True, slots=True)
class PersistedSession:
    session_id: str
    user_id: str
    tenant_id: str
    credential_hash: str
    created_at: str
    expires_at: str
    revoked_at: str | None


@dataclass(frozen=True, slots=True)
class EntitlementRecord:
    tenant_id: str
    entitlement_key: str
    state: str
    limit_value: int | None
    updated_at: str


class SQLiteCentralIdentityStore:
    """Production-oriented persistence adapter for ``CentralIdentityService``."""

    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path
        version = migrate_database(database_path)
        if version < 9 or LATEST_SCHEMA_VERSION < 9:
            raise CentralIdentityError("commercial identity schema is unavailable")

    def find_link(self, identity: VerifiedExternalIdentity) -> IdentityLink | None:
        verified = identity.normalized()
        provider, issuer_namespace, subject = verified.key()
        with self._connect() as connection:
            row = connection.execute(
                "SELECT provider, provider_subject, user_id, tenant_id, "
                "verified_email, issuer_namespace FROM identity_accounts "
                "WHERE provider = ? AND issuer_namespace = ? AND provider_subject = ?",
                (provider.value, issuer_namespace, subject),
            ).fetchone()
        return _link_from_row(row) if row is not None else None

    def get_account(self, user_id: str) -> CanonicalAccount | None:
        normalized_user_id = user_id.strip()
        if not normalized_user_id:
            return None
        with self._connect() as connection:
            row = connection.execute(
                "SELECT u.user_id, m.tenant_id, u.enabled, t.status, m.status "
                "FROM identity_users AS u "
                "JOIN identity_memberships AS m ON m.user_id = u.user_id "
                "JOIN identity_tenants AS t ON t.tenant_id = m.tenant_id "
                "WHERE u.user_id = ? AND m.is_primary = 1",
                (normalized_user_id,),
            ).fetchone()
        if row is None:
            return None
        enabled = bool(row[2]) and row[3] == "ACTIVE" and row[4] == "ACTIVE"
        return CanonicalAccount(user_id=str(row[0]), tenant_id=str(row[1]), enabled=enabled)

    def create_account_with_link(
        self, identity: VerifiedExternalIdentity
    ) -> CanonicalAccount:
        verified = identity.normalized()
        provider, issuer_namespace, subject = verified.key()
        user_id = f"usr_{uuid.uuid4().hex}"
        tenant_id = f"tnt_{uuid.uuid4().hex}"
        identity_account_id = f"ida_{uuid.uuid4().hex}"
        now = _sqlite_now()
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                existing = connection.execute(
                    "SELECT 1 FROM identity_accounts WHERE provider = ? "
                    "AND issuer_namespace = ? AND provider_subject = ?",
                    (provider.value, issuer_namespace, subject),
                ).fetchone()
                if existing is not None:
                    raise CentralIdentityError("external identity is already linked")
                connection.execute(
                    "INSERT INTO identity_tenants "
                    "(tenant_id, status, created_at, updated_at) "
                    "VALUES (?, 'ACTIVE', ?, ?)",
                    (tenant_id, now, now),
                )
                connection.execute(
                    "INSERT INTO identity_users "
                    "(user_id, enabled, created_at, updated_at) VALUES (?, 1, ?, ?)",
                    (user_id, now, now),
                )
                connection.execute(
                    "INSERT INTO identity_memberships "
                    "(tenant_id, user_id, role, status, is_primary, created_at, updated_at) "
                    "VALUES (?, ?, 'OWNER', 'ACTIVE', 1, ?, ?)",
                    (tenant_id, user_id, now, now),
                )
                connection.execute(
                    "INSERT INTO identity_accounts "
                    "(identity_account_id, provider, issuer_namespace, provider_subject, "
                    "user_id, tenant_id, verified_email, created_at, updated_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        identity_account_id,
                        provider.value,
                        issuer_namespace,
                        subject,
                        user_id,
                        tenant_id,
                        verified.email if verified.email_verified else None,
                        now,
                        now,
                    ),
                )
        except sqlite3.IntegrityError as error:
            raise CentralIdentityError("canonical account persistence failed closed") from error
        return CanonicalAccount(user_id=user_id, tenant_id=tenant_id)

    def add_link(
        self, account: CanonicalAccount, identity: VerifiedExternalIdentity
    ) -> IdentityLink:
        verified = identity.normalized()
        provider, issuer_namespace, subject = verified.key()
        current = self.get_account(account.user_id)
        if current != account or not account.enabled:
            raise CentralIdentityError("canonical account changed during linking")
        now = _sqlite_now()
        identity_account_id = f"ida_{uuid.uuid4().hex}"
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                connection.execute(
                    "INSERT INTO identity_accounts "
                    "(identity_account_id, provider, issuer_namespace, provider_subject, "
                    "user_id, tenant_id, verified_email, created_at, updated_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        identity_account_id,
                        provider.value,
                        issuer_namespace,
                        subject,
                        account.user_id,
                        account.tenant_id,
                        verified.email if verified.email_verified else None,
                        now,
                        now,
                    ),
                )
        except sqlite3.IntegrityError as error:
            raise CentralIdentityError("external identity is already linked") from error
        return IdentityLink(
            provider=verified.provider,
            subject=verified.subject,
            user_id=account.user_id,
            tenant_id=account.tenant_id,
            verified_email=verified.email if verified.email_verified else None,
            issuer=verified.issuer,
        )

    def transfer_isolated_link(
        self, account: CanonicalAccount, identity: VerifiedExternalIdentity
    ) -> IdentityLink:
        verified = identity.normalized()
        provider, issuer_namespace, subject = verified.key()
        current = self.get_account(account.user_id)
        if current != account or not account.enabled:
            raise CentralIdentityError("canonical account changed during linking")
        now = _sqlite_now()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT provider, provider_subject, user_id, tenant_id, verified_email, "
                "issuer_namespace FROM identity_accounts WHERE provider = ? "
                "AND issuer_namespace = ? AND provider_subject = ?",
                (provider.value, issuer_namespace, subject),
            ).fetchone()
            if row is None:
                raise CentralIdentityError("external identity is not linked")
            existing = _link_from_row(row)
            if existing.user_id == account.user_id and existing.tenant_id == account.tenant_id:
                return existing

            source = self.get_account(existing.user_id)
            if (
                source is None
                or not source.enabled
                or source.tenant_id != existing.tenant_id
            ):
                raise CentralIdentityError(
                    "external identity is already linked to another account"
                )

            source_link_count_row = connection.execute(
                "SELECT COUNT(*) FROM identity_accounts "
                "WHERE user_id = ? AND tenant_id = ?",
                (source.user_id, source.tenant_id),
            ).fetchone()
            source_memberships = connection.execute(
                "SELECT tenant_id, role, status, is_primary "
                "FROM identity_memberships WHERE user_id = ?",
                (source.user_id,),
            ).fetchall()
            tenant_member_count_row = connection.execute(
                "SELECT COUNT(*) FROM identity_memberships WHERE tenant_id = ?",
                (source.tenant_id,),
            ).fetchone()
            entitlement_count_row = connection.execute(
                "SELECT COUNT(*) FROM identity_entitlements WHERE tenant_id = ?",
                (source.tenant_id,),
            ).fetchone()

            if (
                source_link_count_row is None
                or int(source_link_count_row[0]) != 1
                or source_memberships
                != [(source.tenant_id, "OWNER", "ACTIVE", 1)]
                or tenant_member_count_row is None
                or int(tenant_member_count_row[0]) != 1
                or entitlement_count_row is None
                or int(entitlement_count_row[0]) != 0
            ):
                raise CentralIdentityError(
                    "external identity is already linked to another account"
                )

            connection.execute(
                "UPDATE identity_sessions "
                "SET revoked_at = COALESCE(revoked_at, ?) "
                "WHERE user_id = ? AND tenant_id = ?",
                (now, source.user_id, source.tenant_id),
            )
            cursor = connection.execute(
                "UPDATE identity_accounts SET user_id = ?, tenant_id = ?, updated_at = ? "
                "WHERE provider = ? AND issuer_namespace = ? AND provider_subject = ? "
                "AND user_id = ? AND tenant_id = ?",
                (
                    account.user_id,
                    account.tenant_id,
                    now,
                    provider.value,
                    issuer_namespace,
                    subject,
                    source.user_id,
                    source.tenant_id,
                ),
            )
            if cursor.rowcount != 1:
                raise CentralIdentityError("external identity changed during linking")
            connection.execute(
                "UPDATE identity_memberships "
                "SET status = 'REVOKED', is_primary = 0, updated_at = ? "
                "WHERE tenant_id = ? AND user_id = ?",
                (now, source.tenant_id, source.user_id),
            )
            connection.execute(
                "UPDATE identity_users SET enabled = 0, updated_at = ? WHERE user_id = ?",
                (now, source.user_id),
            )
            connection.execute(
                "UPDATE identity_tenants SET status = 'SUSPENDED', updated_at = ? "
                "WHERE tenant_id = ?",
                (now, source.tenant_id),
            )

        linked = self.find_link(verified)
        if linked is None:
            raise CentralIdentityError("external identity consolidation failed")
        return linked

    def remove_link(
        self, account: CanonicalAccount, identity: VerifiedExternalIdentity
    ) -> IdentityLink:
        verified = identity.normalized()
        provider, issuer_namespace, subject = verified.key()
        current = self.get_account(account.user_id)
        if current != account or not account.enabled:
            raise CentralIdentityError("canonical account changed during unlinking")
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT provider, provider_subject, user_id, tenant_id, verified_email, "
                "issuer_namespace FROM identity_accounts WHERE provider = ? "
                "AND issuer_namespace = ? AND provider_subject = ?",
                (provider.value, issuer_namespace, subject),
            ).fetchone()
            if row is None:
                raise CentralIdentityError("external identity is not linked")
            existing = _link_from_row(row)
            if existing.user_id != account.user_id or existing.tenant_id != account.tenant_id:
                raise CentralIdentityError("external identity belongs to another account")
            count_row = connection.execute(
                "SELECT COUNT(*) FROM identity_accounts WHERE user_id = ? AND tenant_id = ?",
                (account.user_id, account.tenant_id),
            ).fetchone()
            if count_row is None or int(count_row[0]) <= 1:
                raise CentralIdentityError("cannot remove the last usable sign-in method")
            cursor = connection.execute(
                "DELETE FROM identity_accounts WHERE provider = ? "
                "AND issuer_namespace = ? AND provider_subject = ? "
                "AND user_id = ? AND tenant_id = ?",
                (
                    provider.value,
                    issuer_namespace,
                    subject,
                    account.user_id,
                    account.tenant_id,
                ),
            )
            if cursor.rowcount != 1:
                raise CentralIdentityError("external identity unlink failed closed")
        return existing

    def list_links(self, user_id: str) -> tuple[IdentityLink, ...]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT provider, provider_subject, user_id, tenant_id, verified_email, "
                "issuer_namespace FROM identity_accounts WHERE user_id = ? "
                "ORDER BY provider, issuer_namespace, provider_subject",
                (user_id.strip(),),
            ).fetchall()
        return tuple(_link_from_row(row) for row in rows)

    def persist_session(
        self,
        *,
        session_id: str,
        user_id: str,
        tenant_id: str,
        credential_hash: str,
        created_at: str,
        expires_at: str,
    ) -> PersistedSession:
        if len(credential_hash) != 64 or any(
            character not in "0123456789abcdefABCDEF" for character in credential_hash
        ):
            raise CentralIdentityError("session credential digest must be SHA-256 hex")
        account = self.get_account(user_id)
        if account is None or not account.enabled or account.tenant_id != tenant_id:
            raise CentralIdentityError("session account or tenant is invalid")
        try:
            with self._connect() as connection:
                connection.execute(
                    "INSERT INTO identity_sessions "
                    "(session_id, user_id, tenant_id, credential_hash, created_at, expires_at) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (session_id, user_id, tenant_id, credential_hash, created_at, expires_at),
                )
        except sqlite3.IntegrityError as error:
            raise CentralIdentityError("session persistence failed closed") from error
        return PersistedSession(
            session_id=session_id,
            user_id=user_id,
            tenant_id=tenant_id,
            credential_hash=credential_hash,
            created_at=created_at,
            expires_at=expires_at,
            revoked_at=None,
        )

    def revoke_session(self, session_id: str, revoked_at: str) -> bool:
        with self._connect() as connection:
            cursor = connection.execute(
                "UPDATE identity_sessions SET revoked_at = ? "
                "WHERE session_id = ? AND revoked_at IS NULL",
                (revoked_at, session_id),
            )
        return cursor.rowcount == 1

    def get_session(self, session_id: str) -> PersistedSession | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT session_id, user_id, tenant_id, credential_hash, created_at, "
                "expires_at, revoked_at FROM identity_sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()
        if row is None:
            return None
        return PersistedSession(
            session_id=str(row[0]),
            user_id=str(row[1]),
            tenant_id=str(row[2]),
            credential_hash=str(row[3]),
            created_at=str(row[4]),
            expires_at=str(row[5]),
            revoked_at=str(row[6]) if row[6] is not None else None,
        )

    def set_entitlement(
        self,
        *,
        tenant_id: str,
        entitlement_key: str,
        state: str,
        limit_value: int | None,
        updated_at: str,
    ) -> EntitlementRecord:
        if state not in {"ACTIVE", "SUSPENDED", "EXPIRED", "REVOKED"}:
            raise CentralIdentityError("entitlement state is invalid")
        if limit_value is not None and limit_value < 0:
            raise CentralIdentityError("entitlement limit must not be negative")
        with self._connect() as connection:
            tenant = connection.execute(
                "SELECT 1 FROM identity_tenants WHERE tenant_id = ?",
                (tenant_id,),
            ).fetchone()
            if tenant is None:
                raise CentralIdentityError("entitlement tenant is unknown")
            connection.execute(
                "INSERT INTO identity_entitlements "
                "(tenant_id, entitlement_key, state, limit_value, updated_at) "
                "VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT(tenant_id, entitlement_key) DO UPDATE SET "
                "state = excluded.state, limit_value = excluded.limit_value, "
                "updated_at = excluded.updated_at",
                (tenant_id, entitlement_key, state, limit_value, updated_at),
            )
        return EntitlementRecord(
            tenant_id=tenant_id,
            entitlement_key=entitlement_key,
            state=state,
            limit_value=limit_value,
            updated_at=updated_at,
        )

    def get_entitlement(
        self, tenant_id: str, entitlement_key: str
    ) -> EntitlementRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT tenant_id, entitlement_key, state, limit_value, updated_at "
                "FROM identity_entitlements WHERE tenant_id = ? AND entitlement_key = ?",
                (tenant_id, entitlement_key),
            ).fetchone()
        if row is None:
            return None
        return EntitlementRecord(
            tenant_id=str(row[0]),
            entitlement_key=str(row[1]),
            state=str(row[2]),
            limit_value=int(row[3]) if row[3] is not None else None,
            updated_at=str(row[4]),
        )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path)
        connection.execute("PRAGMA foreign_keys = ON")
        return connection


def _link_from_row(row: tuple[object, ...]) -> IdentityLink:
    provider = IdentityProvider(str(row[0]))
    issuer_namespace = str(row[5])
    return IdentityLink(
        provider=provider,
        subject=str(row[1]),
        user_id=str(row[2]),
        tenant_id=str(row[3]),
        verified_email=str(row[4]) if row[4] is not None else None,
        issuer=issuer_namespace if issuer_namespace else None,
    )


def _sqlite_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
