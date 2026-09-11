"""SF-20 migration admission path-selection and review-evidence tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from services.software_factory_db_migration_admission import (
    _changeset_sha256,
    _review_acceptance,
    is_real_migration_path,
)
from services.software_factory_db_migration_safety import (
    DBMigrationSafetyError,
    SoftwareFactoryDBMigrationSafety,
)
from services.software_factory_secret_scanning import ChangedLine

_BASE_SHA = "a" * 40
_AUTHOR = "author@example.com"
_REVIEWER = "reviewer@example.com"


def test_real_migration_paths_are_selected() -> None:
    assert is_real_migration_path("db/migrations/0001_init.py") is True
    assert is_real_migration_path("alembic/versions/0002_expand.py") is True
    assert is_real_migration_path("schema/0003_backfill.sql") is True
    assert is_real_migration_path("services/control_plane/migrations.py") is True


def test_sf20_implementation_and_tests_are_not_scan_subjects() -> None:
    assert (
        is_real_migration_path("services/software_factory_db_migration_safety.py")
        is False
    )
    assert (
        is_real_migration_path("tests/test_software_factory_db_migration_safety.py")
        is False
    )
    assert is_real_migration_path("docs/governance/SF20_DB_MIGRATION_SAFETY.md") is False


def _unique_index_lines() -> tuple[ChangedLine, ...]:
    return (
        ChangedLine(
            path="db/migrations/0011_unique_email.sql",
            line=1,
            text="CREATE UNIQUE INDEX idx_users_email ON users(email);",
        ),
    )


def _review_report(lines: tuple[ChangedLine, ...]):  # type: ignore[no-untyped-def]
    return SoftwareFactoryDBMigrationSafety().scan_lines(
        lines,
        scope="TEST_CHANGESET",
        base_sha=_BASE_SHA,
    )


def _evidence_payload(lines: tuple[ChangedLine, ...]) -> dict[str, object]:
    report = _review_report(lines)
    return {
        "schema_version": 1,
        "decision": "ACCEPT",
        "base_sha": _BASE_SHA,
        "changeset_sha256": _changeset_sha256(lines),
        "changeset_author": _AUTHOR,
        "reviewer": _REVIEWER,
        "reviewed_at": "2026-09-11T10:00:00+00:00",
        "migration_files": list(report.migration_files),
        "finding_fingerprints": sorted(
            finding.fingerprint for finding in report.findings
        ),
        "review_notes": "Duplicate pre-validation and rollback plan independently reviewed.",
    }


def _write_evidence(
    root: Path,
    lines: tuple[ChangedLine, ...],
    payload: dict[str, object] | str,
) -> Path:
    directory = root / "docs/governance/sf20-reviews"
    directory.mkdir(parents=True)
    path = directory / f"{_BASE_SHA}-{_changeset_sha256(lines)}.json"
    if isinstance(payload, str):
        path.write_text(payload, encoding="utf-8")
    else:
        path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_review_required_without_evidence_remains_unaccepted(tmp_path: Path) -> None:
    lines = _unique_index_lines()
    acceptance = _review_acceptance(
        tmp_path,
        report=_review_report(lines),
        selected=lines,
        base_sha=_BASE_SHA,
        change_author=_AUTHOR,
    )

    assert acceptance.accepted is False
    assert acceptance.evidence_path is not None
    assert acceptance.evidence_sha256 is None


def test_malformed_review_evidence_fails_closed(tmp_path: Path) -> None:
    lines = _unique_index_lines()
    _write_evidence(tmp_path, lines, "{not-json")

    with pytest.raises(DBMigrationSafetyError, match="valid UTF-8 JSON"):
        _review_acceptance(
            tmp_path,
            report=_review_report(lines),
            selected=lines,
            base_sha=_BASE_SHA,
            change_author=_AUTHOR,
        )


def test_wrong_changeset_digest_fails_closed(tmp_path: Path) -> None:
    lines = _unique_index_lines()
    payload = _evidence_payload(lines)
    payload["changeset_sha256"] = "b" * 64
    _write_evidence(tmp_path, lines, payload)

    with pytest.raises(DBMigrationSafetyError, match="changeset digest does not match"):
        _review_acceptance(
            tmp_path,
            report=_review_report(lines),
            selected=lines,
            base_sha=_BASE_SHA,
            change_author=_AUTHOR,
        )


def test_wrong_changeset_author_fails_closed(tmp_path: Path) -> None:
    lines = _unique_index_lines()
    payload = _evidence_payload(lines)
    payload["changeset_author"] = "other@example.com"
    _write_evidence(tmp_path, lines, payload)

    with pytest.raises(DBMigrationSafetyError, match="changeset author does not match"):
        _review_acceptance(
            tmp_path,
            report=_review_report(lines),
            selected=lines,
            base_sha=_BASE_SHA,
            change_author=_AUTHOR,
        )


def test_same_author_cannot_self_accept_review(tmp_path: Path) -> None:
    lines = _unique_index_lines()
    payload = _evidence_payload(lines)
    payload["reviewer"] = _AUTHOR
    _write_evidence(tmp_path, lines, payload)

    with pytest.raises(DBMigrationSafetyError, match="reviewer must be independent"):
        _review_acceptance(
            tmp_path,
            report=_review_report(lines),
            selected=lines,
            base_sha=_BASE_SHA,
            change_author=_AUTHOR,
        )


def test_wrong_finding_fingerprint_fails_closed(tmp_path: Path) -> None:
    lines = _unique_index_lines()
    payload = _evidence_payload(lines)
    payload["finding_fingerprints"] = ["c" * 64]
    _write_evidence(tmp_path, lines, payload)

    with pytest.raises(DBMigrationSafetyError, match="finding fingerprints do not match"):
        _review_acceptance(
            tmp_path,
            report=_review_report(lines),
            selected=lines,
            base_sha=_BASE_SHA,
            change_author=_AUTHOR,
        )


def test_exact_independent_review_evidence_is_accepted(tmp_path: Path) -> None:
    lines = _unique_index_lines()
    _write_evidence(tmp_path, lines, _evidence_payload(lines))

    acceptance = _review_acceptance(
        tmp_path,
        report=_review_report(lines),
        selected=lines,
        base_sha=_BASE_SHA,
        change_author=_AUTHOR,
    )

    assert acceptance.accepted is True
    assert acceptance.reviewer == _REVIEWER
    assert acceptance.evidence_sha256 is not None
    assert len(acceptance.finding_fingerprints) == 1


def test_block_finding_cannot_be_accepted_by_review_evidence(tmp_path: Path) -> None:
    lines = (
        ChangedLine(
            path="db/migrations/danger.sql",
            line=1,
            text="DROP DATABASE customer_data;",
        ),
        ChangedLine(
            path="db/migrations/danger.sql",
            line=2,
            text="CREATE UNIQUE INDEX idx_x ON x(id);",
        ),
    )
    _write_evidence(tmp_path, lines, _evidence_payload(lines))

    acceptance = _review_acceptance(
        tmp_path,
        report=_review_report(lines),
        selected=lines,
        base_sha=_BASE_SHA,
        change_author=_AUTHOR,
    )

    assert acceptance.accepted is False
