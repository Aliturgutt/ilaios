"""Fail-closed company-departure lifecycle on canonical identity persistence."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from services.central_identity import CentralIdentityError
from services.control_plane.migrations import migrate_database


class AccountDepartureService:
    """Revoke one tenant membership and its sessions without creating new authority."""

    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path
        if migrate_database(database_path) < 9:
            raise CentralIdentityError("commercial identity schema is unavailable")

    def depart_member(
        self,
        *,
        actor_user_id: str,
        tenant_id: str,
        target_user_id: str,
        recent_authentication_verified: bool,
        occurred_at: str,
    ) -> int:
        actor = actor_user_id.strip()
        tenant = tenant_id.strip()
        target = target_user_id.strip()
        timestamp = occurred_at.strip()
        if not actor or not tenant or not target or not timestamp:
            raise CentralIdentityError("departure context is incomplete")
        if not recent_authentication_verified:
            self._audit_denied(actor, tenant, target, timestamp, "recent_auth_required")
            raise CentralIdentityError("recent authentication is required")

        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            actor_row = connection.execute(
                "SELECT role, status FROM identity_memberships "
                "WHERE tenant_id = ? AND user_id = ?",
                (tenant, actor),
            ).fetchone()
            if actor_row is None or actor_row[1] != "ACTIVE" or actor_row[0] not in {
                "OWNER",
                "ADMIN",
            }:
                self._audit_in_transaction(
                    connection, actor, tenant, target, timestamp, "DENIED", "actor_not_authorized"
                )
                raise CentralIdentityError("departure actor is not authorized")

            target_row = connection.execute(
                "SELECT role, status FROM identity_memberships "
                "WHERE tenant_id = ? AND user_id = ?",
                (tenant, target),
            ).fetchone()
            if target_row is None or target_row[1] != "ACTIVE":
                self._audit_in_transaction(
                    connection, actor, tenant, target, timestamp, "DENIED", "target_not_active"
                )
                raise CentralIdentityError("target membership is not active")

            if target_row[0] == "OWNER":
                owner_count_row = connection.execute(
                    "SELECT COUNT(*) FROM identity_memberships "
                    "WHERE tenant_id = ? AND role = 'OWNER' AND status = 'ACTIVE'",
                    (tenant,),
                ).fetchone()
                if owner_count_row is None or int(owner_count_row[0]) <= 1:
                    self._audit_in_transaction(
                        connection, actor, tenant, target, timestamp, "DENIED", "last_owner"
                    )
                    raise CentralIdentityError("cannot remove the last active tenant owner")

            cursor = connection.execute(
                "UPDATE identity_memberships SET status = 'REVOKED', updated_at = ? "
                "WHERE tenant_id = ? AND user_id = ? AND status = 'ACTIVE'",
                (timestamp, tenant, target),
            )
            if cursor.rowcount != 1:
                raise CentralIdentityError("membership revocation failed closed")
            sessions = connection.execute(
                "UPDATE identity_sessions SET revoked_at = ? "
                "WHERE tenant_id = ? AND user_id = ? AND revoked_at IS NULL",
                (timestamp, tenant, target),
            ).rowcount
            remaining = connection.execute(
                "SELECT COUNT(*) FROM identity_memberships "
                "WHERE user_id = ? AND status = 'ACTIVE'",
                (target,),
            ).fetchone()
            if remaining is not None and int(remaining[0]) == 0:
                connection.execute(
                    "UPDATE identity_users SET enabled = 0, updated_at = ? WHERE user_id = ?",
                    (timestamp, target),
                )
            self._audit_in_transaction(
                connection, actor, tenant, target, timestamp, "SUCCESS", "membership_revoked",
                revoked_sessions=sessions,
            )
            return sessions

    def _audit_denied(
        self, actor: str, tenant: str, target: str, timestamp: str, reason: str
    ) -> None:
        with self._connect() as connection:
            self._audit_in_transaction(
                connection, actor, tenant, target, timestamp, "DENIED", reason
            )

    @staticmethod
    def _audit_in_transaction(
        connection: sqlite3.Connection,
        actor: str,
        tenant: str,
        target: str,
        timestamp: str,
        status: str,
        reason: str,
        *,
        revoked_sessions: int = 0,
    ) -> None:
        payload = json.dumps(
            {
                "action": "member_departure",
                "status": status,
                "actor_user_id": actor,
                "target_user_id": target,
                "tenant_id": tenant,
                "reason": reason,
                "revoked_sessions": revoked_sessions,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        connection.execute(
            "INSERT INTO events (event_type, aggregate_id, payload_json, occurred_at, schema_version) "
            "VALUES ('identity.member_departure', ?, ?, ?, '1')",
            (tenant, payload, timestamp),
        )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path)
        connection.execute("PRAGMA foreign_keys = ON")
        return connection
