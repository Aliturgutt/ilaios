from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from services.central_identity import CentralIdentityError
from services.control_plane.migrations import migrate_database
from services.privacy_retention import PrivacyRetentionService

USER_ID = "user-privacy-1"
TENANT_ID = "tenant-privacy-1"
CLOSED_AT = "2026-08-01T00:00:00Z"
CUTOFF = "2026-08-15T00:00:00Z"
NOW = "2026-08-24T15:00:00Z"


def _connect(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path)
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _seed_closed_account(path: Path, *, with_active_membership: bool = False) -> None:
    migrate_database(path)
    with _connect(path) as connection:
        connection.execute(
            "INSERT INTO identity_tenants (tenant_id, status, created_at, updated_at) "
            "VALUES (?, 'ACTIVE', ?, ?)",
            (TENANT_ID, CLOSED_AT, CLOSED_AT),
        )
        connection.execute(
            "INSERT INTO identity_users (user_id, enabled, created_at, updated_at) "
            "VALUES (?, 0, ?, ?)",
            (USER_ID, CLOSED_AT, CLOSED_AT),
        )
        connection.execute(
            "INSERT INTO identity_memberships "
            "(tenant_id, user_id, role, status, is_primary, created_at, updated_at) "
            "VALUES (?, ?, 'MEMBER', ?, 1, ?, ?)",
            (
                TENANT_ID,
                USER_ID,
                "ACTIVE" if with_active_membership else "REVOKED",
                CLOSED_AT,
                CLOSED_AT,
            ),
        )
        connection.execute(
            "INSERT INTO identity_sessions "
            "(session_id, user_id, tenant_id, credential_hash, created_at, expires_at, revoked_at) "
            "VALUES ('session-privacy-1', ?, ?, ?, ?, ?, ?)",
            (USER_ID, TENANT_ID, "a" * 64, CLOSED_AT, CUTOFF, CLOSED_AT),
        )
        payload = json.dumps(
            {
                "action": "account_delete",
                "status": "SUCCESS",
                "user_id": USER_ID,
                "reason": "account_closed",
            }
        )
        connection.execute(
            "INSERT INTO events "
            "(event_type, aggregate_id, payload_json, occurred_at, schema_version) "
            "VALUES ('identity.account_delete', ?, ?, ?, '1')",
            (USER_ID, payload, CLOSED_AT),
        )


def test_privacy_retention_physically_removes_closed_identity_rows(tmp_path: Path) -> None:
    database = tmp_path / "identity.sqlite3"
    _seed_closed_account(database)

    service = PrivacyRetentionService(database)
    assert service.purge_closed_account(
        user_id=USER_ID,
        retention_cutoff=CUTOFF,
        privacy_deletion_confirmed=True,
        occurred_at=NOW,
    ) == (1, 1, 1)

    with _connect(database) as connection:
        assert connection.execute(
            "SELECT 1 FROM identity_users WHERE user_id = ?", (USER_ID,)
        ).fetchone() is None
        assert connection.execute(
            "SELECT 1 FROM identity_memberships WHERE user_id = ?", (USER_ID,)
        ).fetchone() is None
        assert connection.execute(
            "SELECT 1 FROM identity_sessions WHERE user_id = ?", (USER_ID,)
        ).fetchone() is None
        event = connection.execute(
            "SELECT aggregate_id, payload_json FROM events "
            "WHERE event_type = 'identity.privacy_retention_delete' "
            "ORDER BY sequence DESC LIMIT 1"
        ).fetchone()
        assert event is not None
        assert event[0] != USER_ID
        assert USER_ID not in event[1]
        assert json.loads(event[1])["status"] == "SUCCESS"


def test_privacy_retention_requires_prior_account_delete_evidence(tmp_path: Path) -> None:
    database = tmp_path / "identity.sqlite3"
    _seed_closed_account(database)
    with _connect(database) as connection:
        connection.execute("DELETE FROM events WHERE event_type = 'identity.account_delete'")

    service = PrivacyRetentionService(database)
    with pytest.raises(CentralIdentityError, match="deletion evidence"):
        service.purge_closed_account(
            user_id=USER_ID,
            retention_cutoff=CUTOFF,
            privacy_deletion_confirmed=True,
            occurred_at=NOW,
        )


def test_privacy_retention_fails_closed_while_operational_identity_is_active(
    tmp_path: Path,
) -> None:
    database = tmp_path / "identity.sqlite3"
    _seed_closed_account(database, with_active_membership=True)

    service = PrivacyRetentionService(database)
    with pytest.raises(CentralIdentityError, match="must be revoked"):
        service.purge_closed_account(
            user_id=USER_ID,
            retention_cutoff=CUTOFF,
            privacy_deletion_confirmed=True,
            occurred_at=NOW,
        )

    with _connect(database) as connection:
        assert connection.execute(
            "SELECT enabled FROM identity_users WHERE user_id = ?", (USER_ID,)
        ).fetchone() == (0,)
        assert connection.execute(
            "SELECT status FROM identity_memberships WHERE user_id = ?", (USER_ID,)
        ).fetchone() == ("ACTIVE",)


def test_privacy_retention_waits_for_retention_window(tmp_path: Path) -> None:
    database = tmp_path / "identity.sqlite3"
    _seed_closed_account(database)

    service = PrivacyRetentionService(database)
    with pytest.raises(CentralIdentityError, match="retention window"):
        service.purge_closed_account(
            user_id=USER_ID,
            retention_cutoff="2026-07-31T23:59:59Z",
            privacy_deletion_confirmed=True,
            occurred_at=NOW,
        )


def test_expired_email_challenge_retention_removes_only_expired_rows(
    tmp_path: Path,
) -> None:
    database = tmp_path / "identity.sqlite3"
    migrate_database(database)
    with _connect(database) as connection:
        connection.execute(
            "INSERT INTO identity_email_challenges "
            "(challenge_id, email, secret_digest, issued_at, expires_at, consumed_at) "
            "VALUES ('expired', 'user@example.com', ?, ?, ?, NULL)",
            ("b" * 64, CLOSED_AT, CUTOFF),
        )
        connection.execute(
            "INSERT INTO identity_email_challenges "
            "(challenge_id, email, secret_digest, issued_at, expires_at, consumed_at) "
            "VALUES ('future', 'user@example.com', ?, ?, '2026-09-01T00:00:00Z', NULL)",
            ("c" * 64, CLOSED_AT),
        )

    service = PrivacyRetentionService(database)
    assert service.purge_expired_email_challenges(
        retention_cutoff=CUTOFF, occurred_at=NOW
    ) == 1

    with _connect(database) as connection:
        rows = connection.execute(
            "SELECT challenge_id FROM identity_email_challenges ORDER BY challenge_id"
        ).fetchall()
        assert rows == [("future",)]
        audit = connection.execute(
            "SELECT payload_json FROM events "
            "WHERE event_type = 'identity.email_challenge_retention' "
            "ORDER BY sequence DESC LIMIT 1"
        ).fetchone()
        assert audit is not None
        assert json.loads(audit[0])["deleted_challenges"] == 1
