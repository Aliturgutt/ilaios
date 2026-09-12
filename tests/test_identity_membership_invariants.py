from __future__ import annotations

import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

import pytest

from services.central_identity import (
    CentralIdentityError,
    CentralIdentityService,
    CentralIdentityStore,
    IdentityProvider,
    VerifiedExternalIdentity,
)
from services.central_identity_sqlite import SQLiteCentralIdentityStore as PathStore
from services.control_plane.migrations import (
    current_schema_version,
    migrate_database,
    rollback_database,
)
from services.sqlite_central_identity import SQLiteCentralIdentityStore as ConnectionStore


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    # Keep each matrix case isolated without untyped decorator dependencies.
    if metafunc.function.__name__ == "test_adapter_status_parity":
        metafunc.parametrize("tenant_status", ["ACTIVE", "SUSPENDED"])
        metafunc.parametrize("membership_status", ["ACTIVE", "SUSPENDED", "REVOKED"])
        metafunc.parametrize("enabled", [0, 1])
    elif metafunc.function.__name__ == "test_primary_write_invariant":
        metafunc.parametrize("operation", ["insert", "promote", "recover"])


def _identity() -> VerifiedExternalIdentity:
    return VerifiedExternalIdentity(provider=IdentityProvider.GOOGLE, subject="audit-user")


def _extra_tenant(connection: sqlite3.Connection, tenant: str) -> None:
    connection.execute(
        "INSERT INTO identity_tenants VALUES (?, 'ACTIVE', 'now', 'now')", (tenant,)
    )


def test_adapter_status_parity(
    tmp_path: Path, tenant_status: str, membership_status: str, enabled: int
) -> None:
    database = tmp_path / "identity.db"
    path_store = PathStore(database)
    account = CentralIdentityService(path_store).sign_in(_identity())
    with sqlite3.connect(database) as connection:
        connection.execute("UPDATE identity_tenants SET status = ?", (tenant_status,))
        connection.execute("UPDATE identity_memberships SET status = ?", (membership_status,))
        connection.execute("UPDATE identity_users SET enabled = ?", (enabled,))
        connection.commit()
        connection_store = ConnectionStore(connection)
        assert path_store.get_account(account.user_id) == connection_store.get_account(account.user_id)
        allowed = enabled == 1 and tenant_status == membership_status == "ACTIVE"
        stores: tuple[CentralIdentityStore, ...] = (path_store, connection_store)
        for store in stores:
            if allowed:
                assert CentralIdentityService(store).sign_in(_identity()) == account
            else:
                with pytest.raises(CentralIdentityError):
                    CentralIdentityService(store).sign_in(_identity())
            assert store.get_account("missing") is None
            assert store.get_account(" ") is None


def test_primary_write_invariant(tmp_path: Path, operation: str) -> None:
    database = tmp_path / "identity.db"
    account = CentralIdentityService(PathStore(database)).sign_in(_identity())
    with sqlite3.connect(database) as connection:
        _extra_tenant(connection, "second")
        if operation != "insert":
            connection.execute(
                "INSERT INTO identity_memberships VALUES ('second', ?, 'OWNER', ?, ?, 'now', 'now')",
                (account.user_id, "SUSPENDED" if operation == "recover" else "ACTIVE", int(operation == "recover")),
            )
        connection.commit()
        with pytest.raises(sqlite3.IntegrityError):
            if operation == "insert":
                connection.execute(
                    "INSERT INTO identity_memberships VALUES ('second', ?, 'OWNER', 'ACTIVE', 1, 'now', 'now')",
                    (account.user_id,),
                )
            else:
                connection.execute(
                    "UPDATE identity_memberships SET status = 'ACTIVE', is_primary = 1 WHERE tenant_id = 'second'"
                )
        connection.rollback()
        assert connection.execute(
            "SELECT COUNT(*) FROM identity_memberships WHERE is_primary = 1 AND status = 'ACTIVE'"
        ).fetchone() == (1,)


def test_concurrent_primary_promotions_have_one_winner(tmp_path: Path) -> None:
    database = tmp_path / "identity.db"
    account = CentralIdentityService(PathStore(database)).sign_in(_identity())
    with sqlite3.connect(database) as connection:
        connection.execute("UPDATE identity_memberships SET is_primary = 0")
        _extra_tenant(connection, "second")
        connection.execute(
            "INSERT INTO identity_memberships VALUES ('second', ?, 'OWNER', 'ACTIVE', 0, 'now', 'now')",
            (account.user_id,),
        )
    barrier = Barrier(2)

    def promote(tenant: str) -> bool:
        with sqlite3.connect(database, timeout=10) as connection:
            barrier.wait(timeout=10)
            try:
                connection.execute(
                    "UPDATE identity_memberships SET is_primary = 1 WHERE tenant_id = ?", (tenant,)
                )
                connection.commit()
                return True
            except sqlite3.IntegrityError:
                connection.rollback()
                return False

    with ThreadPoolExecutor(max_workers=2) as executor:
        assert sorted(executor.map(promote, [account.tenant_id, "second"])) == [False, True]
    with sqlite3.connect(database) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM identity_memberships WHERE is_primary = 1 AND status = 'ACTIVE'"
        ).fetchone() == (1,)


def test_duplicate_legacy_state_fails_closed_without_data_loss(tmp_path: Path) -> None:
    database = tmp_path / "identity.db"
    path_store = PathStore(database)
    account = CentralIdentityService(path_store).sign_in(_identity())
    with sqlite3.connect(database) as connection:
        connection.execute("DROP INDEX identity_memberships_one_active_primary")
        connection.execute("DELETE FROM schema_migrations WHERE version = 11")
        _extra_tenant(connection, "second")
        connection.execute(
            "INSERT INTO identity_memberships VALUES ('second', ?, 'OWNER', 'ACTIVE', 1, 'now', 'now')",
            (account.user_id,),
        )
        connection.commit()
        stores: tuple[CentralIdentityStore, ...] = (path_store, ConnectionStore(connection))
        for store in stores:
            assert store.get_account(account.user_id) is None
            with pytest.raises(CentralIdentityError):
                CentralIdentityService(store).sign_in(_identity())
        before = tuple(connection.iterdump())
        with pytest.raises(sqlite3.IntegrityError):
            migrate_database(database)
        assert tuple(connection.iterdump()) == before
        assert connection.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        assert current_schema_version(database) == 10
        assert connection.execute("SELECT COUNT(*) FROM identity_memberships").fetchone() == (2,)


def test_existing_valid_memberships_upgrade_without_rewrite(tmp_path: Path) -> None:
    database = tmp_path / "identity.db"
    account = CentralIdentityService(PathStore(database)).sign_in(_identity())
    with sqlite3.connect(database) as connection:
        connection.execute("DROP INDEX identity_memberships_one_active_primary")
        connection.execute("DELETE FROM schema_migrations WHERE version = 11")
        connection.commit()
        before = connection.execute("SELECT * FROM identity_memberships").fetchall()
    assert migrate_database(database) == 11
    assert migrate_database(database) == 11
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT * FROM identity_memberships").fetchall() == before
        assert connection.execute("PRAGMA integrity_check").fetchone() == ("ok",)
    assert CentralIdentityService(PathStore(database)).sign_in(_identity()) == account


def test_identity_rollback_preserves_enforcement_and_backup(tmp_path: Path) -> None:
    database = tmp_path / "identity.db"
    backup = tmp_path / "identity-v11.db"
    account = CentralIdentityService(PathStore(database)).sign_in(_identity())
    assert rollback_database(database, backup) == 10
    for path in (database, backup):
        with sqlite3.connect(path) as connection:
            assert connection.execute("PRAGMA integrity_check").fetchone() == ("ok",)
            assert ConnectionStore(connection).get_account(account.user_id) == account
            _extra_tenant(connection, "second")
            with pytest.raises(sqlite3.IntegrityError):
                connection.execute(
                    "INSERT INTO identity_memberships VALUES ('second', ?, 'OWNER', 'ACTIVE', 1, 'now', 'now')",
                    (account.user_id,),
                )
            connection.rollback()
    assert migrate_database(database) == 11
