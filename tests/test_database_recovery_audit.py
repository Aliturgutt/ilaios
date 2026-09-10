"""Database/recovery audit regression tests for F01 and F02."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from services.deployment import RuntimeBackupManager


@pytest.mark.parametrize("suffix", [".db", ".sqlite3"])
def test_runtime_backup_restores_committed_wal_data_with_integrity(
    tmp_path: Path, suffix: str
) -> None:
    state_root = tmp_path / "state"
    state_root.mkdir()
    database = state_root / f"runtime{suffix}"

    writer = sqlite3.connect(database)
    try:
        assert writer.execute("PRAGMA journal_mode=WAL").fetchone() == ("wal",)
        writer.execute("PRAGMA wal_autocheckpoint=0")
        writer.execute("CREATE TABLE records (id INTEGER PRIMARY KEY, value TEXT NOT NULL)")
        writer.commit()
        writer.execute("INSERT INTO records (value) VALUES (?)", ("committed-in-wal",))
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
