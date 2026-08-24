from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from services.account_data_export import AccountDataExportService
from services.central_identity import CentralIdentityError
from services.control_plane.migrations import migrate_database

NOW = "2026-08-24T14:00:00Z"


def _seed(path: Path) -> None:
    assert migrate_database(path) >= 10
    with sqlite3.connect(path) as connection:
        connection.execute(
            "INSERT INTO identity_tenants (tenant_id, status, created_at, updated_at) "
            "VALUES ('tenant-a', 'ACTIVE', ?, ?), ('tenant-b', 'ACTIVE', ?, ?)",
            (NOW, NOW, NOW, NOW),
        )
        connection.execute(
            "INSERT INTO identity_users (user_id, enabled, created_at, updated_at) "
            "VALUES ('user-a', 1, ?, ?), ('user-b', 1, ?, ?)",
            (NOW, NOW, NOW, NOW),
        )
        connection.execute(
            "INSERT INTO identity_memberships "
            "(tenant_id, user_id, role, status, is_primary, created_at, updated_at) VALUES "
            "('tenant-a', 'user-a', 'OWNER', 'ACTIVE', 1, ?, ?), "
            "('tenant-b', 'user-b', 'OWNER', 'ACTIVE', 1, ?, ?)",
            (NOW, NOW, NOW, NOW),
        )
        connection.execute(
            "INSERT INTO identity_accounts "
            "(identity_account_id, provider, issuer_namespace, provider_subject, user_id, tenant_id, verified_email, created_at, updated_at) "
            "VALUES ('ia-a', 'GOOGLE', '', 'google-sub-a', 'user-a', 'tenant-a', 'a@example.com', ?, ?), "
            "('ia-b', 'GOOGLE', '', 'google-sub-b', 'user-b', 'tenant-b', 'b@example.com', ?, ?)",
            (NOW, NOW, NOW, NOW),
        )
        connection.execute(
            "INSERT INTO identity_sessions "
            "(session_id, user_id, tenant_id, credential_hash, created_at, expires_at, revoked_at) "
            "VALUES ('session-secret-a', 'user-a', 'tenant-a', ?, ?, '2026-08-25T14:00:00Z', NULL), "
            "('session-secret-b', 'user-b', 'tenant-b', ?, ?, '2026-08-25T14:00:00Z', NULL)",
            ("a" * 64, NOW, "b" * 64, NOW),
        )
        connection.execute(
            "INSERT INTO events (event_type, aggregate_id, payload_json, occurred_at, schema_version) "
            "VALUES ('identity.account_link', 'user-a', '{\"secret\":\"do-not-export\"}', ?, '1'), "
            "('identity.account_link', 'user-b', '{\"secret\":\"other-user\"}', ?, '1')",
            (NOW, NOW),
        )


def test_export_my_data_is_user_scoped_and_excludes_credentials(tmp_path: Path) -> None:
    database = tmp_path / "identity.sqlite3"
    _seed(database)

    export = AccountDataExportService(database).export_my_data(
        user_id="user-a",
        recent_authentication_verified=True,
        occurred_at="2026-08-24T14:05:00Z",
    )

    assert export["schema_version"] == "ilaios.account-export.v1"
    assert export["user"] == {
        "user_id": "user-a",
        "enabled": True,
        "created_at": NOW,
        "updated_at": NOW,
    }
    assert [membership["tenant_id"] for membership in export["memberships"]] == [
        "tenant-a"
    ]
    assert export["linked_identities"][0]["provider_subject"] == "google-sub-a"
    assert export["sessions"] == [
        {
            "tenant_id": "tenant-a",
            "created_at": NOW,
            "expires_at": "2026-08-25T14:00:00Z",
            "revoked_at": None,
        }
    ]

    serialized = json.dumps(export, sort_keys=True)
    assert "session-secret-a" not in serialized
    assert "a" * 64 not in serialized
    assert "do-not-export" not in serialized
    assert "user-b" not in serialized
    assert "google-sub-b" not in serialized
    assert "other-user" not in serialized


def test_export_requires_recent_authentication_and_audits_denial(tmp_path: Path) -> None:
    database = tmp_path / "identity.sqlite3"
    _seed(database)
    service = AccountDataExportService(database)

    with pytest.raises(CentralIdentityError, match="recent authentication"):
        service.export_my_data(
            user_id="user-a",
            recent_authentication_verified=False,
            occurred_at="2026-08-24T14:05:00Z",
        )

    with sqlite3.connect(database) as connection:
        payload = connection.execute(
            "SELECT payload_json FROM events WHERE event_type = 'identity.export_my_data' "
            "ORDER BY sequence DESC LIMIT 1"
        ).fetchone()
    assert payload is not None
    parsed = json.loads(payload[0])
    assert parsed["status"] == "DENIED"
    assert parsed["reason"] == "recent_auth_required"


def test_export_success_audit_contains_counts_not_exported_secrets(tmp_path: Path) -> None:
    database = tmp_path / "identity.sqlite3"
    _seed(database)

    AccountDataExportService(database).export_my_data(
        user_id="user-a",
        recent_authentication_verified=True,
        occurred_at="2026-08-24T14:05:00Z",
    )

    with sqlite3.connect(database) as connection:
        payload = connection.execute(
            "SELECT payload_json FROM events WHERE event_type = 'identity.export_my_data' "
            "ORDER BY sequence DESC LIMIT 1"
        ).fetchone()
    assert payload is not None
    parsed = json.loads(payload[0])
    assert parsed == {
        "action": "export_my_data",
        "audit_events": 1,
        "linked_identities": 1,
        "memberships": 1,
        "reason": "export_created",
        "sessions": 1,
        "status": "SUCCESS",
        "user_id": "user-a",
    }
    assert "session-secret-a" not in payload[0]
    assert "google-sub-a" not in payload[0]


def test_export_unknown_account_fails_closed(tmp_path: Path) -> None:
    database = tmp_path / "identity.sqlite3"
    _seed(database)

    with pytest.raises(CentralIdentityError, match="does not exist"):
        AccountDataExportService(database).export_my_data(
            user_id="missing-user",
            recent_authentication_verified=True,
            occurred_at="2026-08-24T14:05:00Z",
        )
