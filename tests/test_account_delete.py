from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from services.account_delete import AccountDeletionService
from services.central_identity import CentralIdentityError
from services.control_plane.migrations import migrate_database

NOW = "2026-08-24T10:20:00Z"


def _seed(path: Path) -> None:
    migrate_database(path)
    with sqlite3.connect(path) as connection:
        connection.execute(
            "INSERT INTO identity_tenants (tenant_id, status, created_at, updated_at) "
            "VALUES ('tnt_main', 'ACTIVE', ?, ?), ('tnt_other', 'ACTIVE', ?, ?)",
            (NOW, NOW, NOW, NOW),
        )
        for user_id in ("usr_member", "usr_owner", "usr_multi"):
            connection.execute(
                "INSERT INTO identity_users (user_id, enabled, created_at, updated_at) "
                "VALUES (?, 1, ?, ?)",
                (user_id, NOW, NOW),
            )
        memberships = (
            ("tnt_main", "usr_member", "MEMBER", "ACTIVE", 1),
            ("tnt_main", "usr_owner", "OWNER", "ACTIVE", 1),
            ("tnt_main", "usr_multi", "MEMBER", "ACTIVE", 1),
            ("tnt_other", "usr_multi", "MEMBER", "SUSPENDED", 0),
        )
        for tenant_id, user_id, role, status, is_primary in memberships:
            connection.execute(
                "INSERT INTO identity_memberships "
                "(tenant_id, user_id, role, status, is_primary, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (tenant_id, user_id, role, status, is_primary, NOW, NOW),
            )
        connection.execute(
            "INSERT INTO identity_accounts "
            "(identity_account_id, provider, issuer_namespace, provider_subject, user_id, tenant_id, verified_email, created_at, updated_at) "
            "VALUES ('acct_member', 'GOOGLE', '', 'google-member', 'usr_member', 'tnt_main', 'member@example.com', ?, ?), "
            "('acct_multi', 'GITHUB', '', '12345', 'usr_multi', 'tnt_main', 'multi@example.com', ?, ?)",
            (NOW, NOW, NOW, NOW),
        )
        connection.execute(
            "INSERT INTO identity_sessions "
            "(session_id, user_id, tenant_id, credential_hash, created_at, expires_at) "
            "VALUES ('sess_member', 'usr_member', 'tnt_main', ?, ?, '2026-08-25T10:20:00Z'), "
            "('sess_multi_main', 'usr_multi', 'tnt_main', ?, ?, '2026-08-25T10:20:00Z'), "
            "('sess_multi_other', 'usr_multi', 'tnt_other', ?, ?, '2026-08-25T10:20:00Z')",
            ("a" * 64, NOW, "b" * 64, NOW, "c" * 64, NOW),
        )


def _events(path: Path) -> list[dict[str, object]]:
    with sqlite3.connect(path) as connection:
        rows = connection.execute(
            "SELECT payload_json FROM events WHERE event_type = 'identity.account_delete' ORDER BY sequence"
        ).fetchall()
    return [json.loads(str(row[0])) for row in rows]


def test_account_delete_revokes_access_removes_login_links_and_disables_user(tmp_path: Path) -> None:
    database = tmp_path / "identity.db"
    _seed(database)

    counts = AccountDeletionService(database).delete_account(
        user_id="usr_member",
        recent_authentication_verified=True,
        deletion_confirmation_verified=True,
        occurred_at=NOW,
    )

    assert counts == (1, 1, 1)
    with sqlite3.connect(database) as connection:
        membership = connection.execute(
            "SELECT status FROM identity_memberships WHERE tenant_id='tnt_main' AND user_id='usr_member'"
        ).fetchone()
        session = connection.execute(
            "SELECT revoked_at FROM identity_sessions WHERE session_id='sess_member'"
        ).fetchone()
        account_count = connection.execute(
            "SELECT COUNT(*) FROM identity_accounts WHERE user_id='usr_member'"
        ).fetchone()
        enabled = connection.execute(
            "SELECT enabled FROM identity_users WHERE user_id='usr_member'"
        ).fetchone()
    assert membership == ("REVOKED",)
    assert session == (NOW,)
    assert account_count == (0,)
    assert enabled == (0,)
    payload = _events(database)[-1]
    assert payload["status"] == "SUCCESS"
    assert payload["deleted_identities"] == 1


def test_account_delete_requires_recent_auth_and_explicit_confirmation(tmp_path: Path) -> None:
    database = tmp_path / "identity.db"
    _seed(database)
    service = AccountDeletionService(database)

    with pytest.raises(CentralIdentityError, match="recent authentication"):
        service.delete_account(
            user_id="usr_member",
            recent_authentication_verified=False,
            deletion_confirmation_verified=True,
            occurred_at=NOW,
        )
    with pytest.raises(CentralIdentityError, match="explicit account deletion confirmation"):
        service.delete_account(
            user_id="usr_member",
            recent_authentication_verified=True,
            deletion_confirmation_verified=False,
            occurred_at=NOW,
        )

    reasons = [payload["reason"] for payload in _events(database)]
    assert reasons == ["recent_auth_required", "confirmation_required"]


def test_account_delete_denies_active_owner_to_prevent_tenant_lockout(tmp_path: Path) -> None:
    database = tmp_path / "identity.db"
    _seed(database)

    with pytest.raises(CentralIdentityError, match="active owner memberships"):
        AccountDeletionService(database).delete_account(
            user_id="usr_owner",
            recent_authentication_verified=True,
            deletion_confirmation_verified=True,
            occurred_at=NOW,
        )

    with sqlite3.connect(database) as connection:
        enabled = connection.execute(
            "SELECT enabled FROM identity_users WHERE user_id='usr_owner'"
        ).fetchone()
        membership = connection.execute(
            "SELECT status FROM identity_memberships WHERE tenant_id='tnt_main' AND user_id='usr_owner'"
        ).fetchone()
    assert enabled == (1,)
    assert membership == ("ACTIVE",)
    assert _events(database)[-1]["reason"] == "active_owner_membership"


def test_account_delete_revokes_all_memberships_and_sessions_across_tenants(tmp_path: Path) -> None:
    database = tmp_path / "identity.db"
    _seed(database)

    counts = AccountDeletionService(database).delete_account(
        user_id="usr_multi",
        recent_authentication_verified=True,
        deletion_confirmation_verified=True,
        occurred_at=NOW,
    )

    assert counts == (2, 2, 1)
    with sqlite3.connect(database) as connection:
        memberships = connection.execute(
            "SELECT tenant_id, status FROM identity_memberships WHERE user_id='usr_multi' ORDER BY tenant_id"
        ).fetchall()
        sessions = connection.execute(
            "SELECT session_id, revoked_at FROM identity_sessions WHERE user_id='usr_multi' ORDER BY session_id"
        ).fetchall()
    assert memberships == [("tnt_main", "REVOKED"), ("tnt_other", "REVOKED")]
    assert sessions == [("sess_multi_main", NOW), ("sess_multi_other", NOW)]


def test_account_delete_is_not_replayable_after_user_disabled(tmp_path: Path) -> None:
    database = tmp_path / "identity.db"
    _seed(database)
    service = AccountDeletionService(database)
    service.delete_account(
        user_id="usr_member",
        recent_authentication_verified=True,
        deletion_confirmation_verified=True,
        occurred_at=NOW,
    )

    with pytest.raises(CentralIdentityError, match="not active"):
        service.delete_account(
            user_id="usr_member",
            recent_authentication_verified=True,
            deletion_confirmation_verified=True,
            occurred_at=NOW,
        )

    assert _events(database)[-1]["reason"] == "user_not_active"
