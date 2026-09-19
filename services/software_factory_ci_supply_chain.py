"""SF-18 CI supply-chain hardening for the governed Software Factory.

The audit is bootstrap-safe: it uses only the Python standard library so the
Required CI Gate can validate its own dependency/action surface before
third-party Python packages are installed.  It is read-only and grants no
release, promotion, deployment, production, or repository-mutation authority.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Iterable

CI_SUPPLY_CHAIN_CONTRACT_VERSION = "1.0.0"
CRITICAL_WORKFLOWS = (
    ".github/workflows/required-ci-gate.yml",
    ".github/workflows/platform-ci.yml",
    ".github/workflows/website-ci.yml",
)
PRE_COMMIT_CONFIG = ".pre-commit-config.yaml"
PLATFORM_REQUIREMENTS = ".github/requirements/platform-ci.txt"
WEBSITE_REQUIREMENTS = ".github/requirements/website-ci.txt"
_SHA = re.compile(r"^[0-9a-f]{40}$")
_USES = re.compile(r"^\s*-?\s*uses:\s*([^#\s]+)")
_REV = re.compile(r"^\s*rev:\s*([^#\s]+)")
_REQUIREMENT = re.compile(r"^[A-Za-z0-9_.-]+==[^=\s]+$")
_UNTRUSTED_RUN_INTERPOLATION = re.compile(
    r"\$\{\{\s*github\.event\.pull_request\.(?:title|body|head\.label)\s*\}\}"
)
_EXACT_CHECKOUT_REF = "github.event.pull_request.head.sha || github.sha"


class CIHardeningSeverity(str, Enum):
    BLOCK = "BLOCK"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


@dataclass(frozen=True, slots=True)
class CIHardeningFinding:
    finding_id: str
    severity: CIHardeningSeverity
    path: str
    reason: str


@dataclass(frozen=True, slots=True)
class CIHardeningReport:
    contract_version: str
    audited_paths: tuple[str, ...]
    findings: tuple[CIHardeningFinding, ...]
    passed: bool
    acceptance_authorized: bool
    promotion_authorized: bool
    deployment_authorized: bool
    production_applied: bool
    subject_mutated: bool
    report_sha256: str


class SoftwareFactoryCISupplyChainHardening:
    """Fail-closed deterministic audit of the critical CI bootstrap surface."""

    def audit(self, repository_root: Path) -> CIHardeningReport:
        root = repository_root.resolve()
        paths = CRITICAL_WORKFLOWS + (
            PRE_COMMIT_CONFIG,
            PLATFORM_REQUIREMENTS,
            WEBSITE_REQUIREMENTS,
        )
        findings: list[CIHardeningFinding] = []
        contents: dict[str, str] = {}
        for relative in paths:
            path = root / relative
            if not path.is_file():
                findings.append(
                    self._finding(
                        "SF18-MISSING-FILE",
                        relative,
                        "required CI supply-chain control file is missing",
                    )
                )
                continue
            contents[relative] = path.read_text(encoding="utf-8")

        for workflow in CRITICAL_WORKFLOWS:
            text = contents.get(workflow)
            if text is not None:
                findings.extend(self._audit_workflow(workflow, text))

        pre_commit = contents.get(PRE_COMMIT_CONFIG)
        if pre_commit is not None:
            findings.extend(self._audit_pre_commit(pre_commit))

        platform_requirements = contents.get(PLATFORM_REQUIREMENTS)
        if platform_requirements is not None:
            findings.extend(
                self._audit_requirements(PLATFORM_REQUIREMENTS, platform_requirements)
            )
        website_requirements = contents.get(WEBSITE_REQUIREMENTS)
        if website_requirements is not None:
            findings.extend(
                self._audit_requirements(WEBSITE_REQUIREMENTS, website_requirements)
            )

        required = contents.get(CRITICAL_WORKFLOWS[0], "")
        if required:
            if "supply-chain:" not in required:
                findings.append(
                    self._finding(
                        "SF18-GATE-NOT-WIRED",
                        CRITICAL_WORKFLOWS[0],
                        "Required CI Gate must contain a mandatory supply-chain job",
                    )
                )
            if "SUPPLY_CHAIN_RESULT" not in required:
                findings.append(
                    self._finding(
                        "SF18-GATE-NOT-AGGREGATED",
                        CRITICAL_WORKFLOWS[0],
                        "aggregate Required CI Gate must enforce supply-chain result",
                    )
                )

        platform = contents.get(CRITICAL_WORKFLOWS[1], "")
        if platform:
            if f"-r {PLATFORM_REQUIREMENTS}" not in platform:
                findings.append(
                    self._finding(
                        "SF18-PLATFORM-LOCK-NOT-USED",
                        CRITICAL_WORKFLOWS[1],
                        "Platform CI must install from committed pinned requirements",
                    )
                )
            if "pip install --upgrade pip" in platform:
                findings.append(
                    self._finding(
                        "SF18-FLOATING-PIP-UPGRADE",
                        CRITICAL_WORKFLOWS[1],
                        "CI bootstrap must not upgrade pip from a floating index target",
                    )
                )

        website = contents.get(CRITICAL_WORKFLOWS[2], "")
        if website:
            if "npm ci --ignore-scripts" not in website:
                findings.append(
                    self._finding(
                        "SF18-NPM-NONDETERMINISTIC",
                        CRITICAL_WORKFLOWS[2],
                        "Website CI must use lockfile-backed npm ci with lifecycle scripts disabled",
                    )
                )
            if f"-r {WEBSITE_REQUIREMENTS}" not in website:
                findings.append(
                    self._finding(
                        "SF18-WEBSITE-PYTHON-LOCK-NOT-USED",
                        CRITICAL_WORKFLOWS[2],
                        "Website native test dependency must use committed pinned requirements",
                    )
                )

        normalized = tuple(
            sorted(findings, key=lambda item: (item.path, item.finding_id, item.reason))
        )
        material = {
            "contract_version": CI_SUPPLY_CHAIN_CONTRACT_VERSION,
            "audited_paths": list(paths),
            "findings": [
                {
                    "finding_id": item.finding_id,
                    "severity": item.severity.value,
                    "path": item.path,
                    "reason": item.reason,
                }
                for item in normalized
            ],
            "passed": not normalized,
            "authority": {
                "acceptance": False,
                "promotion": False,
                "deployment": False,
                "production": False,
                "mutation": False,
            },
        }
        return CIHardeningReport(
            contract_version=CI_SUPPLY_CHAIN_CONTRACT_VERSION,
            audited_paths=paths,
            findings=normalized,
            passed=not normalized,
            acceptance_authorized=False,
            promotion_authorized=False,
            deployment_authorized=False,
            production_applied=False,
            subject_mutated=False,
            report_sha256=_canonical_sha256(material),
        )

    def _audit_workflow(
        self, relative: str, text: str
    ) -> tuple[CIHardeningFinding, ...]:
        findings: list[CIHardeningFinding] = []
        if "pull_request_target:" in text:
            findings.append(
                self._finding(
                    "SF18-PR-TARGET",
                    relative,
                    "critical validation workflow must not use pull_request_target",
                )
            )
        if "permissions:\n  contents: read" not in text:
            findings.append(
                self._finding(
                    "SF18-LEAST-PERMISSIONS",
                    relative,
                    "critical workflow must declare top-level contents: read permissions",
                )
            )
        if re.search(r"(?m)^\s+[A-Za-z-]+:\s+write\s*$", text):
            findings.append(
                self._finding(
                    "SF18-WRITE-TOKEN",
                    relative,
                    "critical validation workflow must not grant write-scoped GITHUB_TOKEN permissions",
                )
            )
        if "secrets." in text:
            findings.append(
                self._finding(
                    "SF18-PR-SECRETS",
                    relative,
                    "critical validation workflow must not consume repository secrets",
                )
            )
        if _UNTRUSTED_RUN_INTERPOLATION.search(text):
            findings.append(
                self._finding(
                    "SF18-UNTRUSTED-RUN-INTERPOLATION",
                    relative,
                    "untrusted pull-request text must not be interpolated directly into run scripts",
                )
            )
        for reference in self._external_action_references(text):
            _, separator, version = reference.partition("@")
            if not separator or _SHA.fullmatch(version) is None:
                findings.append(
                    self._finding(
                        "SF18-MUTABLE-ACTION",
                        relative,
                        f"external action must be pinned to an immutable 40-hex commit SHA: {reference}",
                    )
                )
        findings.extend(self._audit_checkout(relative, text))
        return tuple(findings)

    def _audit_checkout(
        self, relative: str, text: str
    ) -> tuple[CIHardeningFinding, ...]:
        findings: list[CIHardeningFinding] = []
        lines = text.splitlines()
        for index, line in enumerate(lines):
            if "uses: actions/checkout@" not in line:
                continue
            block = self._step_block(lines, index)
            if "persist-credentials: false" not in block:
                findings.append(
                    self._finding(
                        "SF18-CHECKOUT-CREDENTIALS",
                        relative,
                        "checkout must disable persisted repository credentials",
                    )
                )
            if _EXACT_CHECKOUT_REF not in block:
                findings.append(
                    self._finding(
                        "SF18-CHECKOUT-NONEXACT-REF",
                        relative,
                        "critical CI checkout must bind to exact PR head SHA or github.sha",
                    )
                )
        return tuple(findings)

    @staticmethod
    def _step_block(lines: list[str], uses_index: int) -> str:
        """Return only the current action step, never a later checkout step."""

        uses_line = lines[uses_index]
        uses_indent = len(uses_line) - len(uses_line.lstrip())
        block = [uses_line]
        for candidate in lines[uses_index + 1 :]:
            stripped = candidate.strip()
            if not stripped:
                block.append(candidate)
                continue
            indent = len(candidate) - len(candidate.lstrip())
            if indent < uses_indent and (
                stripped.startswith("- ") or stripped.endswith(":")
            ):
                break
            block.append(candidate)
        return "\n".join(block)

    def _audit_pre_commit(self, text: str) -> tuple[CIHardeningFinding, ...]:
        findings: list[CIHardeningFinding] = []
        for line in text.splitlines():
            match = _REV.match(line)
            if match and _SHA.fullmatch(match.group(1)) is None:
                findings.append(
                    self._finding(
                        "SF18-MUTABLE-PRECOMMIT-REV",
                        PRE_COMMIT_CONFIG,
                        f"pre-commit repository revision must be immutable SHA: {match.group(1)}",
                    )
                )
            stripped = line.strip()
            if stripped.startswith("- types-") and "==" not in stripped:
                findings.append(
                    self._finding(
                        "SF18-FLOATING-PRECOMMIT-DEPENDENCY",
                        PRE_COMMIT_CONFIG,
                        f"pre-commit additional dependency must be exact-pinned: {stripped[2:]}",
                    )
                )
        return tuple(findings)

    def _audit_requirements(
        self, relative: str, text: str
    ) -> tuple[CIHardeningFinding, ...]:
        findings: list[CIHardeningFinding] = []
        requirements = tuple(self._requirement_lines(text))
        if not requirements:
            findings.append(
                self._finding(
                    "SF18-EMPTY-REQUIREMENTS",
                    relative,
                    "CI requirements lock must contain at least one exact dependency",
                )
            )
        for requirement in requirements:
            if _REQUIREMENT.fullmatch(requirement) is None:
                findings.append(
                    self._finding(
                        "SF18-FLOATING-REQUIREMENT",
                        relative,
                        f"CI dependency must use exact == pin: {requirement}",
                    )
                )
        if len(requirements) != len(set(requirements)):
            findings.append(
                self._finding(
                    "SF18-DUPLICATE-REQUIREMENT",
                    relative,
                    "CI requirements lock contains duplicate dependency entries",
                )
            )
        return tuple(findings)

    @staticmethod
    def _external_action_references(text: str) -> Iterable[str]:
        for line in text.splitlines():
            match = _USES.match(line)
            if not match:
                continue
            reference = match.group(1)
            if reference.startswith("./"):
                continue
            yield reference

    @staticmethod
    def _requirement_lines(text: str) -> Iterable[str]:
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            yield stripped

    @staticmethod
    def _finding(
        finding_id: str,
        path: str,
        reason: str,
    ) -> CIHardeningFinding:
        return CIHardeningFinding(
            finding_id=finding_id,
            severity=CIHardeningSeverity.BLOCK,
            path=path,
            reason=reason,
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit SF-18 CI supply-chain controls")
    parser.add_argument("--repository-root", default=".")
    args = parser.parse_args(argv)
    report = SoftwareFactoryCISupplyChainHardening().audit(
        Path(args.repository_root)
    )
    print(f"SF-18 CI supply-chain report: {report.report_sha256}")
    if report.passed:
        print("SF-18 CI supply-chain policy PASS")
        return 0
    for finding in report.findings:
        print(
            f"{finding.severity.value} {finding.finding_id} "
            f"{finding.path}: {finding.reason}"
        )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
