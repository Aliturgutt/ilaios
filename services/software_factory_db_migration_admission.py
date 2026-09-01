"""SF-20 exact-changeset admission selector for database migration safety.

This bootstrap-safe wrapper limits the migration safety engine to actual
migration artifacts. It prevents documentation, tests, and the SF-20 engine
itself from becoming scan subjects merely because their filenames contain the
word "migration".
"""

from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path
from typing import Sequence

from services.software_factory_db_migration_safety import (
    DBMigrationSafetyError,
    DBMigrationSafetyReport,
    SoftwareFactoryDBMigrationSafety,
)
from services.software_factory_secret_scanning import (
    ChangedLine,
    SoftwareFactorySecretScanning,
)

_CONTROL_PLANE_MIGRATIONS = "services/control_plane/migrations.py"
_SHA1 = re.compile(r"^[0-9a-f]{40}$")
_SQL_SUFFIXES = frozenset({".sql", ".ddl", ".psql"})
_MIGRATION_DIRS = frozenset({"migration", "migrations", "alembic"})


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
        return self._scan_selected(
            SoftwareFactorySecretScanning.parse_added_lines(diff),
            scope="REVIEWED_CHANGESET",
            repository_root=repository_root,
            base_sha=base_sha,
            head_sha=head_sha,
        )

    def scan_staged(self, repository_root: Path) -> DBMigrationSafetyReport:
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
        return self._scan_selected(
            SoftwareFactorySecretScanning.parse_added_lines(diff),
            scope="STAGED_CHANGESET",
            repository_root=repository_root,
        )

    def _scan_selected(
        self,
        lines: Sequence[ChangedLine],
        *,
        scope: str,
        repository_root: Path,
        base_sha: str | None = None,
        head_sha: str | None = None,
    ) -> DBMigrationSafetyReport:
        selected = tuple(line for line in lines if is_real_migration_path(line.path))
        return self._gate.scan_lines(
            selected,
            scope=scope,
            repository_root=repository_root,
            base_sha=base_sha,
            head_sha=head_sha,
        )


def _require_sha(value: str, label: str) -> None:
    if _SHA1.fullmatch(value) is None:
        raise DBMigrationSafetyError(f"{label} must be an exact lowercase 40-hex SHA")


def _git_diff(repository_root: Path, arguments: Sequence[str]) -> str:
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
        raise DBMigrationSafetyError("unable to collect exact migration changeset evidence")
    return completed.stdout


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
        report = admission.scan_staged(args.repository_root)
    else:
        if args.base_sha is None or args.head_sha is None:
            parser.error("reviewed changeset scan requires --base-sha and --head-sha")
        report = admission.scan_diff(
            args.repository_root,
            base_sha=args.base_sha,
            head_sha=args.head_sha,
        )

    print(f"SF-20 DB migration safety report: {report.report_sha256}")
    print(f"SF-20 disposition: {report.disposition.value}")
    for finding in report.findings:
        print(
            f"{finding.disposition.value} {finding.finding_id} "
            f"{finding.path}:{finding.line}: {finding.reason}"
        )
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
