from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from services.central_identity import IdentityProvider
from services.control_plane.migrations import (
    LATEST_SCHEMA_VERSION,
    current_schema_version,
    migrate_database,
    rollback_database,
)
from services.email_auth import (
    EmailAuthError,
    EmailAuthService,
    InMemoryEmailChallengeStore,
    SQLiteEmailChallengeStore,
)

NOW = datetime(2026, 8, 23, 18, 0, tzinfo=timezone.utc)


def _service(*, max_issues: int = 5) -> EmailAuthService:
    return EmailAuthService(
        InMemoryEmailChallengeStore(),
        ttl=timedelta(minutes=10),
        rate_window=timedelta(minutes=15),
        max_issues_per_window=max_issues,
    )


def _migrate_email_challenge_schema(database_path: Path) -> None:
    assert migrate_database(database_path) == 10 == LATEST_SCHEMA_VERSION
    assert current_schema_version(database_path) == 10


def _sqlite_service(database_path: Path, *, max_issues: int = 5) -> EmailAuthService:
    return EmailAuthService(
        SQLiteEmailChallengeStore(database_path),
        ttl=timedelta(minutes=10),
        rate_window=timedelta(minutes=15),
        max_issues_per_window=max_issues,
    )


def test_verified_email_challenge_produces_canonical_email_identity() -> None:
    service = _service()
    issued = service.issue(" User@Example.COM ", now=NOW)

    identity = service.verify(
        challenge_id=issued.challenge_id,
        email="user@example.com",
        secret=issued.secret,
        now=NOW + timedelta(minutes=1),
    )

    assert identity.provider is IdentityProvider.EMAIL
    assert identity.subject == "user@example.com"
    assert identity.email == "user@example.com"
    assert identity.email_verified is True
    assert identity.key() == (IdentityProvider.EMAIL, "", "user@example.com")


def test_email_challenge_is_single_use_and_replay_fails_closed() -> None:
    service = _service()
    issued = service.issue("user@example.com", now=NOW)

    service.verify(
        challenge_id=issued.challenge_id,
        email=issued.email,
        secret=issued.secret,
        now=NOW + timedelta(minutes=1),
    )

    with pytest.raises(EmailAuthError, match="invalid, expired, or already used"):
        service.verify(
            challenge_id=issued.challenge_id,
            email=issued.email,
            secret=issued.secret,
            now=NOW + timedelta(minutes=2),
        )


def test_email_challenge_rejects_wrong_email_without_consuming_secret() -> None:
    service = _service()
    issued = service.issue("owner@example.com", now=NOW)

    with pytest.raises(EmailAuthError):
        service.verify(
            challenge_id=issued.challenge_id,
            email="attacker@example.com",
            secret=issued.secret,
            now=NOW + timedelta(minutes=1),
        )

    identity = service.verify(
        challenge_id=issued.challenge_id,
        email=issued.email,
        secret=issued.secret,
        now=NOW + timedelta(minutes=2),
    )
    assert identity.subject == "owner@example.com"


def test_email_challenge_rejects_wrong_secret_without_consuming_challenge() -> None:
    service = _service()
    issued = service.issue("owner@example.com", now=NOW)

    with pytest.raises(EmailAuthError):
        service.verify(
            challenge_id=issued.challenge_id,
            email=issued.email,
            secret="x" * 48,
            now=NOW + timedelta(minutes=1),
        )

    identity = service.verify(
        challenge_id=issued.challenge_id,
        email=issued.email,
        secret=issued.secret,
        now=NOW + timedelta(minutes=2),
    )
    assert identity.email_verified is True


def test_email_challenge_expires_fail_closed() -> None:
    service = _service()
    issued = service.issue("user@example.com", now=NOW)

    with pytest.raises(EmailAuthError, match="invalid, expired, or already used"):
        service.verify(
            challenge_id=issued.challenge_id,
            email=issued.email,
            secret=issued.secret,
            now=NOW + timedelta(minutes=10),
        )


def test_email_challenge_rate_limit_is_per_normalized_email() -> None:
    service = _service(max_issues=2)
    service.issue("User@Example.com", now=NOW)
    service.issue("user@example.COM", now=NOW + timedelta(minutes=1))

    with pytest.raises(EmailAuthError, match="rate limit"):
        service.issue(" USER@example.com ", now=NOW + timedelta(minutes=2))

    other = service.issue("other@example.com", now=NOW + timedelta(minutes=2))
    assert other.email == "other@example.com"


def test_email_challenge_rate_window_recovers_without_disabling_limits() -> None:
    service = _service(max_issues=1)
    service.issue("user@example.com", now=NOW)

    with pytest.raises(EmailAuthError, match="rate limit"):
        service.issue("user@example.com", now=NOW + timedelta(minutes=14))

    issued = service.issue("user@example.com", now=NOW + timedelta(minutes=16))
    assert issued.email == "user@example.com"


def test_email_challenge_rejects_malformed_email() -> None:
    malformed_emails = (
        "",
        "missing-at.example.com",
        "@example.com",
        "user@localhost",
        "a b@example.com",
    )
    for email in malformed_emails:
        with pytest.raises(EmailAuthError, match="email address is invalid"):
            _service().issue(email, now=NOW)


def test_email_auth_rejects_naive_clock_input() -> None:
    with pytest.raises(EmailAuthError, match="timezone-aware"):
        _service().issue("user@example.com", now=datetime(2026, 8, 23, 18, 0))


def test_sqlite_store_fails_closed_until_canonical_schema_exists(tmp_path: Path) -> None:
    database_path = tmp_path / "identity.db"
    sqlite3.connect(database_path).close()

    with pytest.raises(EmailAuthError, match="persistence schema is unavailable"):
        SQLiteEmailChallengeStore(database_path)


def test_v10_migration_creates_email_challenge_table_with_expected_contract(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "identity.db"
    _migrate_email_challenge_schema(database_path)

    with sqlite3.connect(database_path) as connection:
        columns = {
            row[1]: (row[2], row[3], row[5])
            for row in connection.execute(
                "PRAGMA table_info(identity_email_challenges)"
            ).fetchall()
        }
    assert columns == {
        "challenge_id": ("TEXT", 0, 1),
        "email": ("TEXT", 1, 0),
        "secret_digest": ("TEXT", 1, 0),
        "issued_at": ("TEXT", 1, 0),
        "expires_at": ("TEXT", 1, 0),
        "consumed_at": ("TEXT", 0, 0),
    }


def test_sqlite_challenge_survives_restart_and_remains_single_use(tmp_path: Path) -> None:
    database_path = tmp_path / "identity.db"
    _migrate_email_challenge_schema(database_path)
    issued = _sqlite_service(database_path).issue("user@example.com", now=NOW)

    identity = _sqlite_service(database_path).verify(
        challenge_id=issued.challenge_id,
        email=issued.email,
        secret=issued.secret,
        now=NOW + timedelta(minutes=1),
    )
    assert identity.subject == "user@example.com"

    with pytest.raises(EmailAuthError, match="already used"):
        _sqlite_service(database_path).verify(
            challenge_id=issued.challenge_id,
            email=issued.email,
            secret=issued.secret,
            now=NOW + timedelta(minutes=2),
        )


def test_sqlite_rate_limit_survives_restart(tmp_path: Path) -> None:
    database_path = tmp_path / "identity.db"
    _migrate_email_challenge_schema(database_path)
    _sqlite_service(database_path, max_issues=2).issue("user@example.com", now=NOW)
    _sqlite_service(database_path, max_issues=2).issue(
        "user@example.com", now=NOW + timedelta(minutes=1)
    )

    with pytest.raises(EmailAuthError, match="rate limit"):
        _sqlite_service(database_path, max_issues=2).issue(
            "user@example.com", now=NOW + timedelta(minutes=2)
        )


def test_sqlite_store_never_persists_raw_secret(tmp_path: Path) -> None:
    database_path = tmp_path / "identity.db"
    _migrate_email_challenge_schema(database_path)
    issued = _sqlite_service(database_path).issue("user@example.com", now=NOW)

    with sqlite3.connect(database_path) as connection:
        row = connection.execute(
            "SELECT secret_digest FROM identity_email_challenges WHERE challenge_id = ?",
            (issued.challenge_id,),
        ).fetchone()
    assert row is not None
    assert row[0] != issued.secret
    assert len(str(row[0])) == 64


def test_v10_rollback_and_reupgrade_recreate_challenge_persistence(tmp_path: Path) -> None:
    database_path = tmp_path / "identity.db"
    backup_path = tmp_path / "identity-v10-backup.db"
    _migrate_email_challenge_schema(database_path)
    issued = _sqlite_service(database_path).issue("user@example.com", now=NOW)

    assert rollback_database(database_path, backup_path) == 9
    assert current_schema_version(database_path) == 9
    with pytest.raises(EmailAuthError, match="persistence schema is unavailable"):
        SQLiteEmailChallengeStore(database_path)

    assert current_schema_version(backup_path) == 10
    with sqlite3.connect(backup_path) as connection:
        backed_up = connection.execute(
            "SELECT challenge_id FROM identity_email_challenges WHERE challenge_id = ?",
            (issued.challenge_id,),
        ).fetchone()
    assert backed_up == (issued.challenge_id,)

    assert migrate_database(database_path) == 10
    restarted = _sqlite_service(database_path)
    replacement = restarted.issue("user@example.com", now=NOW + timedelta(minutes=16))
    assert replacement.email == "user@example.com"
