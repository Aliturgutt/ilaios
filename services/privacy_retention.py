"""Fail-closed privacy-retention cleanup for closed canonical identity accounts."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

from services.central_identity import CentralIdentityError
from services.control_plane.migrations import migrate_database


class PrivacyRetentionService:
    """Purge closed-account operational identity rows after an explicit retention window."""

    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path
        if migrate_database(database_path) < 10:
            raise CentralIdentityError("commercial identity schema is unavailable")

    def purge_closed_account(
        self,
        *,
        user_id: str,
        retention_cutoff: str,
        privacy_deletion_confirmed: bool,
        occurred_at: str,
    ) -> tuple[int, int, int]:
        user = user_id.strip()
        cutoff = retention_cutoff.strip()
        timestamp = occurred_at.strip()
        if not user or not cutoff or not timestamp:
            raise CentralIdentityError("privacy deletion context is incomplete")
        if not privacy_deletion_confirmed:
            self._audit_denied(user, timestamp, "confirmation_required")
            raise CentralIdentityError("explicit privacy deletion confirmation is required")

        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            user_row = connection.execute(
                "SELECT enabled, updated_at FROM identity_users WHERE user_id = ?",
                (user,),
            ).fetchone()
            if user_row is None:
                self._audit_in_transaction(
                    connection, user, timestamp, "DENIED", "user_not_found"
                )
                connection.commit()
                raise CentralIdentityError("account is not available for privacy deletion")
            if int(user_row[0]) != 0:
                self._audit_in_transaction(
                    connection, user, timestamp, "DENIED", "account_not_closed"
                )
                connection.commit()
                raise CentralIdentityError("account must be closed before privacy deletion")
            if str(user_row[1]) > cutoff:
                self._audit_in_transaction(
                    connection, user, timestamp, "DENIED", "retention_window_active"
                )
                connection.commit()
                raise CentralIdentityError("retention window has not elapsed")

            prior_delete = connection.execute(
                "SELECT 1 FROM events "
                "WHERE event_type = 'identity.account_delete' AND aggregate_id = ? "
                "AND json_extract(payload_json, '$.status') = 'SUCCESS' LIMIT 1",
                (user,),
            ).fetchone()
            if prior_delete is None:
                self._audit_in_transaction(
                    connection, user, timestamp, "DENIED", "account_delete_evidence_missing"
                )
                connection.commit()
                raise CentralIdentityError("account deletion evidence is required")

            active_membership = connection.execute(
                "SELECT 1 FROM identity_memberships "
                "WHERE user_id = ? AND status != 'REVOKED' LIMIT 1",
                (user,),
            ).fetchone()
            active_session = connection.execute(
                "SELECT 1 FROM identity_sessions "
                "WHERE user_id = ? AND revoked_at IS NULL LIMIT 1",
                (user,),
            ).fetchone()
            linked_identity = connection.execute(
                "SELECT 1 FROM identity_accounts WHERE user_id = ? LIMIT 1",
                (user,),
            ).fetchone()
            if active_membership or active_session or linked_identity:
                self._audit_in_transaction(
                    connection, user, timestamp, "DENIED", "operational_identity_still_active"
                )
                connection.commit()
                raise CentralIdentityError("operational identity rows must be revoked first")

            deleted_sessions = connection.execute(
                "DELETE FROM identity_sessions WHERE user_id = ?",
                (user,),
            ).rowcount
            deleted_memberships = connection.execute(
                "DELETE FROM identity_memberships WHERE user_id = ?",
                (user,),
            ).rowcount
            deleted_user = connection.execute(
                "DELETE FROM identity_users WHERE user_id = ? AND enabled = 0",
                (user,),
            ).rowcount
            if deleted_user != 1:
                raise CentralIdentityError("privacy deletion failed closed")

            self._audit_in_transaction(
                connection,
                user,
                timestamp,
                "SUCCESS",
                "retention_elapsed",
                deleted_sessions=deleted_sessions,
                deleted_memberships=deleted_memberships,
                deleted_user=deleted_user,
            )
            return deleted_sessions, deleted_memberships, deleted_user

    def purge_expired_email_challenges(
        self, *, retention_cutoff: str, occurred_at: str
    ) -> int:
        cutoff = retention_cutoff.strip()
        timestamp = occurred_at.strip()
        if not cutoff or not timestamp:
            raise CentralIdentityError("email challenge retention context is incomplete")
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            deleted = connection.execute(
                "DELETE FROM identity_email_challenges WHERE expires_at <= ?",
                (cutoff,),
            ).rowcount
            payload = json.dumps(
                {
                    "action": "email_challenge_retention",
                    "status": "SUCCESS",
                    "deleted_challenges": deleted,
                },
                sort_keys=True,
                separators=(",", ":"),
            )
            connection.execute(
                "INSERT INTO events "
                "(event_type, aggregate_id, payload_json, occurred_at, schema_version) "
                "VALUES ('identity.email_challenge_retention', 'system', ?, ?, '1')",
                (payload, timestamp),
            )
            return deleted

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
        deleted_sessions: int = 0,
        deleted_memberships: int = 0,
        deleted_user: int = 0,
    ) -> None:
        user_digest = hashlib.sha256(user.encode("utf-8")).hexdigest()
        payload = json.dumps(
            {
                "action": "privacy_retention_delete",
                "status": status,
                "reason": reason,
                "user_sha256": user_digest,
                "deleted_sessions": deleted_sessions,
                "deleted_memberships": deleted_memberships,
                "deleted_user": deleted_user,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        connection.execute(
            "INSERT INTO events "
            "(event_type, aggregate_id, payload_json, occurred_at, schema_version) "
            "VALUES ('identity.privacy_retention_delete', ?, ?, ?, '1')",
            (user_digest, payload, timestamp),
        )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path)
        connection.execute("PRAGMA foreign_keys = ON")
        return connection
