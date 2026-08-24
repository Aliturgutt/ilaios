from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from services.central_identity import (
    CentralIdentityError,
    CentralIdentityService,
    IdentityProvider,
    VerifiedExternalIdentity,
)
from services.central_identity_sqlite import SQLiteCentralIdentityStore
from services.control_plane.migrations import (
    LATEST_SCHEMA_VERSION,
    current_schema_version,
    migrate_database,
    rollback_database,
)


def _identity(
    provider: IdentityProvider,
    subject: str,
    *,
    email: str | None = None,
    verified: bool = False,
    issuer: str | None = None,
) -> VerifiedExternalIdentity:
    return VerifiedExternalIdentity(
        provider=provider,
        subject=subject,
        email=email,
        email_verified=verified,
        issuer=issuer,
    )


def _connect(database: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(database)
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def test_migration_v9_creates_canonical_identity_tables(tmp_path: Path) -> None:
    database = tmp_path / "identity.sqlite3"
    assert migrate_database(database) == LATEST_SCHEMA_VERSION == 10
    with _connect(database) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
    assert {
        "identity_users",
        "identity_accounts",
        "identity_tenants",
        "identity_memberships",
        "identity_sessions",
        "identity_entitlements",
    } <= tables


def test_sqlite_store_reuses_same_account_across_restart(tmp_path: Path) -> None:
    database = tmp_path / "identity.sqlite3"
    service = CentralIdentityService(SQLiteCentralIdentityStore(database))
    first = service.sign_in(
        _identity(
            IdentityProvider.GOOGLE,
            "google-sub-1",
            email="Person@Example.com",
            verified=True,
        )
    )

    restarted = CentralIdentityService(SQLiteCentralIdentityStore(database))
    second = restarted.sign_in(
        _identity(
            IdentityProvider.GOOGLE,
            "google-sub-1",
            email="person@example.com",
            verified=True,
        )
    )

    assert second == first


def test_verified_email_does_not_merge_distinct_provider_accounts(tmp_path: Path) -> None:
    service = CentralIdentityService(SQLiteCentralIdentityStore(tmp_path / "identity.sqlite3"))
    google = service.sign_in(
        _identity(
            IdentityProvider.GOOGLE,
            "google-sub",
            email="same@example.com",
            verified=True,
        )
    )
    github = service.sign_in(
        _identity(
            IdentityProvider.GITHUB,
            "github-sub",
            email="same@example.com",
            verified=True,
        )
    )
    assert google.user_id != github.user_id
    assert google.tenant_id != github.tenant_id


def test_enterprise_oidc_subject_is_scoped_by_issuer(tmp_path: Path) -> None:
    service = CentralIdentityService(SQLiteCentralIdentityStore(tmp_path / "identity.sqlite3"))
    first = service.sign_in(
        _identity(
            IdentityProvider.ENTERPRISE_OIDC,
            "shared-sub",
            issuer="https://idp-a.example",
        )
    )
    second = service.sign_in(
        _identity(
            IdentityProvider.ENTERPRISE_OIDC,
            "shared-sub",
            issuer="https://idp-b.example",
        )
    )
    assert first.user_id != second.user_id


def test_link_takeover_and_cross_tenant_fail_closed(tmp_path: Path) -> None:
    service = CentralIdentityService(SQLiteCentralIdentityStore(tmp_path / "identity.sqlite3"))
    first = service.sign_in(_identity(IdentityProvider.GOOGLE, "google-1"))
    second = service.sign_in(_identity(IdentityProvider.GOOGLE, "google-2"))
    github = _identity(IdentityProvider.GITHUB, "github-1")
    service.link_identity(
        authenticated_user_id=first.user_id,
        authenticated_tenant_id=first.tenant_id,
        identity=github,
        recent_authentication_verified=True,
    )
    with pytest.raises(CentralIdentityError, match="already linked"):
        service.link_identity(
            authenticated_user_id=second.user_id,
            authenticated_tenant_id=second.tenant_id,
            identity=github,
            recent_authentication_verified=True,
        )
    with pytest.raises(CentralIdentityError, match="tenant mismatch"):
        service.link_identity(
            authenticated_user_id=first.user_id,
            authenticated_tenant_id=second.tenant_id,
            identity=_identity(
                IdentityProvider.MICROSOFT,
                "ms-1",
                issuer="https://login.microsoftonline.com/test/v2.0",
            ),
            recent_authentication_verified=True,
        )


def test_persistent_unlink_is_atomic_and_preserves_last_sign_in(tmp_path: Path) -> None:
    database = tmp_path / "identity.sqlite3"
    service = CentralIdentityService(SQLiteCentralIdentityStore(database))
    account = service.sign_in(_identity(IdentityProvider.GOOGLE, "google-1"))
    github = _identity(IdentityProvider.GITHUB, "github-1")
    service.link_identity(
        authenticated_user_id=account.user_id,
        authenticated_tenant_id=account.tenant_id,
        identity=github,
        recent_authentication_verified=True,
    )
    removed = service.unlink_identity(
        authenticated_user_id=account.user_id,
        authenticated_tenant_id=account.tenant_id,
        identity=github,
        recent_authentication_verified=True,
    )
    assert removed.provider is IdentityProvider.GITHUB
    restarted = CentralIdentityService(SQLiteCentralIdentityStore(database))
    assert {link.provider for link in restarted.linked_identities(account.user_id)} == {
        IdentityProvider.GOOGLE
    }
    with pytest.raises(CentralIdentityError, match="last usable sign-in method"):
        restarted.unlink_identity(
            authenticated_user_id=account.user_id,
            authenticated_tenant_id=account.tenant_id,
            identity=_identity(IdentityProvider.GOOGLE, "google-1"),
            recent_authentication_verified=True,
        )


def test_session_persistence_revocation_and_tenant_binding(tmp_path: Path) -> None:
    store = SQLiteCentralIdentityStore(tmp_path / "identity.sqlite3")
    service = CentralIdentityService(store)
    first = service.sign_in(_identity(IdentityProvider.GOOGLE, "google-1"))
    second = service.sign_in(_identity(IdentityProvider.GOOGLE, "google-2"))

    stored = store.persist_session(
        session_id="session-1",
        user_id=first.user_id,
        tenant_id=first.tenant_id,
        credential_hash="a" * 64,
        created_at="2026-08-21T10:00:00Z",
        expires_at="2026-08-21T18:00:00Z",
    )
    assert stored.revoked_at is None
    assert store.revoke_session("session-1", "2026-08-21T11:00:00Z") is True
    assert store.get_session("session-1") is not None
    assert store.get_session("session-1").revoked_at == "2026-08-21T11:00:00Z"  # type: ignore[union-attr]

    with pytest.raises(CentralIdentityError, match="tenant"):
        store.persist_session(
            session_id="session-x",
            user_id=first.user_id,
            tenant_id=second.tenant_id,
            credential_hash="b" * 64,
            created_at="2026-08-21T10:00:00Z",
            expires_at="2026-08-21T18:00:00Z",
        )


def test_entitlement_is_tenant_scoped_and_upserted(tmp_path: Path) -> None:
    store = SQLiteCentralIdentityStore(tmp_path / "identity.sqlite3")
    account = CentralIdentityService(store).sign_in(
        _identity(IdentityProvider.GOOGLE, "google-1")
    )
    first = store.set_entitlement(
        tenant_id=account.tenant_id,
        entitlement_key="plan.pro",
        state="ACTIVE",
        limit_value=100,
        updated_at="2026-08-21T10:00:00Z",
    )
    assert first.limit_value == 100
    store.set_entitlement(
        tenant_id=account.tenant_id,
        entitlement_key="plan.pro",
        state="SUSPENDED",
        limit_value=25,
        updated_at="2026-08-21T11:00:00Z",
    )
    current = store.get_entitlement(account.tenant_id, "plan.pro")
    assert current is not None
    assert current.state == "SUSPENDED"
    assert current.limit_value == 25


def test_v9_expand_only_rollback_preserves_identity_data(tmp_path: Path) -> None:
    database = tmp_path / "identity.sqlite3"
    backup_v10 = tmp_path / "identity-v10-backup.sqlite3"
    backup_v9 = tmp_path / "identity-v9-backup.sqlite3"
    service = CentralIdentityService(SQLiteCentralIdentityStore(database))
    account = service.sign_in(_identity(IdentityProvider.GOOGLE, "google-1"))

    assert rollback_database(database, backup_v10) == 9
    assert current_schema_version(database) == 9
    assert current_schema_version(backup_v10) == 10
    assert rollback_database(database, backup_v9) == 8
    assert current_schema_version(database) == 8
    assert current_schema_version(backup_v9) == 9
    with _connect(database) as connection:
        assert connection.execute(
            "SELECT tenant_id FROM identity_users AS u "
            "JOIN identity_memberships AS m ON m.user_id = u.user_id "
            "WHERE u.user_id = ?",
            (account.user_id,),
        ).fetchone() == (account.tenant_id,)

    assert migrate_database(database) == LATEST_SCHEMA_VERSION
    restarted = CentralIdentityService(SQLiteCentralIdentityStore(database))
    assert restarted.sign_in(_identity(IdentityProvider.GOOGLE, "google-1")) == account