"""SF-20 deterministic database-migration safety for the Software Factory.

The gate is read-only. It classifies migration changes from exact reviewed or
staged diffs, blocks clearly destructive operations, requires independent review
for compatibility/locking/data-rewrite risks, and continuously verifies the
existing control-plane SQLite migration/rollback contract. It never executes a
migration and grants no acceptance, promotion, deployment, production, or
repository-mutation authority.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import subprocess
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Iterable, Sequence

from services.software_factory_secret_scanning import (
    ChangedLine,
    SoftwareFactorySecretScanning,
)

DB_MIGRATION_SAFETY_CONTRACT_VERSION = "1.0.0"
_CONTROL_PLANE_MIGRATIONS = "services/control_plane/migrations.py"
_SHA1 = re.compile(r"^[0-9a-f]{40}$")
_MIGRATION_SUFFIXES = frozenset({".sql", ".ddl", ".psql", ".py"})


class MigrationDisposition(str, Enum):
    PASS = "PASS"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    BLOCK = "BLOCK"


@dataclass(frozen=True, slots=True)
class MigrationSafetyFinding:
    finding_id: str
    disposition: MigrationDisposition
    path: str
    line: int
    reason: str
    remediation: str
    backup_required: bool
    rollback_or_compensation_required: bool
    fingerprint: str


@dataclass(frozen=True, slots=True)
class DBMigrationSafetyReport:
    contract_version: str
    scope: str
    base_sha: str | None
    head_sha: str | None
    migration_files: tuple[str, ...]
    scanned_added_lines: int
    findings: tuple[MigrationSafetyFinding, ...]
    disposition: MigrationDisposition
    passed: bool
    independent_review_required: bool
    migration_execution_authorized: bool
    acceptance_authorized: bool
    promotion_authorized: bool
    deployment_authorized: bool
    production_applied: bool
    subject_mutated: bool
    report_sha256: str


@dataclass(frozen=True, slots=True)
class _Rule:
    finding_id: str
    pattern: re.Pattern[str]
    disposition: MigrationDisposition
    reason: str
    remediation: str
    backup_required: bool
    rollback_required: bool


@dataclass(frozen=True, slots=True)
class _Chunk:
    path: str
    lines: tuple[ChangedLine, ...]
    text: str


_RULES: tuple[_Rule, ...] = (
    _Rule(
        "SF20-DROP-DATABASE-SCHEMA",
        re.compile(r"\bDROP\s+(?:DATABASE|SCHEMA)\b", re.IGNORECASE),
        MigrationDisposition.BLOCK,
        "database/schema destruction is outside autonomous migration authority",
        "use an explicitly governed decommission workflow with independent approval",
        True,
        True,
    ),
    _Rule(
        "SF20-TRUNCATE",
        re.compile(r"\bTRUNCATE\s+(?:TABLE\s+)?", re.IGNORECASE),
        MigrationDisposition.BLOCK,
        "unbounded table truncation can irreversibly remove data",
        "replace with a bounded data migration and independently reviewed recovery plan",
        True,
        True,
    ),
    _Rule(
        "SF20-FOREIGN-KEYS-OFF",
        re.compile(r"\bPRAGMA\s+foreign_keys\s*=\s*(?:OFF|0)\b", re.IGNORECASE),
        MigrationDisposition.BLOCK,
        "disabling referential-integrity enforcement is prohibited",
        "keep foreign-key enforcement enabled and redesign the migration ordering",
        True,
        True,
    ),
    _Rule(
        "SF20-DROP-TABLE-COLUMN",
        re.compile(r"\bDROP\s+(?:TABLE|COLUMN)\b", re.IGNORECASE),
        MigrationDisposition.REVIEW_REQUIRED,
        "destructive schema removal has compatibility and data-loss risk",
        "require independent review, verified backup, and rollback/compensation evidence",
        True,
        True,
    ),
    _Rule(
        "SF20-DROP-INDEX",
        re.compile(r"\bDROP\s+INDEX\b", re.IGNORECASE),
        MigrationDisposition.REVIEW_REQUIRED,
        "index removal may change query safety and production performance",
        "require independent review and a measured rollback plan",
        False,
        True,
    ),
    _Rule(
        "SF20-ALTER-RENAME-TYPE",
        re.compile(
            r"\bALTER\s+(?:TABLE|COLUMN|TYPE)\b[\s\S]*?\b(?:RENAME|TYPE|ALTER|DROP)\b",
            re.IGNORECASE,
        ),
        MigrationDisposition.REVIEW_REQUIRED,
        "schema rewrite may break backward/forward compatibility",
        "use expand/migrate/contract sequencing with independent compatibility review",
        True,
        True,
    ),
    _Rule(
        "SF20-SET-NOT-NULL",
        re.compile(r"\bSET\s+NOT\s+NULL\b", re.IGNORECASE),
        MigrationDisposition.REVIEW_REQUIRED,
        "tightening nullability can fail on existing rows or mixed-version writers",
        "backfill and validate first, then enforce in a separately reviewed contract step",
        True,
        True,
    ),
    _Rule(
        "SF20-ADD-NOT-NULL",
        re.compile(
            r"\bADD\s+(?:COLUMN\s+)?[A-Za-z_][A-Za-z0-9_]*[\s\S]*?\bNOT\s+NULL\b",
            re.IGNORECASE,
        ),
        MigrationDisposition.REVIEW_REQUIRED,
        "non-null column introduction may require a table rewrite or break old writers",
        "prefer nullable expand step, bounded backfill, validation, then contract step",
        True,
        True,
    ),
    _Rule(
        "SF20-CREATE-UNIQUE-INDEX",
        re.compile(r"\bCREATE\s+UNIQUE\s+INDEX\b", re.IGNORECASE),
        MigrationDisposition.REVIEW_REQUIRED,
        "new uniqueness enforcement can fail on existing data and may lock writes",
        "pre-validate duplicates and use a database-specific low-lock deployment plan",
        True,
        True,
    ),
    _Rule(
        "SF20-CREATE-INDEX-LOCK",
        re.compile(r"\bCREATE\s+(?!UNIQUE\s+)INDEX\b", re.IGNORECASE),
        MigrationDisposition.REVIEW_REQUIRED,
        "index creation can lock or materially load a production database",
        "use a database-specific online/concurrent strategy and review resource impact",
        False,
        True,
    ),
    _Rule(
        "SF20-DATA-REWRITE",
        re.compile(r"\b(?:UPDATE|INSERT\s+INTO[\s\S]+?SELECT)\b", re.IGNORECASE),
        MigrationDisposition.REVIEW_REQUIRED,
        "data rewrite/backfill requires bounded execution and compensation evidence",
        "make the rewrite resumable, bounded, observable, and independently reviewed",
        True,
        True,
    ),
)

_DELETE = re.compile(r"\bDELETE\s+FROM\b(?P<body>[\s\S]*?)(?:;|$)", re.IGNORECASE)
_UPDATE = re.compile(r"\bUPDATE\b(?P<body>[\s\S]*?)(?:;|$)", re.IGNORECASE)


class DBMigrationSafetyError(RuntimeError):
    """SF-20 execution failed closed."""


class SoftwareFactoryDBMigrationSafety:
    """Fail-closed admission gate for database migration changes."""

    def scan_lines(
        self,
        lines: Sequence[ChangedLine],
        *,
        scope: str,
        repository_root: Path | None = None,
        base_sha: str | None = None,
        head_sha: str | None = None,
    ) -> DBMigrationSafetyReport:
        if not scope.strip():
            raise DBMigrationSafetyError("database migration safety scope is required")
        migration_lines = tuple(line for line in lines if _is_migration_path(line.path))
        findings: list[MigrationSafetyFinding] = []
        for chunk in _chunks(migration_lines):
            findings.extend(self._scan_chunk(chunk))

        migration_files = tuple(sorted({line.path for line in migration_lines}))
        if repository_root is not None and _CONTROL_PLANE_MIGRATIONS in migration_files:
            findings.extend(self._audit_control_plane_contract(repository_root))

        normalized = tuple(
            sorted(
                _deduplicate(findings),
                key=lambda item: (
                    item.path,
                    item.line,
                    item.finding_id,
                    item.fingerprint,
                ),
            )
        )
        disposition = _overall_disposition(normalized)
        independent_review_required = any(
            item.disposition is MigrationDisposition.REVIEW_REQUIRED for item in normalized
        )
        passed = disposition is MigrationDisposition.PASS
        material = {
            "contract_version": DB_MIGRATION_SAFETY_CONTRACT_VERSION,
            "scope": scope,
            "base_sha": base_sha,
            "head_sha": head_sha,
            "migration_files": list(migration_files),
            "scanned_added_lines": len(migration_lines),
            "findings": [
                {
                    "finding_id": item.finding_id,
                    "disposition": item.disposition.value,
                    "path": item.path,
                    "line": item.line,
                    "reason": item.reason,
                    "remediation": item.remediation,
                    "backup_required": item.backup_required,
                    "rollback_or_compensation_required": item.rollback_or_compensation_required,
                    "fingerprint": item.fingerprint,
                }
                for item in normalized
            ],
            "disposition": disposition.value,
            "passed": passed,
            "independent_review_required": independent_review_required,
            "authority": {
                "migration_execution": False,
                "acceptance": False,
                "promotion": False,
                "deployment": False,
                "production": False,
                "mutation": False,
            },
        }
        return DBMigrationSafetyReport(
            contract_version=DB_MIGRATION_SAFETY_CONTRACT_VERSION,
            scope=scope,
            base_sha=base_sha,
            head_sha=head_sha,
            migration_files=migration_files,
            scanned_added_lines=len(migration_lines),
            findings=normalized,
            disposition=disposition,
            passed=passed,
            independent_review_required=independent_review_required,
            migration_execution_authorized=False,
            acceptance_authorized=False,
            promotion_authorized=False,
            deployment_authorized=False,
            production_applied=False,
            subject_mutated=False,
            report_sha256=_canonical_sha256(material),
        )

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
        return self.scan_lines(
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
        return self.scan_lines(
            SoftwareFactorySecretScanning.parse_added_lines(diff),
            scope="STAGED_CHANGESET",
            repository_root=repository_root,
        )

    def _scan_chunk(self, chunk: _Chunk) -> tuple[MigrationSafetyFinding, ...]:
        findings: list[MigrationSafetyFinding] = []
        for rule in _RULES:
            for match in rule.pattern.finditer(chunk.text):
                findings.append(self._finding(rule, chunk, match.start()))

        for pattern, finding_id, reason in (
            (
                _DELETE,
                "SF20-UNBOUNDED-DELETE",
                "DELETE without a WHERE predicate can remove an unbounded dataset",
            ),
            (
                _UPDATE,
                "SF20-UNBOUNDED-UPDATE",
                "UPDATE without a WHERE predicate can rewrite an unbounded dataset",
            ),
        ):
            for match in pattern.finditer(chunk.text):
                body = match.group("body")
                if re.search(r"\bWHERE\b", body, re.IGNORECASE) is not None:
                    continue
                rule = _Rule(
                    finding_id,
                    pattern,
                    MigrationDisposition.BLOCK,
                    reason,
                    "add a bounded predicate and independent data-migration review",
                    True,
                    True,
                )
                findings.append(self._finding(rule, chunk, match.start()))
        return tuple(findings)

    @staticmethod
    def _finding(rule: _Rule, chunk: _Chunk, offset: int) -> MigrationSafetyFinding:
        index = chunk.text[:offset].count("\n")
        line = chunk.lines[min(index, len(chunk.lines) - 1)]
        fingerprint = hashlib.sha256(
            f"{rule.finding_id}\0{line.path}\0{line.line}\0{rule.reason}".encode(
                "utf-8"
            )
        ).hexdigest()
        return MigrationSafetyFinding(
            finding_id=rule.finding_id,
            disposition=rule.disposition,
            path=line.path,
            line=line.line,
            reason=rule.reason,
            remediation=rule.remediation,
            backup_required=rule.backup_required,
            rollback_or_compensation_required=rule.rollback_required,
            fingerprint=fingerprint,
        )

    @staticmethod
    def _audit_control_plane_contract(
        repository_root: Path,
    ) -> tuple[MigrationSafetyFinding, ...]:
        path = repository_root.resolve() / _CONTROL_PLANE_MIGRATIONS
        if not path.is_file():
            raise DBMigrationSafetyError("control-plane migration authority is missing")
        text = path.read_text(encoding="utf-8")
        try:
            tree = ast.parse(text, filename=_CONTROL_PLANE_MIGRATIONS)
        except SyntaxError as error:
            raise DBMigrationSafetyError("control-plane migration authority is invalid") from error

        latest: int | None = None
        up_keys: set[int] | None = None
        down_keys: set[int] | None = None
        for node in tree.body:
            if not isinstance(node, ast.Assign) or len(node.targets) != 1:
                continue
            target = node.targets[0]
            if not isinstance(target, ast.Name):
                continue
            if target.id == "LATEST_SCHEMA_VERSION":
                if isinstance(node.value, ast.Constant) and isinstance(node.value.value, int):
                    latest = node.value.value
            elif target.id == "_UP_MIGRATIONS":
                up_keys = _literal_int_dict_keys(node.value)
            elif target.id == "_DOWN_MIGRATIONS":
                down_keys = _literal_int_dict_keys(node.value)

        failures: list[str] = []
        if latest is None or latest < 1:
            failures.append("LATEST_SCHEMA_VERSION must be a positive integer")
        if up_keys is None or down_keys is None:
            failures.append("up/down migration dictionaries must be statically defined")
        elif latest is not None:
            expected = set(range(1, latest + 1))
            if up_keys != expected:
                failures.append("up migration versions must be contiguous through latest")
            if down_keys != expected:
                failures.append("down migration versions must pair every up migration")
        required_recovery_fragments = (
            "if backup_path.exists():",
            "shutil.copy2(database_path, backup_path)",
            "connection.executescript(_DOWN_MIGRATIONS[current])",
            "except Exception:",
            "shutil.copy2(backup_path, database_path)",
        )
        if any(fragment not in text for fragment in required_recovery_fragments):
            failures.append("rollback must preserve backup-before-change and restore-on-failure")
        if 'connection.execute("PRAGMA foreign_keys = ON")' not in text:
            failures.append("control-plane migration connections must enforce foreign keys")

        findings: list[MigrationSafetyFinding] = []
        for index, reason in enumerate(failures, start=1):
            fingerprint = hashlib.sha256(
                f"SF20-CONTROL-PLANE-CONTRACT\0{index}\0{reason}".encode("utf-8")
            ).hexdigest()
            findings.append(
                MigrationSafetyFinding(
                    finding_id="SF20-CONTROL-PLANE-CONTRACT",
                    disposition=MigrationDisposition.BLOCK,
                    path=_CONTROL_PLANE_MIGRATIONS,
                    line=1,
                    reason=reason,
                    remediation="restore version pairing, FK enforcement, and recoverable rollback invariants",
                    backup_required=True,
                    rollback_or_compensation_required=True,
                    fingerprint=fingerprint,
                )
            )
        return tuple(findings)


def _is_migration_path(path: str) -> bool:
    normalized = path.replace("\\", "/").casefold()
    candidate = Path(normalized)
    if candidate.suffix == ".sql":
        return True
    if candidate.suffix not in _MIGRATION_SUFFIXES:
        return False
    return (
        "/migrations/" in f"/{normalized}"
        or "migration" in candidate.name
        or normalized == _CONTROL_PLANE_MIGRATIONS
    )


def _chunks(lines: Sequence[ChangedLine]) -> tuple[_Chunk, ...]:
    ordered = sorted(lines, key=lambda item: (item.path, item.line))
    chunks: list[_Chunk] = []
    active: list[ChangedLine] = []
    for line in ordered:
        if active and (line.path != active[-1].path or line.line != active[-1].line + 1):
            chunks.append(_make_chunk(active))
            active = []
        active.append(line)
    if active:
        chunks.append(_make_chunk(active))
    return tuple(chunks)


def _make_chunk(lines: Sequence[ChangedLine]) -> _Chunk:
    if not lines:
        raise DBMigrationSafetyError("migration chunk cannot be empty")
    return _Chunk(
        path=lines[0].path,
        lines=tuple(lines),
        text="\n".join(line.text for line in lines),
    )


def _deduplicate(
    findings: Iterable[MigrationSafetyFinding],
) -> tuple[MigrationSafetyFinding, ...]:
    by_key: dict[tuple[str, str, int], MigrationSafetyFinding] = {}
    for item in findings:
        key = (item.finding_id, item.path, item.line)
        existing = by_key.get(key)
        if existing is None or _rank(item.disposition) > _rank(existing.disposition):
            by_key[key] = item
    return tuple(by_key.values())


def _overall_disposition(
    findings: Sequence[MigrationSafetyFinding],
) -> MigrationDisposition:
    if any(item.disposition is MigrationDisposition.BLOCK for item in findings):
        return MigrationDisposition.BLOCK
    if any(
        item.disposition is MigrationDisposition.REVIEW_REQUIRED for item in findings
    ):
        return MigrationDisposition.REVIEW_REQUIRED
    return MigrationDisposition.PASS


def _rank(disposition: MigrationDisposition) -> int:
    return {
        MigrationDisposition.PASS: 0,
        MigrationDisposition.REVIEW_REQUIRED: 1,
        MigrationDisposition.BLOCK: 2,
    }[disposition]


def _literal_int_dict_keys(node: ast.expr) -> set[int] | None:
    if not isinstance(node, ast.Dict):
        return None
    keys: set[int] = set()
    for key in node.keys:
        if not isinstance(key, ast.Constant) or not isinstance(key.value, int):
            return None
        keys.add(key.value)
    return keys


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


def _canonical_sha256(value: object) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Enforce SF-20 DB migration safety")
    parser.add_argument("--repository-root", type=Path, default=Path("."))
    parser.add_argument("--base-sha")
    parser.add_argument("--head-sha")
    parser.add_argument("--staged", action="store_true")
    args = parser.parse_args(argv)

    gate = SoftwareFactoryDBMigrationSafety()
    if args.staged:
        if args.base_sha is not None or args.head_sha is not None:
            parser.error("--staged cannot be combined with --base-sha/--head-sha")
        report = gate.scan_staged(args.repository_root)
    else:
        if args.base_sha is None or args.head_sha is None:
            parser.error("reviewed changeset scan requires --base-sha and --head-sha")
        report = gate.scan_diff(
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
