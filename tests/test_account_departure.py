from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from services.account_departure import AccountDepartureService
from services.central_identity import CentralIdentityError
from services.control_plane.migrations import migrate_database

NOW = "2026-08-24T09:15:00Z"


def _seed(path: Path) -> None:
    migrate_database(path)
    with sqlite3.connect(path) as connection:
        connection.execute(
            "INSERT INTO identity_tenants (tenant_id, status, created_at, updated_at) "
            "VALUES ('tnt_main', 'ACTIVE', ?, ?), ('tnt_other', 'ACTIVE', ?, ?)",
            (NOW, NOW, NOW, NOW),
        )
        for user_id in ("usr_owner", "usr_admin", "usr_member", "usr_other"):
            connection.execute(
                "INSERT INTO identity_users (user_id, enabled, created_at, updated_at) "
                "VALUES (?, 1, ?, ?)",
                (user_id, NOW, NOW),
            )
        memberships = (
            ("tnt_main", "usr_owner", "OWNER", "ACTIVE", 1),
            ("tnt_main", "usr_admin", "ADMIN", "ACTIVE", 0),
            ("tnt_main", "usr_member", "MEMBER", "ACTIVE", 0),
            ("tnt_other", "usr_other", "OWNER", "ACTIVE", 1),
        )
        for tenant_id, user_id, role, status, is_primary in memberships:
            connection.execute(
                "INSERT INTO identity_memberships "
                "(tenant_id, user_id, role, status, is_primary, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (tenant_id, user_id, role, status, is_primary, NOW, NOW),
            )
        connection.execute(
            "INSERT INTO identity_sessions "
            "(session_id, user_id, tenant_id, credential_hash, created_at, expires_at) "
            "VALUES ('sess_member', 'usr_member', 'tnt_main', ?, ?, '2026-08-25T09:15:00Z')",
            ("a" * 64, NOW),
        )


def _event_payloads(path: Path) -> list[dict[str, object]]:
    with sqlite3.connect(path) as connection:
        rows = connection.execute(
            "SELECT payload_json FROM events WHERE event_type = 'identity.member_departure' "
            "ORDER BY sequence"
        ).fetchall()
    return [json.loads(str(row[0])) for row in rows]


def test_departure_revokes_membership_sessions_and_disables_orphan_user(tmp_path: Path) -> None:
    database = tmp_path / "identity.db"
    _seed(database)

    revoked = AccountDepartureService(database).depart_member(
        actor_user_id="usr_owner",
        tenant_id="tnt_main",
        target_user_id="usr_member",
        recent_authentication_verified=True,
        occurred_at=NOW,
    )

    assert revoked == 1
    with sqlite3.connect(database) as connection:
        membership = connection.execute(
            "SELECT status FROM identity_memberships WHERE tenant_id='tnt_main' AND user_id='usr_member'"
        ).fetchone()
        session = connection.execute(
            "SELECT revoked_at FROM identity_sessions WHERE session_id='sess_member'"
        ).fetchone()
        user = connection.execute(
            "SELECT enabled FROM identity_users WHERE user_id='usr_member'"
        ).fetchone()
    assert membership == ("REVOKED",)
    assert session == (NOW,)
    assert user == (0,)
    payload = _event_payloads(database)[-1]
    assert payload["status"] == "SUCCESS"
    assert payload["revoked_sessions"] == 1


def test_departure_requires_recent_authentication_and_persists_denial(tmp_path: Path) -> None:
    database = tmp_path / "identity.db"
    _seed(database)

    with pytest.raises(CentralIdentityError, match="recent authentication"):
        AccountDepartureService(database).depart_member(
            actor_user_id="usr_owner",
            tenant_id="tnt_main",
            target_user_id="usr_member",
            recent_authentication_verified=False,
            occurred_at=NOW,
        )

    assert _event_payloads(database)[-1]["reason"] == "recent_auth_required"


def test_departure_denies_cross_tenant_actor(tmp_path: Path) -> None:
    database = tmp_path / "identity.db"
    _seed(database)

    with pytest.raises(CentralIdentityError, match="not authorized"):
        AccountDepartureService(database).depart_member(
            actor_user_id="usr_other",
            tenant_id="tnt_main",
            target_user_id="usr_member",
            recent_authentication_verified=True,
            occurred_at=NOW,
        )

    assert _event_payloads(database)[-1]["reason"] == "actor_not_authorized"


def test_departure_denies_last_active_owner(tmp_path: Path) -> None:
    database = tmp_path / "identity.db"
    _seed(database)

    with pytest.raises(CentralIdentityError, match="last active tenant owner"):
        AccountDepartureService(database).depart_member(
            actor_user_id="usr_owner",
            tenant_id="tnt_main",
            target_user_id="usr_owner",
            recent_authentication_verified=True,
            occurred_at=NOW,
        )

    with sqlite3.connect(database) as connection:
        status = connection.execute(
            "SELECT status FROM identity_memberships WHERE tenant_id='tnt_main' AND user_id='usr_owner'"
        ).fetchone()
    assert status == ("ACTIVE",)
    assert _event_payloads(database)[-1]["reason"] == "last_owner"


def test_departure_is_fail_closed_after_membership_revoked(tmp_path: Path) -> None:
    database = tmp_path / "identity.db"
    _seed(database)
    service = AccountDepartureService(database)
    service.depart_member(
        actor_user_id="usr_owner",
        tenant_id="tnt_main",
        target_user_id="usr_member",
        recent_authentication_verified=True,
        occurred_at=NOW,
    )

    with pytest.raises(CentralIdentityError, match="not active"):
        service.depart_member(
            actor_user_id="usr_owner",
            tenant_id="tnt_main",
            target_user_id="usr_member",
            recent_authentication_verified=True,
            occurred_at=NOW,
        )
