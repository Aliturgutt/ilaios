from __future__ import annotations

import hashlib
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from services.canonical_browser_session import (
    CanonicalBrowserSessionAuthority,
    CanonicalBrowserSessionError,
)
from services.central_identity import (
    CanonicalAccount,
    CentralIdentityService,
    IdentityProvider,
    VerifiedExternalIdentity,
)
from services.control_plane.migrations import migrate_database
from services.sqlite_central_identity import SQLiteCentralIdentityStore


def _account(database: Path) -> CanonicalAccount:
    migrate_database(database)
    with sqlite3.connect(database) as connection:
        return CentralIdentityService(SQLiteCentralIdentityStore(connection)).sign_in(
            VerifiedExternalIdentity(
                provider=IdentityProvider.GOOGLE,
                subject="immutable-google-subject",
                email="owner@example.com",
                email_verified=True,
            )
        )


def _authority(database: Path) -> CanonicalBrowserSessionAuthority:
    return CanonicalBrowserSessionAuthority(database, timedelta(hours=12))


def test_issues_digest_only_and_verifies_canonical_principal(tmp_path: Path) -> None:
    database = tmp_path / "identity.db"
    account = _account(database)
    authority = _authority(database)
    now = datetime(2026, 8, 29, 12, 0, tzinfo=UTC)

    issued = authority.issue(account, now, timedelta(hours=1))

    with sqlite3.connect(database) as connection:
        row = connection.execute(
            """
            SELECT user_id, tenant_id, credential_hash, expires_at, revoked_at
              FROM identity_sessions
             WHERE session_id = ?
            """,
            (issued.session_id,),
        ).fetchone()

    assert row is not None
    assert row[0] == account.user_id
    assert row[1] == account.tenant_id
    assert row[2] == hashlib.sha256(issued.credential.encode("utf-8")).hexdigest()
    assert row[2] != issued.credential
    assert row[4] is None

    principal = authority.verify(issued.session_id, issued.credential, now)
    assert principal.principal_id == account.user_id
    assert principal.tenant_id == account.tenant_id
    assert principal.roles == frozenset({"OWNER"})


def test_sessions_are_nondeterministic(tmp_path: Path) -> None:
    database = tmp_path / "identity.db"
    account = _account(database)
    authority = _authority(database)
    now = datetime(2026, 8, 29, 12, 0, tzinfo=UTC)

    first = authority.issue(account, now, timedelta(hours=1))
    second = authority.issue(account, now, timedelta(hours=1))

    assert first.session_id != second.session_id
    assert first.credential != second.credential


def test_wrong_digest_and_malformed_credentials_fail_closed(tmp_path: Path) -> None:
    database = tmp_path / "identity.db"
    account = _account(database)
    authority = _authority(database)
    now = datetime(2026, 8, 29, 12, 0, tzinfo=UTC)
    issued = authority.issue(account, now, timedelta(hours=1))
    digest = hashlib.sha256(issued.credential.encode("utf-8")).hexdigest()

    for credential in ("wrong", digest, "", "   "):
        with pytest.raises(CanonicalBrowserSessionError):
            authority.verify(issued.session_id, credential, now)

    with pytest.raises(CanonicalBrowserSessionError):
        authority.verify("ses_missing", issued.credential, now)


def test_expired_session_fails_closed(tmp_path: Path) -> None:
    database = tmp_path / "identity.db"
    account = _account(database)
    authority = _authority(database)
    now = datetime(2026, 8, 29, 12, 0, tzinfo=UTC)
    issued = authority.issue(account, now, timedelta(minutes=5))

    with pytest.raises(CanonicalBrowserSessionError):
        authority.verify(
            issued.session_id,
            issued.credential,
            now + timedelta(minutes=5),
        )


def test_revocation_is_immediate_and_survives_restart(tmp_path: Path) -> None:
    database = tmp_path / "identity.db"
    account = _account(database)
    now = datetime(2026, 8, 29, 12, 0, tzinfo=UTC)
    issued = _authority(database).issue(account, now, timedelta(hours=1))

    _authority(database).revoke(issued.session_id, now + timedelta(minutes=1))

    with pytest.raises(CanonicalBrowserSessionError):
        _authority(database).verify(
            issued.session_id,
            issued.credential,
            now + timedelta(minutes=2),
        )


def test_valid_session_survives_authority_reconstruction(tmp_path: Path) -> None:
    database = tmp_path / "identity.db"
    account = _account(database)
    now = datetime(2026, 8, 29, 12, 0, tzinfo=UTC)
    issued = _authority(database).issue(account, now, timedelta(hours=1))

    principal = _authority(database).verify(
        issued.session_id,
        issued.credential,
        now + timedelta(minutes=1),
    )

    assert principal.principal_id == account.user_id
    assert principal.tenant_id == account.tenant_id


def test_disabled_user_and_inactive_membership_fail_after_issue(
    tmp_path: Path,
) -> None:
    database = tmp_path / "identity.db"
    account = _account(database)
    now = datetime(2026, 8, 29, 12, 0, tzinfo=UTC)
    authority = _authority(database)
    issued = authority.issue(account, now, timedelta(hours=1))

    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE identity_users SET enabled = 0 WHERE user_id = ?",
            (account.user_id,),
        )
        connection.commit()

    with pytest.raises(CanonicalBrowserSessionError):
        authority.verify(issued.session_id, issued.credential, now)

    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE identity_users SET enabled = 1 WHERE user_id = ?",
            (account.user_id,),
        )
        connection.execute(
            "UPDATE identity_memberships SET status = 'SUSPENDED' WHERE user_id = ?",
            (account.user_id,),
        )
        connection.commit()

    with pytest.raises(CanonicalBrowserSessionError):
        authority.verify(issued.session_id, issued.credential, now)


def test_cross_tenant_substitution_fails_closed(tmp_path: Path) -> None:
    database = tmp_path / "identity.db"
    account = _account(database)
    now = datetime(2026, 8, 29, 12, 0, tzinfo=UTC)
    authority = _authority(database)
    issued = authority.issue(account, now, timedelta(hours=1))

    with sqlite3.connect(database) as connection:
        connection.execute("PRAGMA foreign_keys = OFF")
        connection.execute(
            "UPDATE identity_sessions SET tenant_id = ? WHERE session_id = ?",
            ("tnt_attacker_selected", issued.session_id),
        )
        connection.commit()

    with pytest.raises(CanonicalBrowserSessionError):
        authority.verify(issued.session_id, issued.credential, now)


def test_issue_rejects_caller_substituted_tenant_and_invalid_lifetime(
    tmp_path: Path,
) -> None:
    database = tmp_path / "identity.db"
    account = _account(database)
    authority = _authority(database)
    now = datetime(2026, 8, 29, 12, 0, tzinfo=UTC)

    substituted = CanonicalAccount(
        user_id=account.user_id,
        tenant_id="tnt_attacker_selected",
        enabled=True,
    )
    with pytest.raises(PermissionError):
        authority.issue(substituted, now, timedelta(hours=1))

    with pytest.raises(CanonicalBrowserSessionError):
        authority.issue(account, now, timedelta(0))
    with pytest.raises(CanonicalBrowserSessionError):
        authority.issue(account, now, timedelta(days=1))
