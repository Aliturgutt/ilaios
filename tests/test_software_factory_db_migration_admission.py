"""SF-20 migration admission path-selection and review-evidence tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from services import software_factory_db_migration_admission as admission_module
from services.software_factory_db_migration_admission import (
    _migration_changeset_sha256,
    _review_acceptance,
    is_real_migration_path,
)
from services.software_factory_db_migration_safety import (
    DBMigrationSafetyError,
    SoftwareFactoryDBMigrationSafety,
)
from services.software_factory_secret_scanning import ChangedLine

_BASE_SHA = "a" * 40
_HEAD_SHA = "b" * 40
_EVIDENCE_COMMIT_SHA = "c" * 40
_AUTHOR = "author@example.com"
_REVIEWER = "reviewer@example.com"
_CHANGESET_SHA256 = "9" * 64


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
        "changeset_sha256": _CHANGESET_SHA256,
        "changeset_authors": [_AUTHOR],
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
    payload: dict[str, object] | str,
) -> Path:
    directory = root / "docs/governance/sf20-reviews"
    directory.mkdir(parents=True)
    path = directory / f"{_CHANGESET_SHA256}.json"
    if isinstance(payload, str):
        path.write_text(payload, encoding="utf-8")
    else:
        path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _accept(root: Path, lines: tuple[ChangedLine, ...]):  # type: ignore[no-untyped-def]
    return _review_acceptance(
        root,
        report=_review_report(lines),
        selected=lines,
        changeset_sha256=_CHANGESET_SHA256,
        subject_head_sha=_HEAD_SHA,
        expected_base_sha=_BASE_SHA,
        changeset_authors=(_AUTHOR,),
    )


def test_review_required_without_evidence_remains_unaccepted(tmp_path: Path) -> None:
    lines = _unique_index_lines()
    acceptance = _accept(tmp_path, lines)

    assert acceptance.accepted is False
    assert acceptance.evidence_path is not None
    assert acceptance.evidence_sha256 is None


def test_malformed_review_evidence_fails_closed(tmp_path: Path) -> None:
    lines = _unique_index_lines()
    _write_evidence(tmp_path, "{not-json")

    with pytest.raises(DBMigrationSafetyError, match="valid UTF-8 JSON"):
        _accept(tmp_path, lines)


def test_wrong_changeset_digest_fails_closed(tmp_path: Path) -> None:
    lines = _unique_index_lines()
    payload = _evidence_payload(lines)
    payload["changeset_sha256"] = "e" * 64
    _write_evidence(tmp_path, payload)

    with pytest.raises(DBMigrationSafetyError, match="changeset digest does not match"):
        _accept(tmp_path, lines)


def test_wrong_base_sha_fails_closed(tmp_path: Path) -> None:
    lines = _unique_index_lines()
    payload = _evidence_payload(lines)
    payload["base_sha"] = "f" * 40
    _write_evidence(tmp_path, payload)

    with pytest.raises(DBMigrationSafetyError, match="base SHA does not match"):
        _accept(tmp_path, lines)


def test_wrong_changeset_authors_fail_closed(tmp_path: Path) -> None:
    lines = _unique_index_lines()
    payload = _evidence_payload(lines)
    payload["changeset_authors"] = ["other@example.com"]
    _write_evidence(tmp_path, payload)

    with pytest.raises(DBMigrationSafetyError, match="changeset authors do not match"):
        _accept(tmp_path, lines)


def test_same_author_cannot_self_accept_review(tmp_path: Path) -> None:
    lines = _unique_index_lines()
    payload = _evidence_payload(lines)
    payload["reviewer"] = _AUTHOR
    _write_evidence(tmp_path, payload)

    with pytest.raises(DBMigrationSafetyError, match="reviewer must be independent"):
        _accept(tmp_path, lines)


def test_wrong_finding_fingerprint_fails_closed(tmp_path: Path) -> None:
    lines = _unique_index_lines()
    payload = _evidence_payload(lines)
    payload["finding_fingerprints"] = ["1" * 64]
    _write_evidence(tmp_path, payload)

    with pytest.raises(DBMigrationSafetyError, match="finding fingerprints do not match"):
        _accept(tmp_path, lines)


def test_exact_independent_git_provenance_is_accepted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    lines = _unique_index_lines()
    evidence_path = _write_evidence(tmp_path, _evidence_payload(lines))
    raw = evidence_path.read_text(encoding="utf-8")

    def fake_git_success(root: Path, arguments: Any) -> bool:
        del root, arguments
        return True

    def fake_git_text(
        root: Path,
        arguments: Any,
        failure: str,
        *,
        strip: bool = True,
    ) -> str:
        del root, failure
        args = tuple(arguments)
        if args[:3] == ("log", "-1", "--format=%H"):
            value = _EVIDENCE_COMMIT_SHA
        elif args[:3] == ("show", "-s", "--format=%ae"):
            value = _REVIEWER
        elif args[:4] == ("diff-tree", "--no-commit-id", "--name-only", "-r"):
            value = f"docs/governance/sf20-reviews/{_CHANGESET_SHA256}.json"
        elif args[0] == "show" and ":docs/governance/sf20-reviews/" in args[1]:
            value = raw
        else:
            raise AssertionError(f"unexpected git command: {args}")
        return value.strip() if strip else value

    monkeypatch.setattr(admission_module, "_git_success", fake_git_success)
    monkeypatch.setattr(admission_module, "_git_text", fake_git_text)

    acceptance = _accept(tmp_path, lines)

    assert acceptance.accepted is True
    assert acceptance.reviewer == _REVIEWER
    assert acceptance.evidence_commit_sha == _EVIDENCE_COMMIT_SHA
    assert acceptance.evidence_sha256 is not None
    assert len(acceptance.finding_fingerprints) == 1


def test_evidence_commit_author_must_match_reviewer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    lines = _unique_index_lines()
    _write_evidence(tmp_path, _evidence_payload(lines))

    monkeypatch.setattr(admission_module, "_git_success", lambda *_args, **_kwargs: True)

    def fake_git_text(
        root: Path,
        arguments: Any,
        failure: str,
        *,
        strip: bool = True,
    ) -> str:
        del root, failure, strip
        args = tuple(arguments)
        if args[:3] == ("log", "-1", "--format=%H"):
            return _EVIDENCE_COMMIT_SHA
        if args[:3] == ("show", "-s", "--format=%ae"):
            return "different-reviewer@example.com"
        raise AssertionError(f"unexpected git command: {args}")

    monkeypatch.setattr(admission_module, "_git_text", fake_git_text)

    with pytest.raises(
        DBMigrationSafetyError,
        match="reviewer does not match evidence commit author",
    ):
        _accept(tmp_path, lines)


def test_full_migration_diff_digest_binds_deletions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    diff = "diff --git a/db/migrations/x.sql b/db/migrations/x.sql\n-old\n+new\n"
    monkeypatch.setattr(admission_module, "_git_diff", lambda *_args, **_kwargs: diff)

    digest = _migration_changeset_sha256(
        tmp_path,
        migration_files=("db/migrations/x.sql",),
        base_sha=_BASE_SHA,
        head_sha=_HEAD_SHA,
        staged=False,
    )

    import hashlib

    assert digest == hashlib.sha256(diff.encode("utf-8")).hexdigest()


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
    _write_evidence(tmp_path, _evidence_payload(lines))

    acceptance = _review_acceptance(
        tmp_path,
        report=_review_report(lines),
        selected=lines,
        changeset_sha256=_CHANGESET_SHA256,
        subject_head_sha=_HEAD_SHA,
        expected_base_sha=_BASE_SHA,
        changeset_authors=(_AUTHOR,),
    )

    assert acceptance.accepted is False
