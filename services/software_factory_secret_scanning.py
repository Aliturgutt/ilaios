"""SF-19 fail-closed secret scanning for Software Factory changesets.

The gate is read-only and scopes evidence to reviewed/staged added lines. It
reuses the existing Security Factory secret detectors, adds bounded
Software-Factory-specific provider credential detectors, never prints detected
secret values, and grants no acceptance, promotion, deployment, production, or
repository-mutation authority.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import subprocess
from collections import Counter
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Sequence

from services.security_factory import SecurityFactory

SECRET_SCANNING_CONTRACT_VERSION = "1.0.0"
_SHA1 = re.compile(r"^[0-9a-f]{40}$")
_HUNK = re.compile(r"@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")
_PROVIDER_RULES: tuple[tuple[str, re.Pattern[str], str, str], ...] = (
    (
        "SF19-GITHUB-TOKEN",
        re.compile(r"\bgh(?:p|o|u|s|r)_[A-Za-z0-9]{36,255}\b"),
        "GitHub credential-like material detected",
        "revoke/rotate the token and store credentials outside Git",
    ),
    (
        "SF19-GITHUB-FINE-GRAINED-TOKEN",
        re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,255}\b"),
        "GitHub fine-grained credential-like material detected",
        "revoke/rotate the token and store credentials outside Git",
    ),
    (
        "SF19-OPENAI-KEY",
        re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b"),
        "provider API credential-like material detected",
        "revoke/rotate the key and store credentials outside Git",
    ),
    (
        "SF19-GOOGLE-API-KEY",
        re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"),
        "Google API credential-like material detected",
        "revoke/rotate the key and store credentials outside Git",
    ),
    (
        "SF19-SLACK-TOKEN",
        re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"),
        "Slack credential-like material detected",
        "revoke/rotate the token and store credentials outside Git",
    ),
    (
        "SF19-STRIPE-LIVE-KEY",
        re.compile(r"\bsk_live_[A-Za-z0-9]{16,}\b"),
        "live payment credential-like material detected",
        "revoke/rotate the key and store credentials outside Git",
    ),
)
_GENERIC_ASSIGNMENT = re.compile(
    r"(?i)\b(?:api[_-]?key|access[_-]?token|auth[_-]?token|client[_-]?secret|"
    r"password|passwd|secret|token)\b\s*[:=]\s*[\"']([^\"']{20,})[\"']"
)
_PLACEHOLDER_MARKERS = (
    "example",
    "placeholder",
    "redacted",
    "changeme",
    "dummy",
    "not-a-secret",
    "not_a_secret",
)


class SecretScanningError(RuntimeError):
    """SF-19 execution failed closed."""


class SecretScanSeverity(str, Enum):
    BLOCK = "BLOCK"


@dataclass(frozen=True, slots=True)
class ChangedLine:
    path: str
    line: int
    text: str


@dataclass(frozen=True, slots=True)
class SecretScanFinding:
    finding_id: str
    severity: SecretScanSeverity
    path: str
    line: int
    detector: str
    reason: str
    remediation: str
    fingerprint: str


@dataclass(frozen=True, slots=True)
class SecretScanReport:
    contract_version: str
    scope: str
    base_sha: str | None
    head_sha: str | None
    scanned_added_lines: int
    findings: tuple[SecretScanFinding, ...]
    passed: bool
    secret_values_emitted: bool
    acceptance_authorized: bool
    promotion_authorized: bool
    deployment_authorized: bool
    production_applied: bool
    subject_mutated: bool
    report_sha256: str


class SoftwareFactorySecretScanning:
    """Deterministic secret gate over exact reviewed changeset content."""

    def __init__(self, security_factory: SecurityFactory | None = None) -> None:
        self._security_factory = security_factory or SecurityFactory()

    def scan_lines(
        self,
        lines: Sequence[ChangedLine],
        *,
        scope: str,
        base_sha: str | None = None,
        head_sha: str | None = None,
    ) -> SecretScanReport:
        if not scope.strip():
            raise SecretScanningError("secret scanning scope is required")
        findings: list[SecretScanFinding] = []
        for changed in lines:
            if changed.line < 1 or not changed.path.strip():
                raise SecretScanningError("changed-line evidence is malformed")
            findings.extend(self._scan_line(changed))

        normalized = tuple(
            sorted(
                self._deduplicate(findings),
                key=lambda item: (
                    item.path,
                    item.line,
                    item.finding_id,
                    item.fingerprint,
                ),
            )
        )
        material = {
            "contract_version": SECRET_SCANNING_CONTRACT_VERSION,
            "scope": scope,
            "base_sha": base_sha,
            "head_sha": head_sha,
            "scanned_added_lines": len(lines),
            "findings": [
                {
                    "finding_id": item.finding_id,
                    "severity": item.severity.value,
                    "path": item.path,
                    "line": item.line,
                    "detector": item.detector,
                    "reason": item.reason,
                    "remediation": item.remediation,
                    "fingerprint": item.fingerprint,
                }
                for item in normalized
            ],
            "passed": not normalized,
            "secret_values_emitted": False,
            "authority": {
                "acceptance": False,
                "promotion": False,
                "deployment": False,
                "production": False,
                "mutation": False,
            },
        }
        return SecretScanReport(
            contract_version=SECRET_SCANNING_CONTRACT_VERSION,
            scope=scope,
            base_sha=base_sha,
            head_sha=head_sha,
            scanned_added_lines=len(lines),
            findings=normalized,
            passed=not normalized,
            secret_values_emitted=False,
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
    ) -> SecretScanReport:
        self._require_sha(base_sha, "base SHA")
        self._require_sha(head_sha, "head SHA")
        diff = self._git_diff(
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
            self.parse_added_lines(diff),
            scope="REVIEWED_CHANGESET",
            base_sha=base_sha,
            head_sha=head_sha,
        )

    def scan_staged(self, repository_root: Path) -> SecretScanReport:
        diff = self._git_diff(
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
            self.parse_added_lines(diff),
            scope="STAGED_CHANGESET",
        )

    @staticmethod
    def parse_added_lines(diff: str) -> tuple[ChangedLine, ...]:
        current_path: str | None = None
        next_line: int | None = None
        added: list[ChangedLine] = []
        for raw in diff.splitlines():
            if raw.startswith("+++ "):
                value = raw[4:].strip()
                if value == "/dev/null":
                    current_path = None
                elif value.startswith("b/"):
                    current_path = value[2:]
                else:
                    current_path = value
                continue
            if raw.startswith("@@ "):
                match = _HUNK.search(raw)
                next_line = int(match.group(1)) if match else None
                continue
            if next_line is None:
                continue
            if raw.startswith("+") and not raw.startswith("+++"):
                if current_path is not None:
                    added.append(ChangedLine(current_path, next_line, raw[1:]))
                next_line += 1
            elif raw.startswith(" "):
                next_line += 1
            elif raw.startswith("-"):
                continue
        return tuple(added)

    def _scan_line(self, changed: ChangedLine) -> tuple[SecretScanFinding, ...]:
        findings: list[SecretScanFinding] = []
        suffix = Path(changed.path).suffix.casefold()
        upstream = self._security_factory._scan_text(  # noqa: SLF001
            changed.path,
            changed.text,
            suffix,
        )
        for item in upstream:
            if item.category != "secret":
                continue
            findings.append(
                self._finding(
                    item.finding_id,
                    changed,
                    "security-factory",
                    item.message,
                    item.remediation,
                )
            )

        for finding_id, pattern, reason, remediation in _PROVIDER_RULES:
            if pattern.search(changed.text):
                findings.append(
                    self._finding(
                        finding_id,
                        changed,
                        "software-factory-provider-policy",
                        reason,
                        remediation,
                    )
                )

        generic = _GENERIC_ASSIGNMENT.search(changed.text)
        if generic is not None:
            candidate = generic.group(1).strip()
            if self._generic_candidate_is_secret(candidate):
                findings.append(
                    self._finding(
                        "SF19-GENERIC-CREDENTIAL-ASSIGNMENT",
                        changed,
                        "software-factory-generic-policy",
                        "high-entropy credential assignment detected",
                        "remove the credential from Git and use an authorized secret store",
                    )
                )
        return tuple(findings)

    @staticmethod
    def _generic_candidate_is_secret(candidate: str) -> bool:
        lowered = candidate.casefold()
        if any(marker in lowered for marker in _PLACEHOLDER_MARKERS):
            return False
        if len(candidate) < 20:
            return False
        return _shannon_entropy(candidate) >= 3.5

    @staticmethod
    def _deduplicate(
        findings: Sequence[SecretScanFinding],
    ) -> tuple[SecretScanFinding, ...]:
        unique: dict[tuple[str, str, int], SecretScanFinding] = {}
        for item in findings:
            key = (item.finding_id, item.path, item.line)
            unique.setdefault(key, item)
        return tuple(unique.values())

    @staticmethod
    def _finding(
        finding_id: str,
        changed: ChangedLine,
        detector: str,
        reason: str,
        remediation: str,
    ) -> SecretScanFinding:
        fingerprint_material = (
            f"{finding_id}:{changed.path}:{changed.line}:{len(changed.text)}"
        ).encode("utf-8")
        return SecretScanFinding(
            finding_id=finding_id,
            severity=SecretScanSeverity.BLOCK,
            path=changed.path,
            line=changed.line,
            detector=detector,
            reason=reason,
            remediation=remediation,
            fingerprint=hashlib.sha256(fingerprint_material).hexdigest(),
        )

    @staticmethod
    def _require_sha(value: str, label: str) -> None:
        if _SHA1.fullmatch(value) is None:
            raise SecretScanningError(f"{label} must be an exact 40-hex commit SHA")

    @staticmethod
    def _git_diff(repository_root: Path, arguments: Sequence[str]) -> str:
        root = repository_root.resolve()
        if not root.is_dir():
            raise SecretScanningError("repository root must exist")
        completed = subprocess.run(
            ("git", *arguments),
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if completed.returncode != 0:
            raise SecretScanningError("git diff evidence collection failed")
        return completed.stdout


def _shannon_entropy(value: str) -> float:
    if not value:
        return 0.0
    counts = Counter(value)
    length = len(value)
    return -sum(
        (count / length) * math.log2(count / length) for count in counts.values()
    )


def _canonical_sha256(value: object) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _print_report(report: SecretScanReport) -> int:
    print(f"SF-19 secret scanning report: {report.report_sha256}")
    if report.passed:
        print(
            "SF-19 secret scanning PASS "
            f"scope={report.scope} lines={report.scanned_added_lines}"
        )
        return 0
    for finding in report.findings:
        print(
            f"{finding.severity.value} {finding.finding_id} "
            f"{finding.path}:{finding.line} {finding.reason} "
            f"fingerprint={finding.fingerprint}"
        )
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run SF-19 secret scanning")
    parser.add_argument("--repository-root", default=".")
    parser.add_argument("--base-sha")
    parser.add_argument("--head-sha")
    parser.add_argument("--staged", action="store_true")
    args = parser.parse_args(argv)

    scanner = SoftwareFactorySecretScanning()
    try:
        if args.staged:
            if args.base_sha or args.head_sha:
                raise SecretScanningError(
                    "--staged cannot be combined with --base-sha/--head-sha"
                )
            report = scanner.scan_staged(Path(args.repository_root))
        else:
            if not args.base_sha or not args.head_sha:
                raise SecretScanningError(
                    "exact --base-sha and --head-sha are required outside staged mode"
                )
            report = scanner.scan_diff(
                Path(args.repository_root),
                base_sha=args.base_sha,
                head_sha=args.head_sha,
            )
    except SecretScanningError as exc:
        print(f"SF-19 secret scanning BLOCK: {exc}")
        return 2
    return _print_report(report)


if __name__ == "__main__":
    raise SystemExit(main())
