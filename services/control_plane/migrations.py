"""Versioned SQLite migrations for the authoritative local control plane."""

from __future__ import annotations

import argparse
import shutil
import sqlite3
from collections.abc import Sequence
from pathlib import Path


class MigrationError(RuntimeError):
    """Raised when a control-plane migration cannot complete safely."""


LATEST_SCHEMA_VERSION = 1

_UP_MIGRATIONS = {
    1: """
        CREATE TABLE goals (
            goal_id TEXT PRIMARY KEY,
            objective TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE jobs (
            job_id TEXT PRIMARY KEY,
            goal_id TEXT NOT NULL REFERENCES goals(goal_id),
            state TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE events (
            sequence INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            aggregate_id TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            occurred_at TEXT NOT NULL,
            schema_version TEXT NOT NULL
        );
    """,
}

_DOWN_MIGRATIONS = {
    1: """
        DROP TABLE events;
        DROP TABLE jobs;
        DROP TABLE goals;
    """,
}


def migrate_database(database_path: Path) -> int:
    """Apply every pending migration and return the resulting version."""
    database_path.parent.mkdir(parents=True, exist_ok=True)
    with _connect(database_path) as connection:
        _ensure_version_table(connection)
        _adopt_legacy_schema(connection)
        current = _current_version(connection)
        if current > LATEST_SCHEMA_VERSION:
            raise MigrationError(
                f"database schema {current} is newer than supported "
                f"{LATEST_SCHEMA_VERSION}"
            )
        for version in range(current + 1, LATEST_SCHEMA_VERSION + 1):
            connection.executescript(_UP_MIGRATIONS[version])
            connection.execute(
                "INSERT INTO schema_migrations (version) VALUES (?)", (version,)
            )
    return LATEST_SCHEMA_VERSION


def rollback_database(database_path: Path, backup_path: Path) -> int:
    """Back up the database, then roll one schema version back."""
    if not database_path.is_file():
        raise MigrationError("database does not exist")
    if backup_path.exists():
        raise MigrationError("backup path already exists")
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(database_path, backup_path)
    try:
        with _connect(database_path) as connection:
            _ensure_version_table(connection)
            current = _current_version(connection)
            if current == 0:
                raise MigrationError("database is already at schema version 0")
            connection.executescript(_DOWN_MIGRATIONS[current])
            connection.execute(
                "DELETE FROM schema_migrations WHERE version = ?", (current,)
            )
        return current - 1
    except Exception:
        shutil.copy2(backup_path, database_path)
        raise


def current_schema_version(database_path: Path) -> int:
    """Return the recorded schema version, or zero for an uninitialized file."""
    if not database_path.is_file():
        return 0
    with _connect(database_path) as connection:
        exists = connection.execute(
            "SELECT 1 FROM sqlite_master "
            "WHERE type = 'table' AND name = 'schema_migrations'"
        ).fetchone()
        return _current_version(connection) if exists else 0


def _connect(database_path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(database_path)
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _ensure_version_table(connection: sqlite3.Connection) -> None:
    connection.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations "
        "(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL "
        "DEFAULT CURRENT_TIMESTAMP)"
    )


def _current_version(connection: sqlite3.Connection) -> int:
    row = connection.execute(
        "SELECT COALESCE(MAX(version), 0) FROM schema_migrations"
    ).fetchone()
    return int(row[0])


def _adopt_legacy_schema(connection: sqlite3.Connection) -> None:
    """Record the exact pre-migration P05 schema without rewriting its data."""
    if _current_version(connection) != 0:
        return
    expected = {
        "goals": ("goal_id", "objective", "created_at"),
        "jobs": ("job_id", "goal_id", "state", "created_at"),
        "events": (
            "sequence",
            "event_type",
            "aggregate_id",
            "payload_json",
            "occurred_at",
            "schema_version",
        ),
    }
    present = {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
    }
    legacy_present = present.intersection(expected)
    if not legacy_present:
        return
    if legacy_present != expected.keys():
        raise MigrationError("partial legacy control-plane schema cannot be adopted")
    for table, expected_columns in expected.items():
        actual_columns = tuple(
            row[1] for row in connection.execute(f"PRAGMA table_info({table})")
        )
        if actual_columns != expected_columns:
            raise MigrationError(f"legacy {table} schema does not match version 1")
    connection.execute("INSERT INTO schema_migrations (version) VALUES (1)")


def main(argv: Sequence[str] | None = None) -> int:
    """Run explicit migration or rollback operations."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("upgrade", "rollback", "version"))
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--backup", type=Path)
    arguments = parser.parse_args(argv)

    if arguments.operation == "upgrade":
        version = migrate_database(arguments.database)
    elif arguments.operation == "rollback":
        if arguments.backup is None:
            parser.error("rollback requires --backup")
        version = rollback_database(arguments.database, arguments.backup)
    else:
        version = current_schema_version(arguments.database)
    print(version)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
