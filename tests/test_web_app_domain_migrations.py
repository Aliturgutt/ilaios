"""Phase-2 Web App domain/data-model migration acceptance tests."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from services.control_plane import migrations
from services.control_plane.migrations import (
    LATEST_SCHEMA_VERSION,
    MigrationError,
    current_schema_version,
    migrate_database,
    rollback_database,
)


_EXPECTED_TABLES = {
    "web_app_tenants",
    "web_app_users",
    "web_app_projects",
    "web_app_goal_context",
    "web_app_workflow_context",
    "web_app_agents",
    "web_app_approvals",
    "web_app_evidence",
    "web_app_outputs",
    "web_app_cost_records",
    "web_app_sessions",
    "web_app_integrations",
}

_EXPECTED_INDEXES = {
    "idx_web_app_projects_tenant_updated",
    "idx_web_app_goal_context_project",
    "idx_web_app_workflow_context_project",
    "idx_web_app_agents_project",
    "idx_web_app_approvals_project_state",
    "idx_web_app_evidence_project_status",
    "idx_web_app_outputs_project_updated",
    "idx_web_app_cost_records_project_created",
    "idx_web_app_sessions_user",
    "idx_web_app_integrations_tenant_kind",
}


def _connect(database: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(database)
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _migrate_through_v7(database: Path) -> None:
    with _connect(database) as connection:
        connection.execute(
            "CREATE TABLE schema_migrations "
            "(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL "
            "DEFAULT CURRENT_TIMESTAMP)"
        )
        for version in range(1, 8):
            connection.executescript(migrations._UP_MIGRATIONS[version])
            connection.execute(
                "INSERT INTO schema_migrations (version) VALUES (?)", (version,)
            )


def _seed_project_context(connection: sqlite3.Connection) -> None:
    connection.execute(
        "INSERT INTO web_app_tenants "
        "(tenant_id, name, created_at, updated_at, version) "
        "VALUES ('tenant-1', 'Tenant One', '2026-08-20T09:00:00Z', "
        "'2026-08-20T09:00:00Z', 1)"
    )
    connection.execute(
        "INSERT INTO web_app_users "
        "(tenant_id, user_id, display_name, created_at, updated_at, version) "
        "VALUES ('tenant-1', 'user-1', 'Owner', '2026-08-20T09:00:00Z', "
        "'2026-08-20T09:00:00Z', 1)"
    )
    connection.execute(
        "INSERT INTO web_app_projects "
        "(tenant_id, project_id, owner_user_id, name, created_at, updated_at, version) "
        "VALUES ('tenant-1', 'project-1', 'user-1', 'Project One', "
        "'2026-08-20T09:00:00Z', '2026-08-20T09:00:00Z', 1)"
    )
    connection.execute(
        "INSERT INTO workflows (workflow_id, status, created_at) "
        "VALUES ('workflow-1', 'planning', '2026-08-20T09:00:00Z')"
    )
    connection.execute(
        "INSERT INTO web_app_workflow_context "
        "(workflow_id, tenant_id, project_id, owner_user_id, updated_at, version) "
        "VALUES ('workflow-1', 'tenant-1', 'project-1', 'user-1', "
        "'2026-08-20T09:00:00Z', 1)"
    )


def test_phase2_migration_creates_domain_schema_indexes_and_foreign_keys(
    tmp_path: Path,
) -> None:
    database = tmp_path / "state.sqlite3"
    assert migrate_database(database) == 8 == LATEST_SCHEMA_VERSION

    with _connect(database) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        indexes = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'index'"
            ).fetchall()
        }
        workflow_fks = connection.execute(
            "PRAGMA foreign_key_list(web_app_workflow_context)"
        ).fetchall()

    assert _EXPECTED_TABLES <= tables
    assert _EXPECTED_INDEXES <= indexes
    assert {row[2] for row in workflow_fks} >= {
        "workflows",
        "web_app_projects",
        "web_app_users",
    }


def test_phase2_upgrade_from_v7_preserves_authoritative_records_and_adds_context(
    tmp_path: Path,
) -> None:
    database = tmp_path / "upgrade.sqlite3"
    _migrate_through_v7(database)
    with _connect(database) as connection:
        connection.execute(
            "INSERT INTO goals (goal_id, objective, created_at) "
            "VALUES ('goal-1', 'Preserve goal', '2026-08-20T09:00:00Z')"
        )
        connection.execute(
            "INSERT INTO workflows (workflow_id, status, created_at) "
            "VALUES ('workflow-1', 'planning', '2026-08-20T09:00:00Z')"
        )
        connection.execute(
            "INSERT INTO runtime_agents (agent_id, authorities_json) "
            "VALUES ('agent-1', '[]')"
        )

    assert migrate_database(database) == 8
    assert migrate_database(database) == 8

    with _connect(database) as connection:
        assert connection.execute(
            "SELECT objective FROM goals WHERE goal_id = 'goal-1'"
        ).fetchone() == ("Preserve goal",)
        assert connection.execute(
            "SELECT status FROM workflows WHERE workflow_id = 'workflow-1'"
        ).fetchone() == ("planning",)
        _seed_project_context_without_workflow(connection)
        connection.execute(
            "INSERT INTO web_app_goal_context "
            "(goal_id, tenant_id, project_id, owner_user_id, updated_at, version) "
            "VALUES ('goal-1', 'tenant-1', 'project-1', 'user-1', "
            "'2026-08-20T09:00:00Z', 1)"
        )
        connection.execute(
            "INSERT INTO web_app_workflow_context "
            "(workflow_id, tenant_id, project_id, owner_user_id, updated_at, version) "
            "VALUES ('workflow-1', 'tenant-1', 'project-1', 'user-1', "
            "'2026-08-20T09:00:00Z', 1)"
        )
        connection.execute(
            "INSERT INTO web_app_agents "
            "(tenant_id, project_id, agent_id, owner_user_id, created_at, updated_at, version) "
            "VALUES ('tenant-1', 'project-1', 'agent-1', 'user-1', "
            "'2026-08-20T09:00:00Z', '2026-08-20T09:00:00Z', 1)"
        )
        migration_count = connection.execute(
            "SELECT COUNT(*) FROM schema_migrations WHERE version = 8"
        ).fetchone()

    assert migration_count == (1,)


def _seed_project_context_without_workflow(connection: sqlite3.Connection) -> None:
    connection.execute(
        "INSERT INTO web_app_tenants "
        "(tenant_id, name, created_at, updated_at, version) "
        "VALUES ('tenant-1', 'Tenant One', '2026-08-20T09:00:00Z', "
        "'2026-08-20T09:00:00Z', 1)"
    )
    connection.execute(
        "INSERT INTO web_app_users "
        "(tenant_id, user_id, display_name, created_at, updated_at, version) "
        "VALUES ('tenant-1', 'user-1', 'Owner', '2026-08-20T09:00:00Z', "
        "'2026-08-20T09:00:00Z', 1)"
    )
    connection.execute(
        "INSERT INTO web_app_projects "
        "(tenant_id, project_id, owner_user_id, name, created_at, updated_at, version) "
        "VALUES ('tenant-1', 'project-1', 'user-1', 'Project One', "
        "'2026-08-20T09:00:00Z', '2026-08-20T09:00:00Z', 1)"
    )


def test_phase2_composite_foreign_keys_fail_closed_on_cross_tenant_project(
    tmp_path: Path,
) -> None:
    database = tmp_path / "tenant.sqlite3"
    migrate_database(database)
    with _connect(database) as connection:
        _seed_project_context(connection)
        connection.execute(
            "INSERT INTO web_app_tenants "
            "(tenant_id, name, created_at, updated_at, version) "
            "VALUES ('tenant-2', 'Tenant Two', '2026-08-20T09:00:00Z', "
            "'2026-08-20T09:00:00Z', 1)"
        )
        connection.execute(
            "INSERT INTO web_app_users "
            "(tenant_id, user_id, display_name, created_at, updated_at, version) "
            "VALUES ('tenant-2', 'user-2', 'Other', '2026-08-20T09:00:00Z', "
            "'2026-08-20T09:00:00Z', 1)"
        )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO web_app_approvals "
                "(approval_id, tenant_id, project_id, workflow_id, requester_user_id, "
                "state, created_at, updated_at, version) VALUES "
                "('approval-x', 'tenant-2', 'project-1', 'workflow-1', 'user-2', "
                "'PENDING', '2026-08-20T09:00:00Z', '2026-08-20T09:00:00Z', 1)"
            )


def test_phase2_constraints_reject_invalid_versions_states_and_artifact_digests(
    tmp_path: Path,
) -> None:
    database = tmp_path / "constraints.sqlite3"
    migrate_database(database)
    with _connect(database) as connection:
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO web_app_tenants "
                "(tenant_id, name, created_at, updated_at, version) "
                "VALUES ('bad', 'Bad', '2026-08-20T09:00:00Z', "
                "'2026-08-20T09:00:00Z', 0)"
            )
        _seed_project_context(connection)
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO web_app_approvals "
                "(approval_id, tenant_id, project_id, workflow_id, requester_user_id, "
                "state, created_at, updated_at, version) VALUES "
                "('approval-bad', 'tenant-1', 'project-1', 'workflow-1', 'user-1', "
                "'MAYBE', '2026-08-20T09:00:00Z', '2026-08-20T09:00:00Z', 1)"
            )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO web_app_evidence "
                "(evidence_id, tenant_id, project_id, workflow_id, owner_user_id, "
                "artifact_sha256, status, created_at, updated_at, version) VALUES "
                "('evidence-bad', 'tenant-1', 'project-1', 'workflow-1', 'user-1', "
                "'short', 'GENERATED', '2026-08-20T09:00:00Z', "
                "'2026-08-20T09:00:00Z', 1)"
            )


def test_phase2_rollback_removes_only_phase2_schema_and_preserves_base_data(
    tmp_path: Path,
) -> None:
    database = tmp_path / "rollback.sqlite3"
    backup = tmp_path / "rollback-backup.sqlite3"
    migrate_database(database)
    with _connect(database) as connection:
        connection.execute(
            "INSERT INTO goals (goal_id, objective, created_at) "
            "VALUES ('goal-rollback', 'Keep me', '2026-08-20T09:00:00Z')"
        )

    assert rollback_database(database, backup) == 7
    assert current_schema_version(database) == 7
    assert current_schema_version(backup) == 8

    with _connect(database) as connection:
        assert connection.execute(
            "SELECT objective FROM goals WHERE goal_id = 'goal-rollback'"
        ).fetchone() == ("Keep me",)
        phase2_table = connection.execute(
            "SELECT 1 FROM sqlite_master "
            "WHERE type = 'table' AND name = 'web_app_projects'"
        ).fetchone()
    assert phase2_table is None

    with _connect(backup) as connection:
        assert connection.execute(
            "SELECT 1 FROM sqlite_master "
            "WHERE type = 'table' AND name = 'web_app_projects'"
        ).fetchone() == (1,)


def test_phase2_migration_rejects_newer_unknown_schema(tmp_path: Path) -> None:
    database = tmp_path / "future.sqlite3"
    with _connect(database) as connection:
        connection.execute(
            "CREATE TABLE schema_migrations "
            "(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL "
            "DEFAULT CURRENT_TIMESTAMP)"
        )
        connection.execute(
            "INSERT INTO schema_migrations (version) VALUES (?)",
            (LATEST_SCHEMA_VERSION + 1,),
        )

    with pytest.raises(MigrationError, match="newer than supported"):
        migrate_database(database)
