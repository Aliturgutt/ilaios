"""Fail-closed export of canonical account data without credential disclosure."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from services.central_identity import CentralIdentityError
from services.control_plane.migrations import migrate_database


class AccountDataExportService:
    """Export one canonical user's identity data from existing persistence."""

    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path
        if migrate_database(database_path) < 10:
            raise CentralIdentityError("commercial identity schema is unavailable")

    def export_my_data(
        self,
        *,
        user_id: str,
        recent_authentication_verified: bool,
        occurred_at: str,
    ) -> dict[str, Any]:
        user = user_id.strip()
        timestamp = occurred_at.strip()
        if not user or not timestamp:
            raise CentralIdentityError("account export context is incomplete")
        if not recent_authentication_verified:
            self._audit(user, timestamp, "DENIED", "recent_auth_required")
            raise CentralIdentityError("recent authentication is required")

        with self._connect() as connection:
            user_row = connection.execute(
                "SELECT enabled, created_at, updated_at FROM identity_users WHERE user_id = ?",
                (user,),
            ).fetchone()
            if user_row is None:
                self._audit_in_transaction(
                    connection, user, timestamp, "DENIED", "user_not_found"
                )
                raise CentralIdentityError("account does not exist")

            memberships = [
                {
                    "tenant_id": row[0],
                    "role": row[1],
                    "status": row[2],
                    "is_primary": bool(row[3]),
                    "created_at": row[4],
                    "updated_at": row[5],
                }
                for row in connection.execute(
                    "SELECT tenant_id, role, status, is_primary, created_at, updated_at "
                    "FROM identity_memberships WHERE user_id = ? ORDER BY tenant_id",
                    (user,),
                ).fetchall()
            ]
            identities = [
                {
                    "provider": row[0],
                    "issuer_namespace": row[1],
                    "provider_subject": row[2],
                    "tenant_id": row[3],
                    "verified_email": row[4],
                    "created_at": row[5],
                    "updated_at": row[6],
                }
                for row in connection.execute(
                    "SELECT provider, issuer_namespace, provider_subject, tenant_id, "
                    "verified_email, created_at, updated_at FROM identity_accounts "
                    "WHERE user_id = ? ORDER BY provider, issuer_namespace, provider_subject",
                    (user,),
                ).fetchall()
            ]
            sessions = [
                {
                    "tenant_id": row[0],
                    "created_at": row[1],
                    "expires_at": row[2],
                    "revoked_at": row[3],
                }
                for row in connection.execute(
                    "SELECT tenant_id, created_at, expires_at, revoked_at "
                    "FROM identity_sessions WHERE user_id = ? "
                    "ORDER BY created_at, tenant_id",
                    (user,),
                ).fetchall()
            ]
            audit_events = [
                {"event_type": row[0], "occurred_at": row[1]}
                for row in connection.execute(
                    "SELECT event_type, occurred_at FROM events "
                    "WHERE aggregate_id = ? AND event_type LIKE 'identity.%' "
                    "ORDER BY sequence",
                    (user,),
                ).fetchall()
            ]

            export: dict[str, Any] = {
                "schema_version": "ilaios.account-export.v1",
                "exported_at": timestamp,
                "user": {
                    "user_id": user,
                    "enabled": bool(user_row[0]),
                    "created_at": user_row[1],
                    "updated_at": user_row[2],
                },
                "memberships": memberships,
                "linked_identities": identities,
                "sessions": sessions,
                "audit_events": audit_events,
            }
            self._audit_in_transaction(
                connection,
                user,
                timestamp,
                "SUCCESS",
                "export_created",
                memberships=len(memberships),
                linked_identities=len(identities),
                sessions=len(sessions),
                audit_events=len(audit_events),
            )
            return export

    def _audit(self, user: str, timestamp: str, status: str, reason: str) -> None:
        with self._connect() as connection:
            self._audit_in_transaction(connection, user, timestamp, status, reason)

    @staticmethod
    def _audit_in_transaction(
        connection: sqlite3.Connection,
        user: str,
        timestamp: str,
        status: str,
        reason: str,
        *,
        memberships: int = 0,
        linked_identities: int = 0,
        sessions: int = 0,
        audit_events: int = 0,
    ) -> None:
        payload = json.dumps(
            {
                "action": "export_my_data",
                "status": status,
                "user_id": user,
                "reason": reason,
                "memberships": memberships,
                "linked_identities": linked_identities,
                "sessions": sessions,
                "audit_events": audit_events,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        connection.execute(
            "INSERT INTO events (event_type, aggregate_id, payload_json, occurred_at, schema_version) "
            "VALUES ('identity.export_my_data', ?, ?, ?, '1')",
            (user, payload, timestamp),
        )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path)
        connection.execute("PRAGMA foreign_keys = ON")
        return connection
