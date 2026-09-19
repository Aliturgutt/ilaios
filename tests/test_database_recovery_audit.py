"""Database/recovery audit regression tests for F01 and F02."""

from __future__ import annotations

import sqlite3
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from services.control_plane.migrations import (
    LATEST_SCHEMA_VERSION,
    _restore_database,
    current_schema_version,
    migrate_database,
    rollback_database,
)
from services.deployment import RuntimeBackupManager


def test_runtime_backup_restores_committed_wal_data_with_integrity(tmp_path: Path) -> None:
    for suffix in (".db", ".sqlite3"):
        state_root = tmp_path / f"state-{suffix[1:]}"
        state_root.mkdir()
        database = state_root / f"runtime{suffix}"

        writer = sqlite3.connect(database)
        try:
            assert writer.execute("PRAGMA journal_mode=WAL").fetchone() == ("wal",)
            writer.execute("PRAGMA wal_autocheckpoint=0")
            writer.execute(
                "CREATE TABLE records (id INTEGER PRIMARY KEY, value TEXT NOT NULL)"
            )
            writer.commit()
            writer.execute(
                "INSERT INTO records (value) VALUES (?)", ("committed-in-wal",)
            )
            writer.commit()

            wal_path = Path(f"{database}-wal")
            shm_path = Path(f"{database}-shm")
            assert wal_path.is_file()
            assert wal_path.stat().st_size > 0

            archive = tmp_path / f"runtime-{suffix[1:]}.zip"
            manifest = RuntimeBackupManager().backup(state_root, archive)
            manifest_files = manifest["files"]
            assert isinstance(manifest_files, dict)
            assert database.name in manifest_files
            assert wal_path.name not in manifest_files
            assert shm_path.name not in manifest_files

            restored_root = tmp_path / f"restored-{suffix[1:]}"
            RuntimeBackupManager().restore(archive, restored_root)
            restored_database = restored_root / database.name
            with sqlite3.connect(restored_database) as restored:
                assert restored.execute("PRAGMA integrity_check").fetchone() == ("ok",)
                assert restored.execute("SELECT value FROM records").fetchall() == [
                    ("committed-in-wal",)
                ]
        finally:
            writer.close()


def test_rollback_backup_restores_committed_wal_data_with_integrity(tmp_path: Path) -> None:
    for suffix in (".db", ".sqlite3"):
        database = tmp_path / f"control{suffix}"
        backup = tmp_path / f"control-backup{suffix}"
        assert migrate_database(database) == LATEST_SCHEMA_VERSION

        writer = sqlite3.connect(database)
        try:
            assert writer.execute("PRAGMA journal_mode=WAL").fetchone() == ("wal",)
            writer.execute("PRAGMA wal_autocheckpoint=0")
            writer.execute(
                "INSERT INTO goals (goal_id, objective, created_at) VALUES (?, ?, ?)",
                ("wal-goal", "committed-in-wal", "2026-09-10T00:00:00Z"),
            )
            writer.commit()
            wal_path = Path(f"{database}-wal")
            assert wal_path.is_file()
            assert wal_path.stat().st_size > 0

            assert rollback_database(database, backup) == LATEST_SCHEMA_VERSION - 1
            assert backup.is_file()

            # A rollback snapshot must remain valid without WAL/SHM sidecars. SQLite
            # may create empty/transient sidecars when opening a WAL-mode database,
            # so remove them after the snapshot connection has closed and prove that
            # the main snapshot file alone contains the committed state.
            Path(f"{backup}-wal").unlink(missing_ok=True)
            Path(f"{backup}-shm").unlink(missing_ok=True)
            with sqlite3.connect(backup) as snapshot:
                assert snapshot.execute("PRAGMA integrity_check").fetchone() == ("ok",)
                assert snapshot.execute(
                    "SELECT objective FROM goals WHERE goal_id = ?", ("wal-goal",)
                ).fetchone() == ("committed-in-wal",)

            _restore_database(backup, database)
            assert current_schema_version(database) == LATEST_SCHEMA_VERSION
            with sqlite3.connect(database) as restored:
                assert restored.execute("PRAGMA integrity_check").fetchone() == ("ok",)
                assert restored.execute(
                    "SELECT objective FROM goals WHERE goal_id = ?", ("wal-goal",)
                ).fetchone() == ("committed-in-wal",)
        finally:
            writer.close()


def test_concurrent_migrators_serialize_and_converge(tmp_path: Path) -> None:
    database = tmp_path / "concurrent.db"
    barrier = threading.Barrier(2)

    def run_migration() -> int:
        barrier.wait(timeout=10)
        return migrate_database(database)

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(run_migration) for _ in range(2)]
        results = [future.result(timeout=30) for future in futures]

    assert results == [LATEST_SCHEMA_VERSION, LATEST_SCHEMA_VERSION]
    with sqlite3.connect(database) as connection:
        assert connection.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        versions = connection.execute(
            "SELECT version FROM schema_migrations ORDER BY version"
        ).fetchall()
    assert versions == [(version,) for version in range(1, LATEST_SCHEMA_VERSION + 1)]


def test_hard_crash_rolls_back_partial_schema_and_version(tmp_path: Path) -> None:
    database = tmp_path / "crash.db"
    crash_program = r'''
import os
import sys
from pathlib import Path

import sqlite3
import services.control_plane.migrations as migrations


def crash_after_first_statement(connection: sqlite3.Connection, script: str) -> None:
    pending = ""
    for line in script.splitlines(keepends=True):
        pending += line
        if not sqlite3.complete_statement(pending):
            continue
        statement = pending.strip()
        if statement:
            connection.execute(statement)
            os._exit(91)
        pending = ""
    os._exit(92)


migrations._execute_script_statements = crash_after_first_statement
migrations.migrate_database(Path(sys.argv[1]))
'''
    completed = subprocess.run(
        (sys.executable, "-c", crash_program, str(database)),
        check=False,
        timeout=30,
    )
    assert completed.returncode == 91

    with sqlite3.connect(database) as connection:
        assert connection.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
    assert "goals" not in tables
    assert "schema_migrations" not in tables

    assert migrate_database(database) == LATEST_SCHEMA_VERSION
    assert current_schema_version(database) == LATEST_SCHEMA_VERSION
