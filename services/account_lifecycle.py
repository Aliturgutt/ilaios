"""Authenticated account-link lifecycle boundary for commercial identity.

This module extends the existing canonical central identity authority without
creating a parallel identity store. Linking remains owned by
``CentralIdentityService``. This boundary adds two sensitive operations:

- recovery of an *existing* canonical account from an already-verified linked
  provider identity without creating a new account;
- unlinking only after canonical authentication plus re-authentication through
  a different, already-linked provider identity.

Email/login metadata is never used as an account key. Provider immutable keys
remain the only external identity authority.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Protocol

from services.central_identity import (
    CanonicalAccount,
    CentralIdentityError,
    CentralIdentityStore,
    IdentityLink,
    VerifiedExternalIdentity,
)
from services.control_plane.migrations import LATEST_SCHEMA_VERSION, migrate_database


class IdentityLinkRemovalStore(Protocol):
    """Atomic mutation boundary for removing one canonical external identity."""

    def remove_link_if_alternate_exists(
        self,
        *,
        user_id: str,
        tenant_id: str,
        identity: VerifiedExternalIdentity,
    ) -> IdentityLink: ...


class AccountLifecycleService:
    """Fail-closed account recovery and unlinking policy."""

    def __init__(
        self,
        *,
        identity_store: CentralIdentityStore,
        removal_store: IdentityLinkRemovalStore,
    ) -> None:
        self._identity_store = identity_store
        self._removal_store = removal_store

    def recover_existing_account(
        self, identity: VerifiedExternalIdentity
    ) -> CanonicalAccount:
        """Recover only an existing linked account; never create or auto-merge."""

        verified = identity.normalized()
        link = self._identity_store.find_link(verified)
        if link is None:
            raise CentralIdentityError("recovery identity is not linked")
        account = self._identity_store.get_account(link.user_id)
        if account is None or not account.enabled:
            raise CentralIdentityError("recovery account is unavailable")
        if account.tenant_id != link.tenant_id:
            raise CentralIdentityError("recovery identity tenant mismatch")
        return account

    def unlink_identity(
        self,
        *,
        authenticated_user_id: str,
        authenticated_tenant_id: str,
        identity: VerifiedExternalIdentity,
        reauthenticated_identity: VerifiedExternalIdentity,
    ) -> IdentityLink:
        """Unlink one identity only after re-auth through a distinct linked identity."""

        user_id = authenticated_user_id.strip()
        tenant_id = authenticated_tenant_id.strip()
        if not user_id or not tenant_id:
            raise CentralIdentityError("authenticated user and tenant are required")

        account = self._identity_store.get_account(user_id)
        if account is None or not account.enabled:
            raise CentralIdentityError("authenticated account is unavailable")
        if account.tenant_id != tenant_id:
            raise CentralIdentityError("authenticated tenant mismatch")

        target = identity.normalized()
        reauth = reauthenticated_identity.normalized()
        if target.key() == reauth.key():
            raise CentralIdentityError("unlink requires a different re-authenticated identity")

        target_link = self._identity_store.find_link(target)
        if target_link is None:
            raise CentralIdentityError("identity to unlink is not linked")
        _require_owned_link(target_link, user_id=user_id, tenant_id=tenant_id)

        reauth_link = self._identity_store.find_link(reauth)
        if reauth_link is None:
            raise CentralIdentityError("re-authenticated identity is not linked")
        _require_owned_link(reauth_link, user_id=user_id, tenant_id=tenant_id)

        links = self._identity_store.list_links(user_id)
        if len(links) < 2:
            raise CentralIdentityError("cannot remove the last usable login identity")

        return self._removal_store.remove_link_if_alternate_exists(
            user_id=user_id,
            tenant_id=tenant_id,
            identity=target,
        )


class SQLiteIdentityLinkRemovalStore:
    """Atomic unlink mutation against the canonical identity database."""

    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path
        version = migrate_database(database_path)
        if version < 9 or LATEST_SCHEMA_VERSION < 9:
            raise CentralIdentityError("commercial identity schema is unavailable")

    def remove_link_if_alternate_exists(
        self,
        *,
        user_id: str,
        tenant_id: str,
        identity: VerifiedExternalIdentity,
    ) -> IdentityLink:
        verified = identity.normalized()
        provider, issuer_namespace, subject = verified.key()
        with self._connect() as connection:
            try:
                connection.execute("BEGIN IMMEDIATE")
                row = connection.execute(
                    "SELECT provider, provider_subject, user_id, tenant_id, verified_email, "
                    "issuer_namespace FROM identity_accounts "
                    "WHERE provider = ? AND issuer_namespace = ? AND provider_subject = ?",
                    (provider.value, issuer_namespace, subject),
                ).fetchone()
                if row is None:
                    raise CentralIdentityError("identity to unlink is not linked")
                link = _link_from_row(row)
                _require_owned_link(link, user_id=user_id, tenant_id=tenant_id)

                alternate_count = connection.execute(
                    "SELECT COUNT(*) FROM identity_accounts "
                    "WHERE user_id = ? AND tenant_id = ? AND NOT "
                    "(provider = ? AND issuer_namespace = ? AND provider_subject = ?)",
                    (
                        user_id,
                        tenant_id,
                        provider.value,
                        issuer_namespace,
                        subject,
                    ),
                ).fetchone()
                if alternate_count is None or int(alternate_count[0]) < 1:
                    raise CentralIdentityError("cannot remove the last usable login identity")

                cursor = connection.execute(
                    "DELETE FROM identity_accounts WHERE provider = ? "
                    "AND issuer_namespace = ? AND provider_subject = ? "
                    "AND user_id = ? AND tenant_id = ?",
                    (provider.value, issuer_namespace, subject, user_id, tenant_id),
                )
                if cursor.rowcount != 1:
                    raise CentralIdentityError("identity unlink failed closed")
                return link
            except sqlite3.IntegrityError as error:
                raise CentralIdentityError("identity unlink failed closed") from error

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path)
        connection.execute("PRAGMA foreign_keys = ON")
        return connection


def _require_owned_link(link: IdentityLink, *, user_id: str, tenant_id: str) -> None:
    if link.user_id != user_id or link.tenant_id != tenant_id:
        raise CentralIdentityError("identity belongs to another canonical account")


def _link_from_row(row: tuple[object, ...]) -> IdentityLink:
    from services.central_identity import IdentityProvider

    issuer_namespace = str(row[5])
    return IdentityLink(
        provider=IdentityProvider(str(row[0])),
        subject=str(row[1]),
        user_id=str(row[2]),
        tenant_id=str(row[3]),
        verified_email=str(row[4]) if row[4] is not None else None,
        issuer=issuer_namespace if issuer_namespace else None,
    )
