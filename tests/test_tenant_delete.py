from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from services.central_identity import CentralIdentityError
from services.control_plane.migrations import migrate_database
from services.tenant_delete import TenantDeletionService

NOW = "2026-08-24T12:30:00Z"


def _seed(database_path: Path) -> None:
    migrate_database(database_path)
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "INSERT INTO identity_tenants (tenant_id, status, created_at, updated_at) "
            "VALUES ('tenant-a', 'ACTIVE', ?, ?), ('tenant-b', 'ACTIVE', ?, ?)",
            (NOW, NOW, NOW, NOW),
        )
        connection.execute(
            "INSERT INTO identity_users (user_id, enabled, created_at, updated_at) VALUES "
            "('owner-a', 1, ?, ?), ('member-a', 1, ?, ?), ('shared-user', 1, ?, ?)",
            (NOW, NOW, NOW, NOW, NOW, NOW),
        )
        connection.execute(
            "INSERT INTO identity_memberships "
            "(tenant_id, user_id, role, status, is_primary, created_at, updated_at) VALUES "
            "('tenant-a', 'owner-a', 'OWNER', 'ACTIVE', 1, ?, ?), "
            "('tenant-a', 'member-a', 'MEMBER', 'ACTIVE', 0, ?, ?), "
            "('tenant-a', 'shared-user', 'MEMBER', 'ACTIVE', 0, ?, ?), "
            "('tenant-b', 'shared-user', 'MEMBER', 'ACTIVE', 1, ?, ?)",
            (NOW, NOW, NOW, NOW, NOW, NOW, NOW, NOW),
        )
        connection.execute(
            "INSERT INTO identity_sessions "
            "(session_id, user_id, tenant_id, credential_hash, created_at, expires_at) VALUES "
            "('session-owner', 'owner-a', 'tenant-a', ?, ?, ?), "
            "('session-member', 'member-a', 'tenant-a', ?, ?, ?), "
            "('session-shared-a', 'shared-user', 'tenant-a', ?, ?, ?), "
            "('session-shared-b', 'shared-user', 'tenant-b', ?, ?, ?)",
            ("a" * 64, NOW, "2026-08-25T12:30:00Z", "b" * 64, NOW, "2026-08-25T12:30:00Z", "c" * 64, NOW, "2026-08-25T12:30:00Z", "d" * 64, NOW, "2026-08-25T12:30:00Z"),
        )
        connection.execute(
            "INSERT INTO identity_entitlements (tenant_id, entitlement_key, state, limit_value, updated_at) "
            "VALUES ('tenant-a', 'plan.pro', 'ACTIVE', 10, ?), "
            "('tenant-b', 'plan.pro', 'ACTIVE', 10, ?)",
            (NOW, NOW),
        )


def test_owner_can_close_tenant_atomically(tmp_path: Path) -> None:
    database_path = tmp_path / "identity.db"
    _seed(database_path)
    service = TenantDeletionService(database_path)

    result = service.delete_tenant(
        actor_user_id="owner-a",
        tenant_id="tenant-a",
        recent_authentication_verified=True,
        deletion_confirmation_verified=True,
        occurred_at=NOW,
    )

    assert result == (3, 3, 1, 2)
    with sqlite3.connect(database_path) as connection:
        assert connection.execute(
            "SELECT status FROM identity_tenants WHERE tenant_id = 'tenant-a'"
        ).fetchone() == ("SUSPENDED",)
        assert connection.execute(
            "SELECT COUNT(*) FROM identity_memberships WHERE tenant_id = 'tenant-a' AND status = 'ACTIVE'"
        ).fetchone() == (0,)
        assert connection.execute(
            "SELECT COUNT(*) FROM identity_sessions WHERE tenant_id = 'tenant-a' AND revoked_at IS NULL"
        ).fetchone() == (0,)
        assert connection.execute(
            "SELECT state FROM identity_entitlements WHERE tenant_id = 'tenant-a' AND entitlement_key = 'plan.pro'"
        ).fetchone() == ("REVOKED",)
        assert connection.execute(
            "SELECT enabled FROM identity_users WHERE user_id = 'owner-a'"
        ).fetchone() == (0,)
        assert connection.execute(
            "SELECT enabled FROM identity_users WHERE user_id = 'member-a'"
        ).fetchone() == (0,)


def test_multi_tenant_user_remains_enabled_and_other_tenant_session_survives(tmp_path: Path) -> None:
    database_path = tmp_path / "identity.db"
    _seed(database_path)
    service = TenantDeletionService(database_path)

    service.delete_tenant(
        actor_user_id="owner-a",
        tenant_id="tenant-a",
        recent_authentication_verified=True,
        deletion_confirmation_verified=True,
        occurred_at=NOW,
    )

    with sqlite3.connect(database_path) as connection:
        assert connection.execute(
            "SELECT enabled FROM identity_users WHERE user_id = 'shared-user'"
        ).fetchone() == (1,)
        assert connection.execute(
            "SELECT status FROM identity_memberships WHERE tenant_id = 'tenant-b' AND user_id = 'shared-user'"
        ).fetchone() == ("ACTIVE",)
        assert connection.execute(
            "SELECT revoked_at FROM identity_sessions WHERE session_id = 'session-shared-b'"
        ).fetchone() == (None,)
        assert connection.execute(
            "SELECT state FROM identity_entitlements WHERE tenant_id = 'tenant-b' AND entitlement_key = 'plan.pro'"
        ).fetchone() == ("ACTIVE",)


def test_non_owner_cannot_close_tenant(tmp_path: Path) -> None:
    database_path = tmp_path / "identity.db"
    _seed(database_path)
    service = TenantDeletionService(database_path)

    with pytest.raises(CentralIdentityError, match="active tenant owner"):
        service.delete_tenant(
            actor_user_id="member-a",
            tenant_id="tenant-a",
            recent_authentication_verified=True,
            deletion_confirmation_verified=True,
            occurred_at=NOW,
        )


def test_owner_cannot_close_a_different_tenant(tmp_path: Path) -> None:
    database_path = tmp_path / "identity.db"
    _seed(database_path)
    service = TenantDeletionService(database_path)

    with pytest.raises(CentralIdentityError, match="active tenant owner"):
        service.delete_tenant(
            actor_user_id="owner-a",
            tenant_id="tenant-b",
            recent_authentication_verified=True,
            deletion_confirmation_verified=True,
            occurred_at=NOW,
        )

    with sqlite3.connect(database_path) as connection:
        assert connection.execute(
            "SELECT status FROM identity_tenants WHERE tenant_id = 'tenant-b'"
        ).fetchone() == ("ACTIVE",)
        assert connection.execute(
            "SELECT revoked_at FROM identity_sessions WHERE session_id = 'session-shared-b'"
        ).fetchone() == (None,)
        assert connection.execute(
            "SELECT state FROM identity_entitlements WHERE tenant_id = 'tenant-b' AND entitlement_key = 'plan.pro'"
        ).fetchone() == ("ACTIVE",)
        payload_text = connection.execute(
            "SELECT payload_json FROM events WHERE event_type = 'identity.tenant_delete' "
            "ORDER BY sequence DESC LIMIT 1"
        ).fetchone()[0]
    payload = json.loads(payload_text)
    assert payload["status"] == "DENIED"
    assert payload["actor_user_id"] == "owner-a"
    assert payload["tenant_id"] == "tenant-b"
    assert payload["reason"] == "actor_not_owner"


def test_recent_auth_and_explicit_confirmation_are_required(tmp_path: Path) -> None:
    database_path = tmp_path / "identity.db"
    _seed(database_path)
    service = TenantDeletionService(database_path)

    with pytest.raises(CentralIdentityError, match="recent authentication"):
        service.delete_tenant(
            actor_user_id="owner-a",
            tenant_id="tenant-a",
            recent_authentication_verified=False,
            deletion_confirmation_verified=True,
            occurred_at=NOW,
        )
    with pytest.raises(CentralIdentityError, match="explicit tenant deletion confirmation"):
        service.delete_tenant(
            actor_user_id="owner-a",
            tenant_id="tenant-a",
            recent_authentication_verified=True,
            deletion_confirmation_verified=False,
            occurred_at=NOW,
        )


def test_closed_or_unknown_tenant_fails_closed(tmp_path: Path) -> None:
    database_path = tmp_path / "identity.db"
    _seed(database_path)
    service = TenantDeletionService(database_path)
    service.delete_tenant(
        actor_user_id="owner-a",
        tenant_id="tenant-a",
        recent_authentication_verified=True,
        deletion_confirmation_verified=True,
        occurred_at=NOW,
    )

    for tenant_id in ("tenant-a", "missing"):
        with pytest.raises(CentralIdentityError, match="tenant is not active"):
            service.delete_tenant(
                actor_user_id="owner-a",
                tenant_id=tenant_id,
                recent_authentication_verified=True,
                deletion_confirmation_verified=True,
                occurred_at=NOW,
            )


def test_audit_is_durable_and_contains_no_session_credentials(tmp_path: Path) -> None:
    database_path = tmp_path / "identity.db"
    _seed(database_path)
    service = TenantDeletionService(database_path)

    service.delete_tenant(
        actor_user_id="owner-a",
        tenant_id="tenant-a",
        recent_authentication_verified=True,
        deletion_confirmation_verified=True,
        occurred_at=NOW,
    )

    with sqlite3.connect(database_path) as connection:
        payload_text = connection.execute(
            "SELECT payload_json FROM events WHERE event_type = 'identity.tenant_delete' "
            "ORDER BY sequence DESC LIMIT 1"
        ).fetchone()[0]
    payload = json.loads(payload_text)
    assert payload["status"] == "SUCCESS"
    assert payload["tenant_id"] == "tenant-a"
    assert payload["revoked_sessions"] == 3
    assert "session-owner" not in payload_text
    assert "credential" not in payload_text
    assert "a" * 64 not in payload_text
