"""Fail-closed self-service account deletion on canonical identity persistence."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from services.central_identity import CentralIdentityError
from services.control_plane.migrations import migrate_database


class AccountDeletionService:
    """Close one canonical user account without creating parallel identity authority."""

    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path
        if migrate_database(database_path) < 9:
            raise CentralIdentityError("commercial identity schema is unavailable")

    def delete_account(
        self,
        *,
        user_id: str,
        recent_authentication_verified: bool,
        deletion_confirmation_verified: bool,
        occurred_at: str,
    ) -> tuple[int, int, int]:
        user = user_id.strip()
        timestamp = occurred_at.strip()
        if not user or not timestamp:
            raise CentralIdentityError("account deletion context is incomplete")
        if not recent_authentication_verified:
            self._audit_denied(user, timestamp, "recent_auth_required")
            raise CentralIdentityError("recent authentication is required")
        if not deletion_confirmation_verified:
            self._audit_denied(user, timestamp, "confirmation_required")
            raise CentralIdentityError("explicit account deletion confirmation is required")

        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            user_row = connection.execute(
                "SELECT enabled FROM identity_users WHERE user_id = ?",
                (user,),
            ).fetchone()
            if user_row is None or int(user_row[0]) != 1:
                self._audit_in_transaction(
                    connection, user, timestamp, "DENIED", "user_not_active"
                )
                connection.commit()
                raise CentralIdentityError("account is not active")

            owner_memberships = connection.execute(
                "SELECT tenant_id FROM identity_memberships "
                "WHERE user_id = ? AND role = 'OWNER' AND status = 'ACTIVE'",
                (user,),
            ).fetchall()
            if owner_memberships:
                self._audit_in_transaction(
                    connection, user, timestamp, "DENIED", "active_owner_membership"
                )
                connection.commit()
                raise CentralIdentityError(
                    "account deletion requires transferring or closing active owner memberships"
                )

            revoked_memberships = connection.execute(
                "UPDATE identity_memberships SET status = 'REVOKED', updated_at = ? "
                "WHERE user_id = ? AND status != 'REVOKED'",
                (timestamp, user),
            ).rowcount
            revoked_sessions = connection.execute(
                "UPDATE identity_sessions SET revoked_at = ? "
                "WHERE user_id = ? AND revoked_at IS NULL",
                (timestamp, user),
            ).rowcount
            deleted_identities = connection.execute(
                "DELETE FROM identity_accounts WHERE user_id = ?",
                (user,),
            ).rowcount
            disabled = connection.execute(
                "UPDATE identity_users SET enabled = 0, updated_at = ? "
                "WHERE user_id = ? AND enabled = 1",
                (timestamp, user),
            ).rowcount
            if disabled != 1:
                raise CentralIdentityError("account deletion failed closed")

            self._audit_in_transaction(
                connection,
                user,
                timestamp,
                "SUCCESS",
                "account_closed",
                revoked_memberships=revoked_memberships,
                revoked_sessions=revoked_sessions,
                deleted_identities=deleted_identities,
            )
            return revoked_memberships, revoked_sessions, deleted_identities

    def _audit_denied(self, user: str, timestamp: str, reason: str) -> None:
        with self._connect() as connection:
            self._audit_in_transaction(connection, user, timestamp, "DENIED", reason)

    @staticmethod
    def _audit_in_transaction(
        connection: sqlite3.Connection,
        user: str,
        timestamp: str,
        status: str,
        reason: str,
        *,
        revoked_memberships: int = 0,
        revoked_sessions: int = 0,
        deleted_identities: int = 0,
    ) -> None:
        payload = json.dumps(
            {
                "action": "account_delete",
                "status": status,
                "user_id": user,
                "reason": reason,
                "revoked_memberships": revoked_memberships,
                "revoked_sessions": revoked_sessions,
                "deleted_identities": deleted_identities,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        connection.execute(
            "INSERT INTO events (event_type, aggregate_id, payload_json, occurred_at, schema_version) "
            "VALUES ('identity.account_delete', ?, ?, ?, '1')",
            (user, payload, timestamp),
        )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path)
        connection.execute("PRAGMA foreign_keys = ON")
        return connection
