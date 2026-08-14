"""SF-20 database migration safety tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from services.software_factory_db_migration_safety import (
    DBMigrationSafetyError,
    MigrationDisposition,
    SoftwareFactoryDBMigrationSafety,
)
from services.software_factory_secret_scanning import ChangedLine

REPO_ROOT = Path(__file__).resolve().parents[1]


def _line(path: str, line: int, text: str) -> ChangedLine:
    return ChangedLine(path=path, line=line, text=text)


def _scan(*lines: ChangedLine):  # type: ignore[no-untyped-def]
    return SoftwareFactoryDBMigrationSafety().scan_lines(
        lines,
        scope="TEST_CHANGESET",
    )


def test_additive_migration_passes_without_execution_authority() -> None:
    report = _scan(
        _line("db/migrations/0008_add_widget.sql", 1, "CREATE TABLE widgets ("),
        _line("db/migrations/0008_add_widget.sql", 2, "id TEXT PRIMARY KEY"),
        _line("db/migrations/0008_add_widget.sql", 3, ");"),
        _line(
            "db/migrations/0008_add_widget.sql",
            4,
            "ALTER TABLE widgets ADD COLUMN description TEXT;",
        ),
    )

    assert report.passed is True
    assert report.disposition is MigrationDisposition.PASS
    assert report.findings == ()
    assert report.migration_execution_authorized is False
    assert report.acceptance_authorized is False
    assert report.promotion_authorized is False
    assert report.deployment_authorized is False
    assert report.production_applied is False
    assert report.subject_mutated is False


def test_drop_table_requires_independent_review_and_recovery() -> None:
    report = _scan(
        _line("db/migrations/0009_contract.sql", 10, "DROP TABLE legacy_orders;")
    )

    assert report.passed is False
    assert report.disposition is MigrationDisposition.REVIEW_REQUIRED
    assert report.independent_review_required is True
    finding = report.findings[0]
    assert finding.finding_id == "SF20-DROP-TABLE-COLUMN"
    assert finding.backup_required is True
    assert finding.rollback_or_compensation_required is True


def test_database_or_schema_destruction_is_blocked() -> None:
    report = _scan(
        _line("db/migrations/danger.sql", 1, "DROP DATABASE customer_data;")
    )

    assert report.passed is False
    assert report.disposition is MigrationDisposition.BLOCK
    assert "SF20-DROP-DATABASE-SCHEMA" in {
        finding.finding_id for finding in report.findings
    }


def test_unbounded_delete_and_update_are_blocked() -> None:
    report = _scan(
        _line("db/migrations/data.sql", 1, "DELETE FROM sessions;"),
        _line("db/migrations/data.sql", 2, "UPDATE accounts SET active = 0;"),
    )

    ids = {finding.finding_id for finding in report.findings}
    assert report.disposition is MigrationDisposition.BLOCK
    assert "SF20-UNBOUNDED-DELETE" in ids
    assert "SF20-UNBOUNDED-UPDATE" in ids


def test_bounded_data_rewrite_still_requires_review() -> None:
    report = _scan(
        _line(
            "db/migrations/backfill.sql",
            1,
            "UPDATE accounts SET normalized = 1 WHERE account_id = 'bounded-id';",
        ),
        _line(
            "db/migrations/backfill.sql",
            2,
            "DELETE FROM sessions WHERE expires_at < CURRENT_TIMESTAMP;",
        ),
    )

    assert report.disposition is MigrationDisposition.REVIEW_REQUIRED
    assert "SF20-DATA-REWRITE" in {
        finding.finding_id for finding in report.findings
    }
    assert "SF20-UNBOUNDED-UPDATE" not in {
        finding.finding_id for finding in report.findings
    }
    assert "SF20-UNBOUNDED-DELETE" not in {
        finding.finding_id for finding in report.findings
    }


def test_split_destructive_statement_cannot_bypass_scanner() -> None:
    report = _scan(
        _line("db/migrations/split.sql", 20, "DROP"),
        _line("db/migrations/split.sql", 21, "TABLE old_records;"),
    )

    assert report.disposition is MigrationDisposition.REVIEW_REQUIRED
    assert report.findings[0].line == 20
    assert report.findings[0].finding_id == "SF20-DROP-TABLE-COLUMN"


def test_non_migration_source_is_out_of_scope() -> None:
    report = _scan(
        _line("services/example.py", 1, 'message = "DROP DATABASE is documentation"')
    )

    assert report.passed is True
    assert report.migration_files == ()
    assert report.scanned_added_lines == 0


def test_report_is_deterministic() -> None:
    lines = (
        _line("db/migrations/0010_index.sql", 1, "CREATE INDEX idx_name ON users(name);"),
    )
    gate = SoftwareFactoryDBMigrationSafety()

    first = gate.scan_lines(lines, scope="REVIEWED_CHANGESET")
    second = gate.scan_lines(lines, scope="REVIEWED_CHANGESET")

    assert first == second
    assert len(first.report_sha256) == 64
    assert first.disposition is MigrationDisposition.REVIEW_REQUIRED


def test_invalid_diff_sha_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(DBMigrationSafetyError, match="exact lowercase 40-hex SHA"):
        SoftwareFactoryDBMigrationSafety().scan_diff(
            tmp_path,
            base_sha="main",
            head_sha="1" * 40,
        )


def test_repository_control_plane_migration_contract_is_currently_recoverable() -> None:
    line = _line(
        "services/control_plane/migrations.py",
        1,
        "# migration authority touched for structural audit",
    )
    report = SoftwareFactoryDBMigrationSafety().scan_lines(
        (line,),
        scope="TEST_CHANGESET",
        repository_root=REPO_ROOT,
    )

    assert "SF20-CONTROL-PLANE-CONTRACT" not in {
        finding.finding_id for finding in report.findings
    }


def test_control_plane_contract_blocks_missing_down_pair(tmp_path: Path) -> None:
    path = tmp_path / "services/control_plane/migrations.py"
    path.parent.mkdir(parents=True)
    path.write_text(
        """\
import shutil
LATEST_SCHEMA_VERSION = 2
_UP_MIGRATIONS = {1: \"CREATE TABLE one(id INT);\", 2: \"CREATE TABLE two(id INT);\"}
_DOWN_MIGRATIONS = {1: \"DROP TABLE one;\"}
def rollback_database(database_path, backup_path, connection, current):
    if backup_path.exists():
        raise RuntimeError
    shutil.copy2(database_path, backup_path)
    try:
        connection.executescript(_DOWN_MIGRATIONS[current])
    except Exception:
        shutil.copy2(backup_path, database_path)
        raise
def connect(connection):
    connection.execute(\"PRAGMA foreign_keys = ON\")
""",
        encoding="utf-8",
    )
    report = SoftwareFactoryDBMigrationSafety().scan_lines(
        (
            _line(
                "services/control_plane/migrations.py",
                1,
                "LATEST_SCHEMA_VERSION = 2",
            ),
        ),
        scope="TEST_CHANGESET",
        repository_root=tmp_path,
    )

    assert report.disposition is MigrationDisposition.BLOCK
    control_findings = [
        finding
        for finding in report.findings
        if finding.finding_id == "SF20-CONTROL-PLANE-CONTRACT"
    ]
    assert control_findings
    assert any("pair every up migration" in finding.reason for finding in control_findings)
