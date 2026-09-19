"""Fail-closed tenant closure on canonical identity persistence."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from services.central_identity import CentralIdentityError
from services.control_plane.migrations import migrate_database


class TenantDeletionService:
    """Close one canonical tenant without creating parallel lifecycle authority."""

    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path
        if migrate_database(database_path) < 9:
            raise CentralIdentityError("commercial identity schema is unavailable")

    def delete_tenant(
        self,
        *,
        actor_user_id: str,
        tenant_id: str,
        recent_authentication_verified: bool,
        deletion_confirmation_verified: bool,
        occurred_at: str,
    ) -> tuple[int, int, int, int]:
        actor = actor_user_id.strip()
        tenant = tenant_id.strip()
        timestamp = occurred_at.strip()
        if not actor or not tenant or not timestamp:
            raise CentralIdentityError("tenant deletion context is incomplete")
        if not recent_authentication_verified:
            self._audit_denied(actor, tenant, timestamp, "recent_auth_required")
            raise CentralIdentityError("recent authentication is required")
        if not deletion_confirmation_verified:
            self._audit_denied(actor, tenant, timestamp, "confirmation_required")
            raise CentralIdentityError("explicit tenant deletion confirmation is required")

        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            tenant_row = connection.execute(
                "SELECT status FROM identity_tenants WHERE tenant_id = ?",
                (tenant,),
            ).fetchone()
            if tenant_row is None or tenant_row[0] != "ACTIVE":
                self._audit_in_transaction(
                    connection, actor, tenant, timestamp, "DENIED", "tenant_not_active"
                )
                connection.commit()
                raise CentralIdentityError("tenant is not active")

            actor_row = connection.execute(
                "SELECT role, status FROM identity_memberships "
                "WHERE tenant_id = ? AND user_id = ?",
                (tenant, actor),
            ).fetchone()
            if actor_row is None or actor_row[1] != "ACTIVE" or actor_row[0] != "OWNER":
                self._audit_in_transaction(
                    connection, actor, tenant, timestamp, "DENIED", "actor_not_owner"
                )
                connection.commit()
                raise CentralIdentityError("tenant deletion requires an active tenant owner")

            revoked_memberships = connection.execute(
                "UPDATE identity_memberships SET status = 'REVOKED', updated_at = ? "
                "WHERE tenant_id = ? AND status != 'REVOKED'",
                (timestamp, tenant),
            ).rowcount
            revoked_sessions = connection.execute(
                "UPDATE identity_sessions SET revoked_at = ? "
                "WHERE tenant_id = ? AND revoked_at IS NULL",
                (timestamp, tenant),
            ).rowcount
            revoked_entitlements = connection.execute(
                "UPDATE identity_entitlements SET state = 'REVOKED', updated_at = ? "
                "WHERE tenant_id = ? AND state != 'REVOKED'",
                (timestamp, tenant),
            ).rowcount
            suspended = connection.execute(
                "UPDATE identity_tenants SET status = 'SUSPENDED', updated_at = ? "
                "WHERE tenant_id = ? AND status = 'ACTIVE'",
                (timestamp, tenant),
            ).rowcount
            if suspended != 1:
                raise CentralIdentityError("tenant deletion failed closed")

            disabled_users = 0
            tenant_users = connection.execute(
                "SELECT DISTINCT user_id FROM identity_memberships WHERE tenant_id = ?",
                (tenant,),
            ).fetchall()
            for row in tenant_users:
                user_id = str(row[0])
                remaining = connection.execute(
                    "SELECT COUNT(*) FROM identity_memberships "
                    "WHERE user_id = ? AND status = 'ACTIVE'",
                    (user_id,),
                ).fetchone()
                if remaining is not None and int(remaining[0]) == 0:
                    disabled_users += connection.execute(
                        "UPDATE identity_users SET enabled = 0, updated_at = ? "
                        "WHERE user_id = ? AND enabled = 1",
                        (timestamp, user_id),
                    ).rowcount

            self._audit_in_transaction(
                connection,
                actor,
                tenant,
                timestamp,
                "SUCCESS",
                "tenant_closed",
                revoked_memberships=revoked_memberships,
                revoked_sessions=revoked_sessions,
                revoked_entitlements=revoked_entitlements,
                disabled_users=disabled_users,
            )
            return (
                revoked_memberships,
                revoked_sessions,
                revoked_entitlements,
                disabled_users,
            )

    def _audit_denied(self, actor: str, tenant: str, timestamp: str, reason: str) -> None:
        with self._connect() as connection:
            self._audit_in_transaction(
                connection, actor, tenant, timestamp, "DENIED", reason
            )

    @staticmethod
    def _audit_in_transaction(
        connection: sqlite3.Connection,
        actor: str,
        tenant: str,
        timestamp: str,
        status: str,
        reason: str,
        *,
        revoked_memberships: int = 0,
        revoked_sessions: int = 0,
        revoked_entitlements: int = 0,
        disabled_users: int = 0,
    ) -> None:
        payload = json.dumps(
            {
                "action": "tenant_delete",
                "status": status,
                "actor_user_id": actor,
                "tenant_id": tenant,
                "reason": reason,
                "revoked_memberships": revoked_memberships,
                "revoked_sessions": revoked_sessions,
                "revoked_entitlements": revoked_entitlements,
                "disabled_users": disabled_users,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        connection.execute(
            "INSERT INTO events (event_type, aggregate_id, payload_json, occurred_at, schema_version) "
            "VALUES ('identity.tenant_delete', ?, ?, ?, '1')",
            (tenant, payload, timestamp),
        )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path)
        connection.execute("PRAGMA foreign_keys = ON")
        return connection
