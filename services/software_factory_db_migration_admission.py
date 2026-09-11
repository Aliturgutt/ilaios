"""SF-20 exact-changeset admission selector for database migration safety.

This bootstrap-safe wrapper limits the migration safety engine to actual
migration artifacts. It prevents documentation, tests, and the SF-20 engine
itself from becoming scan subjects merely because their filenames contain the
word "migration".

SF-20 safety classification remains authoritative. REVIEW_REQUIRED findings can
only be admitted when an exact, independent review-evidence artifact matches the
base SHA, canonical migration changeset digest, migration files, and every
review-required finding fingerprint. BLOCK findings are never review-acceptable.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Sequence

from services.software_factory_db_migration_safety import (
    DBMigrationSafetyError,
    DBMigrationSafetyReport,
    MigrationDisposition,
    SoftwareFactoryDBMigrationSafety,
)
from services.software_factory_secret_scanning import (
    ChangedLine,
    SoftwareFactorySecretScanning,
)

_CONTROL_PLANE_MIGRATIONS = "services/control_plane/migrations.py"
_SHA1 = re.compile(r"^[0-9a-f]{40}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_SQL_SUFFIXES = frozenset({".sql", ".ddl", ".psql"})
_MIGRATION_DIRS = frozenset({"migration", "migrations", "alembic"})
_REVIEW_EVIDENCE_VERSION = 1
_REVIEW_EVIDENCE_DIR = Path("docs/governance/sf20-reviews")


@dataclass(frozen=True, slots=True)
class SF20ReviewAcceptance:
    """Auditable result of exact SF-20 independent-review evidence validation."""

    accepted: bool
    evidence_path: str | None
    evidence_sha256: str | None
    reviewer: str | None
    reviewed_at: str | None
    finding_fingerprints: tuple[str, ...]


def is_real_migration_path(path: str) -> bool:
    """Return whether a repository path is an executable migration artifact."""

    normalized = path.replace("\\", "/").casefold().strip("/")
    if normalized == _CONTROL_PLANE_MIGRATIONS:
        return True
    candidate = Path(normalized)
    if candidate.suffix in _SQL_SUFFIXES:
        return True
    parents = candidate.parts[:-1]
    return any(part in _MIGRATION_DIRS for part in parents)


class SoftwareFactoryDBMigrationAdmission:
    """Collect exact diff evidence and invoke the canonical SF-20 safety engine."""

    def __init__(self, gate: SoftwareFactoryDBMigrationSafety | None = None) -> None:
        self._gate = gate or SoftwareFactoryDBMigrationSafety()

    def scan_diff(
        self,
        repository_root: Path,
        *,
        base_sha: str,
        head_sha: str,
    ) -> DBMigrationSafetyReport:
        report, _ = self.admit_diff(
            repository_root,
            base_sha=base_sha,
            head_sha=head_sha,
        )
        return report

    def admit_diff(
        self,
        repository_root: Path,
        *,
        base_sha: str,
        head_sha: str,
    ) -> tuple[DBMigrationSafetyReport, SF20ReviewAcceptance]:
        _require_sha(base_sha, "base SHA")
        _require_sha(head_sha, "head SHA")
        diff = _git_diff(
            repository_root,
            (
                "diff",
                "--unified=0",
                "--no-color",
                "--no-ext-diff",
                base_sha,
                head_sha,
                "--",
            ),
        )
        lines = SoftwareFactorySecretScanning.parse_added_lines(diff)
        report, selected = self._scan_selected(
            lines,
            scope="REVIEWED_CHANGESET",
            repository_root=repository_root,
            base_sha=base_sha,
            head_sha=head_sha,
        )
        change_author = _git_text(
            repository_root,
            ("show", "-s", "--format=%ae", head_sha),
            "unable to resolve reviewed changeset author",
        )
        acceptance = _review_acceptance(
            repository_root,
            report=report,
            selected=selected,
            base_sha=base_sha,
            change_author=change_author,
        )
        return report, acceptance

    def scan_staged(self, repository_root: Path) -> DBMigrationSafetyReport:
        report, _ = self.admit_staged(repository_root)
        return report

    def admit_staged(
        self,
        repository_root: Path,
    ) -> tuple[DBMigrationSafetyReport, SF20ReviewAcceptance]:
        diff = _git_diff(
            repository_root,
            (
                "diff",
                "--cached",
                "--unified=0",
                "--no-color",
                "--no-ext-diff",
                "--",
            ),
        )
        base_sha = _git_text(
            repository_root,
            ("rev-parse", "HEAD"),
            "unable to resolve staged changeset base SHA",
        )
        _require_sha(base_sha, "staged base SHA")
        lines = SoftwareFactorySecretScanning.parse_added_lines(diff)
        report, selected = self._scan_selected(
            lines,
            scope="STAGED_CHANGESET",
            repository_root=repository_root,
            base_sha=base_sha,
        )
        change_author = _git_text(
            repository_root,
            ("config", "user.email"),
            "unable to resolve staged changeset author",
        )
        acceptance = _review_acceptance(
            repository_root,
            report=report,
            selected=selected,
            base_sha=base_sha,
            change_author=change_author,
        )
        return report, acceptance

    def _scan_selected(
        self,
        lines: Sequence[ChangedLine],
        *,
        scope: str,
        repository_root: Path,
        base_sha: str | None = None,
        head_sha: str | None = None,
    ) -> tuple[DBMigrationSafetyReport, tuple[ChangedLine, ...]]:
        selected = tuple(line for line in lines if is_real_migration_path(line.path))
        report = self._gate.scan_lines(
            selected,
            scope=scope,
            repository_root=repository_root,
            base_sha=base_sha,
            head_sha=head_sha,
        )
        return report, selected


def _review_acceptance(
    repository_root: Path,
    *,
    report: DBMigrationSafetyReport,
    selected: Sequence[ChangedLine],
    base_sha: str,
    change_author: str,
) -> SF20ReviewAcceptance:
    review_fingerprints = tuple(
        sorted(
            finding.fingerprint
            for finding in report.findings
            if finding.disposition is MigrationDisposition.REVIEW_REQUIRED
        )
    )
    if not review_fingerprints:
        return SF20ReviewAcceptance(False, None, None, None, None, ())
    if report.disposition is MigrationDisposition.BLOCK:
        return SF20ReviewAcceptance(False, None, None, None, None, review_fingerprints)

    changeset_sha256 = _changeset_sha256(selected)
    evidence_path = (
        repository_root.resolve()
        / _REVIEW_EVIDENCE_DIR
        / f"{base_sha}-{changeset_sha256}.json"
    )
    if not evidence_path.is_file():
        return SF20ReviewAcceptance(
            False,
            str(evidence_path.relative_to(repository_root.resolve())),
            None,
            None,
            None,
            review_fingerprints,
        )

    raw = evidence_path.read_bytes()
    evidence_sha256 = hashlib.sha256(raw).hexdigest()
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise DBMigrationSafetyError("SF-20 review evidence must be valid UTF-8 JSON") from error
    if not isinstance(payload, dict):
        raise DBMigrationSafetyError("SF-20 review evidence must be a JSON object")

    _require_exact_keys(
        payload,
        {
            "schema_version",
            "decision",
            "base_sha",
            "changeset_sha256",
            "changeset_author",
            "reviewer",
            "reviewed_at",
            "migration_files",
            "finding_fingerprints",
            "review_notes",
        },
    )
    if payload["schema_version"] != _REVIEW_EVIDENCE_VERSION:
        raise DBMigrationSafetyError("unsupported SF-20 review evidence schema_version")
    if payload["decision"] != "ACCEPT":
        raise DBMigrationSafetyError("SF-20 review evidence decision must be ACCEPT")
    if payload["base_sha"] != base_sha:
        raise DBMigrationSafetyError("SF-20 review evidence base SHA does not match changeset")
    if payload["changeset_sha256"] != changeset_sha256:
        raise DBMigrationSafetyError("SF-20 review evidence changeset digest does not match")
    if _SHA256.fullmatch(str(payload["changeset_sha256"])) is None:
        raise DBMigrationSafetyError("SF-20 review evidence changeset digest is malformed")

    author = _require_nonempty_string(payload["changeset_author"], "changeset_author")
    reviewer = _require_nonempty_string(payload["reviewer"], "reviewer")
    if author.casefold() != change_author.strip().casefold():
        raise DBMigrationSafetyError("SF-20 review evidence changeset author does not match")
    if reviewer.casefold() == author.casefold():
        raise DBMigrationSafetyError("SF-20 review evidence reviewer must be independent")

    reviewed_at = _require_nonempty_string(payload["reviewed_at"], "reviewed_at")
    _require_offset_timestamp(reviewed_at)
    _require_nonempty_string(payload["review_notes"], "review_notes")

    migration_files = payload["migration_files"]
    if not isinstance(migration_files, list) or not all(
        isinstance(item, str) and item for item in migration_files
    ):
        raise DBMigrationSafetyError("SF-20 review evidence migration_files is malformed")
    if tuple(sorted(migration_files)) != tuple(sorted(report.migration_files)):
        raise DBMigrationSafetyError("SF-20 review evidence migration_files do not match")

    fingerprints = payload["finding_fingerprints"]
    if not isinstance(fingerprints, list) or not all(
        isinstance(item, str) and _SHA256.fullmatch(item) is not None for item in fingerprints
    ):
        raise DBMigrationSafetyError("SF-20 review evidence finding_fingerprints is malformed")
    if tuple(sorted(fingerprints)) != review_fingerprints:
        raise DBMigrationSafetyError("SF-20 review evidence finding fingerprints do not match")

    return SF20ReviewAcceptance(
        True,
        str(evidence_path.relative_to(repository_root.resolve())),
        evidence_sha256,
        reviewer,
        reviewed_at,
        review_fingerprints,
    )


def _changeset_sha256(lines: Sequence[ChangedLine]) -> str:
    material = [
        {"path": line.path, "line": line.line, "text": line.text}
        for line in sorted(lines, key=lambda item: (item.path, item.line, item.text))
    ]
    encoded = json.dumps(
        material,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _require_exact_keys(payload: dict[str, Any], expected: set[str]) -> None:
    if set(payload) != expected:
        raise DBMigrationSafetyError("SF-20 review evidence fields are malformed")


def _require_nonempty_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DBMigrationSafetyError(f"SF-20 review evidence {field} is required")
    return value.strip()


def _require_offset_timestamp(value: str) -> None:
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as error:
        raise DBMigrationSafetyError("SF-20 review evidence reviewed_at is malformed") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise DBMigrationSafetyError("SF-20 review evidence reviewed_at requires timezone")


def _require_sha(value: str, label: str) -> None:
    if _SHA1.fullmatch(value) is None:
        raise DBMigrationSafetyError(f"{label} must be an exact lowercase 40-hex SHA")


def _git_diff(repository_root: Path, arguments: Sequence[str]) -> str:
    return _git_text(
        repository_root,
        arguments,
        "unable to collect exact migration changeset evidence",
        strip=False,
    )


def _git_text(
    repository_root: Path,
    arguments: Sequence[str],
    failure: str,
    *,
    strip: bool = True,
) -> str:
    root = repository_root.resolve()
    if not root.is_dir():
        raise DBMigrationSafetyError("repository root must exist")
    completed = subprocess.run(
        ("git", *arguments),
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if completed.returncode != 0:
        raise DBMigrationSafetyError(failure)
    return completed.stdout.strip() if strip else completed.stdout


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run SF-20 DB migration admission")
    parser.add_argument("--repository-root", type=Path, default=Path("."))
    parser.add_argument("--base-sha")
    parser.add_argument("--head-sha")
    parser.add_argument("--staged", action="store_true")
    args = parser.parse_args(argv)

    admission = SoftwareFactoryDBMigrationAdmission()
    if args.staged:
        if args.base_sha is not None or args.head_sha is not None:
            parser.error("--staged cannot be combined with --base-sha/--head-sha")
        report, acceptance = admission.admit_staged(args.repository_root)
    else:
        if args.base_sha is None or args.head_sha is None:
            parser.error("reviewed changeset scan requires --base-sha and --head-sha")
        report, acceptance = admission.admit_diff(
            args.repository_root,
            base_sha=args.base_sha,
            head_sha=args.head_sha,
        )

    print(f"SF-20 DB migration safety report: {report.report_sha256}")
    print(f"SF-20 safety disposition: {report.disposition.value}")
    for finding in report.findings:
        print(
            f"{finding.disposition.value} {finding.finding_id} "
            f"{finding.path}:{finding.line}: {finding.reason}"
        )
    if acceptance.accepted:
        print(
            "SF-20 review acceptance: ACCEPTED "
            f"reviewer={acceptance.reviewer} "
            f"evidence={acceptance.evidence_path} "
            f"evidence_sha256={acceptance.evidence_sha256}"
        )
        return 0
    if report.disposition is MigrationDisposition.REVIEW_REQUIRED:
        print(
            "SF-20 review acceptance: REQUIRED "
            f"evidence={acceptance.evidence_path or 'not-applicable'}"
        )
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
