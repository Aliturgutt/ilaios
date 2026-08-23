"""Versioned SQLite migrations for the authoritative local control plane."""

from __future__ import annotations

import argparse
import shutil
import sqlite3
from collections.abc import Sequence
from pathlib import Path


class MigrationError(RuntimeError):
    """Raised when a control-plane migration cannot complete safely."""


LATEST_SCHEMA_VERSION = 10

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
    2: """
        CREATE TABLE proposals (
            proposal_id TEXT PRIMARY KEY,
            goal_id TEXT NOT NULL REFERENCES goals(goal_id),
            proposal_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
    """,
    3: """
        CREATE TABLE workflows (
            workflow_id TEXT PRIMARY KEY,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE workflow_tasks (
            workflow_id TEXT NOT NULL REFERENCES workflows(workflow_id),
            task_id TEXT NOT NULL,
            status TEXT NOT NULL,
            max_attempts INTEGER NOT NULL,
            compensation_event_type TEXT,
            PRIMARY KEY (workflow_id, task_id)
        );
        CREATE TABLE attempts (
            attempt_id TEXT PRIMARY KEY,
            workflow_id TEXT NOT NULL,
            task_id TEXT NOT NULL,
            number INTEGER NOT NULL,
            status TEXT NOT NULL,
            deadline TEXT NOT NULL,
            FOREIGN KEY (workflow_id, task_id)
                REFERENCES workflow_tasks(workflow_id, task_id)
        );
        CREATE TABLE checkpoints (
            attempt_id TEXT NOT NULL REFERENCES attempts(attempt_id),
            checkpoint_key TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            PRIMARY KEY (attempt_id, checkpoint_key)
        );
        CREATE TABLE outbox (
            sequence INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id TEXT UNIQUE NOT NULL,
            event_type TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            delivered INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE inbox (
            event_id TEXT PRIMARY KEY,
            payload_json TEXT NOT NULL,
            received_at TEXT NOT NULL
        );
    """,
    4: """
        CREATE TABLE live_events (
            sequence INTEGER PRIMARY KEY AUTOINCREMENT,
            aggregate_id TEXT NOT NULL,
            version INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            state_json TEXT NOT NULL,
            occurred_at TEXT NOT NULL,
            UNIQUE (aggregate_id, version)
        );
        CREATE TABLE live_state (
            aggregate_id TEXT PRIMARY KEY,
            version INTEGER NOT NULL,
            state_json TEXT NOT NULL,
            last_sequence INTEGER NOT NULL
        );
    """,
    5: """
        CREATE TABLE runtime_agents (
            agent_id TEXT PRIMARY KEY,
            authorities_json TEXT NOT NULL
        );
        CREATE TABLE runtime_skills (
            skill_id TEXT PRIMARY KEY,
            digest TEXT NOT NULL,
            authorities_json TEXT NOT NULL,
            content BLOB NOT NULL
        );
        CREATE TABLE runtime_providers (
            provider_id TEXT PRIMARY KEY,
            capabilities_json TEXT NOT NULL,
            deterministic INTEGER NOT NULL,
            enabled INTEGER NOT NULL,
            adapter_kind TEXT NOT NULL
        );
        CREATE TABLE runtime_routes (
            sequence INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_id TEXT NOT NULL,
            skill_id TEXT NOT NULL,
            provider_id TEXT NOT NULL,
            capability TEXT NOT NULL,
            input_sha256 TEXT NOT NULL,
            output_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
    """,
    6: """
        CREATE TABLE scheduler_workers (
            worker_id TEXT PRIMARY KEY,
            capabilities_json TEXT NOT NULL,
            max_concurrent_tasks INTEGER NOT NULL
        );
        CREATE TABLE scheduler_fences (
            task_id TEXT PRIMARY KEY,
            fencing_token INTEGER NOT NULL
        );
        CREATE TABLE scheduler_leases (
            task_id TEXT PRIMARY KEY,
            worker_id TEXT NOT NULL REFERENCES scheduler_workers(worker_id),
            capability TEXT NOT NULL,
            fencing_token INTEGER NOT NULL,
            expires_at TEXT NOT NULL
        );
        CREATE TABLE scheduler_effects (
            task_id TEXT NOT NULL,
            fencing_token INTEGER NOT NULL,
            payload_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            PRIMARY KEY (task_id, fencing_token)
        );
    """,
    7: """
        CREATE TABLE execution_grants (
            grant_id TEXT PRIMARY KEY, subject_id TEXT NOT NULL,
            actions_json TEXT NOT NULL, resources_json TEXT NOT NULL,
            expires_at TEXT NOT NULL, max_side_effects INTEGER NOT NULL,
            max_resources INTEGER NOT NULL, used_side_effects INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE grant_resources (
            grant_id TEXT NOT NULL REFERENCES execution_grants(grant_id),
            resource TEXT NOT NULL, PRIMARY KEY (grant_id, resource)
        );
        CREATE TABLE revoked_grants (
            grant_id TEXT PRIMARY KEY, revoked_at TEXT NOT NULL
        );
        CREATE TABLE stopped_subjects (
            subject_id TEXT PRIMARY KEY, stopped_at TEXT NOT NULL
        );
    """,
    8: """
        CREATE TABLE IF NOT EXISTS web_app_tenants (
            tenant_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            version INTEGER NOT NULL DEFAULT 1 CHECK (version >= 1),
            deleted_at TEXT
        );
        CREATE TABLE IF NOT EXISTS web_app_users (
            tenant_id TEXT NOT NULL REFERENCES web_app_tenants(tenant_id),
            user_id TEXT NOT NULL,
            display_name TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            version INTEGER NOT NULL DEFAULT 1 CHECK (version >= 1),
            deleted_at TEXT,
            PRIMARY KEY (tenant_id, user_id)
        );
        CREATE TABLE IF NOT EXISTS web_app_projects (
            tenant_id TEXT NOT NULL REFERENCES web_app_tenants(tenant_id),
            project_id TEXT NOT NULL,
            owner_user_id TEXT NOT NULL,
            name TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            version INTEGER NOT NULL DEFAULT 1 CHECK (version >= 1),
            deleted_at TEXT,
            PRIMARY KEY (tenant_id, project_id),
            FOREIGN KEY (tenant_id, owner_user_id)
                REFERENCES web_app_users(tenant_id, user_id)
        );
        CREATE TABLE IF NOT EXISTS web_app_goal_context (
            goal_id TEXT PRIMARY KEY REFERENCES goals(goal_id) ON DELETE CASCADE,
            tenant_id TEXT NOT NULL,
            project_id TEXT NOT NULL,
            owner_user_id TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            version INTEGER NOT NULL DEFAULT 1 CHECK (version >= 1),
            deleted_at TEXT,
            UNIQUE (tenant_id, project_id, goal_id),
            FOREIGN KEY (tenant_id, project_id)
                REFERENCES web_app_projects(tenant_id, project_id),
            FOREIGN KEY (tenant_id, owner_user_id)
                REFERENCES web_app_users(tenant_id, user_id)
        );
        CREATE TABLE IF NOT EXISTS web_app_workflow_context (
            workflow_id TEXT PRIMARY KEY REFERENCES workflows(workflow_id) ON DELETE CASCADE,
            tenant_id TEXT NOT NULL,
            project_id TEXT NOT NULL,
            owner_user_id TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            version INTEGER NOT NULL DEFAULT 1 CHECK (version >= 1),
            deleted_at TEXT,
            UNIQUE (tenant_id, project_id, workflow_id),
            FOREIGN KEY (tenant_id, project_id)
                REFERENCES web_app_projects(tenant_id, project_id),
            FOREIGN KEY (tenant_id, owner_user_id)
                REFERENCES web_app_users(tenant_id, user_id)
        );
        CREATE TABLE IF NOT EXISTS web_app_agents (
            tenant_id TEXT NOT NULL,
            project_id TEXT NOT NULL,
            agent_id TEXT NOT NULL REFERENCES runtime_agents(agent_id),
            owner_user_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            version INTEGER NOT NULL DEFAULT 1 CHECK (version >= 1),
            deleted_at TEXT,
            PRIMARY KEY (tenant_id, project_id, agent_id),
            FOREIGN KEY (tenant_id, project_id)
                REFERENCES web_app_projects(tenant_id, project_id),
            FOREIGN KEY (tenant_id, owner_user_id)
                REFERENCES web_app_users(tenant_id, user_id)
        );
        CREATE TABLE IF NOT EXISTS web_app_approvals (
            approval_id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            project_id TEXT NOT NULL,
            workflow_id TEXT NOT NULL,
            requester_user_id TEXT NOT NULL,
            reviewer_user_id TEXT,
            state TEXT NOT NULL CHECK (
                state IN ('PENDING', 'REVIEWING', 'APPROVED', 'REJECTED')
            ),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            version INTEGER NOT NULL DEFAULT 1 CHECK (version >= 1),
            UNIQUE (tenant_id, project_id, approval_id),
            FOREIGN KEY (tenant_id, project_id, workflow_id)
                REFERENCES web_app_workflow_context(
                    tenant_id, project_id, workflow_id
                ),
            FOREIGN KEY (tenant_id, requester_user_id)
                REFERENCES web_app_users(tenant_id, user_id),
            FOREIGN KEY (tenant_id, reviewer_user_id)
                REFERENCES web_app_users(tenant_id, user_id)
        );
        CREATE TABLE IF NOT EXISTS web_app_evidence (
            evidence_id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            project_id TEXT NOT NULL,
            workflow_id TEXT,
            owner_user_id TEXT,
            artifact_sha256 TEXT NOT NULL CHECK (length(artifact_sha256) = 64),
            status TEXT NOT NULL CHECK (
                status IN ('GENERATED', 'REVIEWED', 'VERIFIED', 'FAILED')
            ),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            version INTEGER NOT NULL DEFAULT 1 CHECK (version >= 1),
            UNIQUE (tenant_id, project_id, evidence_id),
            FOREIGN KEY (tenant_id, project_id)
                REFERENCES web_app_projects(tenant_id, project_id),
            FOREIGN KEY (tenant_id, project_id, workflow_id)
                REFERENCES web_app_workflow_context(
                    tenant_id, project_id, workflow_id
                ),
            FOREIGN KEY (tenant_id, owner_user_id)
                REFERENCES web_app_users(tenant_id, user_id)
        );
        CREATE TABLE IF NOT EXISTS web_app_outputs (
            output_id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            project_id TEXT NOT NULL,
            workflow_id TEXT,
            owner_user_id TEXT NOT NULL,
            evidence_id TEXT,
            kind TEXT NOT NULL,
            artifact_sha256 TEXT CHECK (
                artifact_sha256 IS NULL OR length(artifact_sha256) = 64
            ),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            version INTEGER NOT NULL DEFAULT 1 CHECK (version >= 1),
            deleted_at TEXT,
            UNIQUE (tenant_id, project_id, output_id),
            FOREIGN KEY (tenant_id, project_id)
                REFERENCES web_app_projects(tenant_id, project_id),
            FOREIGN KEY (tenant_id, project_id, workflow_id)
                REFERENCES web_app_workflow_context(
                    tenant_id, project_id, workflow_id
                ),
            FOREIGN KEY (tenant_id, owner_user_id)
                REFERENCES web_app_users(tenant_id, user_id),
            FOREIGN KEY (tenant_id, project_id, evidence_id)
                REFERENCES web_app_evidence(tenant_id, project_id, evidence_id)
        );
        CREATE TABLE IF NOT EXISTS web_app_cost_records (
            cost_record_id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            project_id TEXT NOT NULL,
            workflow_id TEXT,
            owner_user_id TEXT,
            amount_minor INTEGER NOT NULL CHECK (amount_minor >= 0),
            currency_code TEXT NOT NULL CHECK (
                length(currency_code) = 3 AND currency_code = upper(currency_code)
            ),
            created_at TEXT NOT NULL,
            UNIQUE (tenant_id, project_id, cost_record_id),
            FOREIGN KEY (tenant_id, project_id)
                REFERENCES web_app_projects(tenant_id, project_id),
            FOREIGN KEY (tenant_id, project_id, workflow_id)
                REFERENCES web_app_workflow_context(
                    tenant_id, project_id, workflow_id
                ),
            FOREIGN KEY (tenant_id, owner_user_id)
                REFERENCES web_app_users(tenant_id, user_id)
        );
        CREATE TABLE IF NOT EXISTS web_app_sessions (
            session_id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            project_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            revoked_at TEXT,
            version INTEGER NOT NULL DEFAULT 1 CHECK (version >= 1),
            UNIQUE (tenant_id, project_id, session_id),
            FOREIGN KEY (tenant_id, project_id)
                REFERENCES web_app_projects(tenant_id, project_id),
            FOREIGN KEY (tenant_id, user_id)
                REFERENCES web_app_users(tenant_id, user_id)
        );
        CREATE TABLE IF NOT EXISTS web_app_integrations (
            integration_id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL REFERENCES web_app_tenants(tenant_id),
            project_id TEXT,
            owner_user_id TEXT,
            kind TEXT NOT NULL,
            external_ref TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            version INTEGER NOT NULL DEFAULT 1 CHECK (version >= 1),
            deleted_at TEXT,
            UNIQUE (tenant_id, project_id, integration_id),
            FOREIGN KEY (tenant_id, project_id)
                REFERENCES web_app_projects(tenant_id, project_id),
            FOREIGN KEY (tenant_id, owner_user_id)
                REFERENCES web_app_users(tenant_id, user_id)
        );
    """,
    9: """
        CREATE TABLE IF NOT EXISTS identity_tenants (
            tenant_id TEXT PRIMARY KEY,
            status TEXT NOT NULL CHECK (status IN ('ACTIVE', 'SUSPENDED')),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS identity_users (
            user_id TEXT PRIMARY KEY,
            enabled INTEGER NOT NULL CHECK (enabled IN (0, 1)),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS identity_memberships (
            tenant_id TEXT NOT NULL REFERENCES identity_tenants(tenant_id),
            user_id TEXT NOT NULL REFERENCES identity_users(user_id),
            role TEXT NOT NULL,
            status TEXT NOT NULL CHECK (status IN ('ACTIVE', 'SUSPENDED', 'REVOKED')),
            is_primary INTEGER NOT NULL DEFAULT 0 CHECK (is_primary IN (0, 1)),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (tenant_id, user_id)
        );
        CREATE TABLE IF NOT EXISTS identity_accounts (
            identity_account_id TEXT PRIMARY KEY,
            provider TEXT NOT NULL,
            issuer_namespace TEXT NOT NULL DEFAULT '',
            provider_subject TEXT NOT NULL,
            user_id TEXT NOT NULL,
            tenant_id TEXT NOT NULL,
            verified_email TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE (provider, issuer_namespace, provider_subject),
            FOREIGN KEY (tenant_id, user_id)
                REFERENCES identity_memberships(tenant_id, user_id)
        );
        CREATE TABLE IF NOT EXISTS identity_sessions (
            session_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            tenant_id TEXT NOT NULL,
            credential_hash TEXT NOT NULL CHECK (length(credential_hash) = 64),
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            revoked_at TEXT,
            FOREIGN KEY (tenant_id, user_id)
                REFERENCES identity_memberships(tenant_id, user_id)
        );
        CREATE TABLE IF NOT EXISTS identity_entitlements (
            tenant_id TEXT NOT NULL REFERENCES identity_tenants(tenant_id),
            entitlement_key TEXT NOT NULL,
            state TEXT NOT NULL CHECK (state IN ('ACTIVE', 'SUSPENDED', 'EXPIRED', 'REVOKED')),
            limit_value INTEGER CHECK (limit_value IS NULL OR limit_value >= 0),
            updated_at TEXT NOT NULL,
            PRIMARY KEY (tenant_id, entitlement_key)
        );
    """,
    10: """
        CREATE TABLE identity_email_challenges (
            challenge_id TEXT PRIMARY KEY,
            email TEXT NOT NULL,
            secret_digest TEXT NOT NULL CHECK (length(secret_digest) = 64),
            issued_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            consumed_at TEXT
        );
    """,
}

_DOWN_MIGRATIONS = {
    1: """
        DROP TABLE events;
        DROP TABLE jobs;
        DROP TABLE goals;
    """,
    2: """
        DROP TABLE proposals;
    """,
    3: """
        DROP TABLE inbox;
        DROP TABLE outbox;
        DROP TABLE checkpoints;
        DROP TABLE attempts;
        DROP TABLE workflow_tasks;
        DROP TABLE workflows;
    """,
    4: """
        DROP TABLE live_state;
        DROP TABLE live_events;
    """,
    5: """
        DROP TABLE runtime_routes;
        DROP TABLE runtime_providers;
        DROP TABLE runtime_skills;
        DROP TABLE runtime_agents;
    """,
    6: """
        DROP TABLE scheduler_effects;
        DROP TABLE scheduler_leases;
        DROP TABLE scheduler_fences;
        DROP TABLE scheduler_workers;
    """,
    7: """
        DROP TABLE stopped_subjects;
        DROP TABLE revoked_grants;
        DROP TABLE grant_resources;
        DROP TABLE execution_grants;
    """,
    8: """
        SELECT 1;
    """,
    9: """
        SELECT 1;
    """,
    10: """
        DROP TABLE identity_email_challenges;
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
