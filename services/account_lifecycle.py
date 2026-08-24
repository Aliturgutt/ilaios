"""Authenticated account-link lifecycle boundary for commercial identity.

This module extends the existing canonical central identity authority without
creating a parallel identity store. Linking remains owned by
``CentralIdentityService``. This boundary adds sensitive account recovery and
unlink operations plus durable audit projection into the existing canonical
control-plane ``events`` table.

Email/login metadata is never used as an account key. Provider immutable keys
remain the only external identity authority.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
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


class AccountLifecycleAuditStore(Protocol):
    """Durable projection boundary for sensitive account lifecycle events."""

    def record(
        self,
        *,
        action: str,
        status: str,
        user_id: str | None,
        tenant_id: str | None,
        identity: VerifiedExternalIdentity,
    ) -> None: ...


class AccountLifecycleService:
    """Fail-closed account recovery and unlinking policy."""

    def __init__(
        self,
        *,
        identity_store: CentralIdentityStore,
        removal_store: IdentityLinkRemovalStore,
        audit_store: AccountLifecycleAuditStore | None = None,
    ) -> None:
        self._identity_store = identity_store
        self._removal_store = removal_store
        self._audit_store = audit_store

    def recover_existing_account(
        self, identity: VerifiedExternalIdentity
    ) -> CanonicalAccount:
        """Recover only an existing linked account; never create or auto-merge."""

        verified = identity.normalized()
        try:
            link = self._identity_store.find_link(verified)
            if link is None:
                raise CentralIdentityError("recovery identity is not linked")
            account = self._identity_store.get_account(link.user_id)
            if account is None or not account.enabled:
                raise CentralIdentityError("recovery account is unavailable")
            if account.tenant_id != link.tenant_id:
                raise CentralIdentityError("recovery identity tenant mismatch")
        except CentralIdentityError:
            self._audit(
                action="recover_existing_account",
                status="denied",
                user_id=None,
                tenant_id=None,
                identity=verified,
            )
            raise

        self._audit(
            action="recover_existing_account",
            status="success",
            user_id=account.user_id,
            tenant_id=account.tenant_id,
            identity=verified,
        )
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
        target = identity.normalized()
        reauth = reauthenticated_identity.normalized()
        try:
            if not user_id or not tenant_id:
                raise CentralIdentityError("authenticated user and tenant are required")

            account = self._identity_store.get_account(user_id)
            if account is None or not account.enabled:
                raise CentralIdentityError("authenticated account is unavailable")
            if account.tenant_id != tenant_id:
                raise CentralIdentityError("authenticated tenant mismatch")

            if target.key() == reauth.key():
                raise CentralIdentityError(
                    "unlink requires a different re-authenticated identity"
                )

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

            removed = self._removal_store.remove_link_if_alternate_exists(
                user_id=user_id,
                tenant_id=tenant_id,
                identity=target,
            )
        except CentralIdentityError:
            self._audit(
                action="unlink_identity",
                status="denied",
                user_id=user_id or None,
                tenant_id=tenant_id or None,
                identity=target,
            )
            raise

        self._audit(
            action="unlink_identity",
            status="success",
            user_id=user_id,
            tenant_id=tenant_id,
            identity=target,
        )
        return removed

    def _audit(
        self,
        *,
        action: str,
        status: str,
        user_id: str | None,
        tenant_id: str | None,
        identity: VerifiedExternalIdentity,
    ) -> None:
        if self._audit_store is None:
            return
        self._audit_store.record(
            action=action,
            status=status,
            user_id=user_id,
            tenant_id=tenant_id,
            identity=identity,
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


class SQLiteAccountLifecycleAuditStore:
    """Append lifecycle events to the canonical persistent control-plane event log."""

    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path
        version = migrate_database(database_path)
        if version < 1:
            raise CentralIdentityError("canonical audit event store is unavailable")

    def record(
        self,
        *,
        action: str,
        status: str,
        user_id: str | None,
        tenant_id: str | None,
        identity: VerifiedExternalIdentity,
    ) -> None:
        if status not in {"success", "denied"}:
            raise CentralIdentityError("unsupported account lifecycle audit status")
        verified = identity.normalized()
        payload = {
            "action": action,
            "status": status,
            "user_id": user_id,
            "tenant_id": tenant_id,
            "provider": verified.provider.value,
            "identity_key_sha256": _identity_key_digest(verified),
        }
        aggregate_id = user_id or _identity_key_digest(verified)
        occurred_at = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self._database_path) as connection:
            connection.execute(
                "INSERT INTO events "
                "(event_type, aggregate_id, payload_json, occurred_at, schema_version) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    "identity.account_lifecycle",
                    aggregate_id,
                    json.dumps(payload, sort_keys=True, separators=(",", ":")),
                    occurred_at,
                    "account-lifecycle.v1",
                ),
            )


def _identity_key_digest(identity: VerifiedExternalIdentity) -> str:
    provider, issuer_namespace, subject = identity.key()
    material = "\x1f".join((provider.value, issuer_namespace, subject)).encode("utf-8")
    return hashlib.sha256(material).hexdigest()


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
