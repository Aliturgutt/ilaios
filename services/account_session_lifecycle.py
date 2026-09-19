"""Authenticated session lifecycle boundary for commercial identity.

This module reuses the canonical commercial identity database and its
``identity_sessions`` table.  It does not create a second session, identity,
audit, or migration authority.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from services.central_identity import CentralIdentityError
from services.central_identity_sqlite import SQLiteCentralIdentityStore
from services.control_plane.migrations import LATEST_SCHEMA_VERSION, migrate_database


class AccountSessionLifecycleService:
    """Fail-closed logout and revoke-all policy for one canonical account."""

    def __init__(
        self,
        *,
        identity_store: SQLiteCentralIdentityStore,
        revocation_store: SQLiteAccountSessionRevocationStore,
        audit_store: SQLiteAccountSessionAuditStore,
    ) -> None:
        self._identity_store = identity_store
        self._revocation_store = revocation_store
        self._audit_store = audit_store

    def logout_session(
        self,
        *,
        authenticated_user_id: str,
        authenticated_tenant_id: str,
        session_id: str,
    ) -> bool:
        """Revoke exactly one session owned by the authenticated account."""

        user_id = authenticated_user_id.strip()
        tenant_id = authenticated_tenant_id.strip()
        normalized_session_id = session_id.strip()
        try:
            self._require_account(user_id=user_id, tenant_id=tenant_id)
            if not normalized_session_id:
                raise CentralIdentityError("session id is required")
            self._revocation_store.revoke_one(
                user_id=user_id,
                tenant_id=tenant_id,
                session_id=normalized_session_id,
            )
        except CentralIdentityError:
            self._audit_store.record(
                action="logout_session",
                status="denied",
                user_id=user_id or None,
                tenant_id=tenant_id or None,
                session_id=normalized_session_id or None,
                revoked_count=None,
            )
            raise

        self._audit_store.record(
            action="logout_session",
            status="success",
            user_id=user_id,
            tenant_id=tenant_id,
            session_id=normalized_session_id,
            revoked_count=1,
        )
        return True

    def revoke_all_sessions(
        self,
        *,
        authenticated_user_id: str,
        authenticated_tenant_id: str,
        recent_authentication_verified: bool,
    ) -> int:
        """Revoke all active sessions after recent authentication proof."""

        user_id = authenticated_user_id.strip()
        tenant_id = authenticated_tenant_id.strip()
        try:
            self._require_account(user_id=user_id, tenant_id=tenant_id)
            if not recent_authentication_verified:
                raise CentralIdentityError("revoke-all requires recent authentication")
            revoked_count = self._revocation_store.revoke_all(
                user_id=user_id,
                tenant_id=tenant_id,
            )
        except CentralIdentityError:
            self._audit_store.record(
                action="revoke_all_sessions",
                status="denied",
                user_id=user_id or None,
                tenant_id=tenant_id or None,
                session_id=None,
                revoked_count=None,
            )
            raise

        self._audit_store.record(
            action="revoke_all_sessions",
            status="success",
            user_id=user_id,
            tenant_id=tenant_id,
            session_id=None,
            revoked_count=revoked_count,
        )
        return revoked_count

    def _require_account(self, *, user_id: str, tenant_id: str) -> None:
        if not user_id or not tenant_id:
            raise CentralIdentityError("authenticated user and tenant are required")
        account = self._identity_store.get_account(user_id)
        if account is None or not account.enabled:
            raise CentralIdentityError("authenticated account is unavailable")
        if account.tenant_id != tenant_id:
            raise CentralIdentityError("authenticated tenant mismatch")


class SQLiteAccountSessionRevocationStore:
    """Atomic revocation mutations against canonical ``identity_sessions``."""

    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path
        version = migrate_database(database_path)
        if version < 9 or LATEST_SCHEMA_VERSION < 9:
            raise CentralIdentityError("commercial identity session schema is unavailable")

    def revoke_one(self, *, user_id: str, tenant_id: str, session_id: str) -> None:
        revoked_at = _now()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT user_id, tenant_id, revoked_at FROM identity_sessions "
                "WHERE session_id = ?",
                (session_id,),
            ).fetchone()
            if row is None:
                raise CentralIdentityError("session is unavailable")
            if str(row[0]) != user_id or str(row[1]) != tenant_id:
                raise CentralIdentityError("session belongs to another canonical account")
            if row[2] is not None:
                raise CentralIdentityError("session is already revoked")
            cursor = connection.execute(
                "UPDATE identity_sessions SET revoked_at = ? "
                "WHERE session_id = ? AND user_id = ? AND tenant_id = ? "
                "AND revoked_at IS NULL",
                (revoked_at, session_id, user_id, tenant_id),
            )
            if cursor.rowcount != 1:
                raise CentralIdentityError("session revoke failed closed")

    def revoke_all(self, *, user_id: str, tenant_id: str) -> int:
        revoked_at = _now()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            cursor = connection.execute(
                "UPDATE identity_sessions SET revoked_at = ? "
                "WHERE user_id = ? AND tenant_id = ? AND revoked_at IS NULL",
                (revoked_at, user_id, tenant_id),
            )
            return int(cursor.rowcount)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path)
        connection.execute("PRAGMA foreign_keys = ON")
        return connection


class SQLiteAccountSessionAuditStore:
    """Project session lifecycle outcomes into the canonical persistent event log."""

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
        session_id: str | None,
        revoked_count: int | None,
    ) -> None:
        if status not in {"success", "denied"}:
            raise CentralIdentityError("unsupported session lifecycle audit status")
        payload: dict[str, object] = {
            "action": action,
            "status": status,
            "user_id": user_id,
            "tenant_id": tenant_id,
            "revoked_count": revoked_count,
        }
        if session_id is not None:
            payload["session_id_sha256"] = hashlib.sha256(session_id.encode("utf-8")).hexdigest()
        aggregate_id = user_id or "identity-session-denied"
        with sqlite3.connect(self._database_path) as connection:
            connection.execute(
                "INSERT INTO events "
                "(event_type, aggregate_id, payload_json, occurred_at, schema_version) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    "identity.account_session_lifecycle",
                    aggregate_id,
                    json.dumps(payload, sort_keys=True, separators=(",", ":")),
                    _now(),
                    "account-session-lifecycle.v1",
                ),
            )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
