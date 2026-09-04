"""Bounded defensive Security Factory for ILAIOS.

The factory performs deterministic repository security analysis and validates
non-destructive DAST observations only for explicitly authorized local/test
hosts. It does not exploit targets, broaden scope, or authorize external
network activity.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path
from types import MappingProxyType
from typing import Mapping
from urllib.parse import urlparse


class SecurityFactoryError(RuntimeError):
    """Security Factory execution failed closed."""


class Severity(IntEnum):
    INFO = 10
    LOW = 20
    MEDIUM = 30
    HIGH = 40
    CRITICAL = 50


@dataclass(frozen=True, slots=True)
class SecurityScope:
    scope_id: str
    repository_root: Path
    allowed_local_targets: frozenset[str] = frozenset(
        {"localhost", "127.0.0.1", "::1"}
    )
    external_network_allowed: bool = False

    def __post_init__(self) -> None:
        if not self.scope_id.strip():
            raise SecurityFactoryError("explicit security scope ID is required")
        if self.external_network_allowed:
            raise SecurityFactoryError(
                "Security Factory v1 prohibits external-network testing"
            )
        root = self.repository_root.resolve()
        if not root.is_dir():
            raise SecurityFactoryError("authorized repository root must exist")
        if not self.allowed_local_targets:
            raise SecurityFactoryError("at least one local test target is required")


@dataclass(frozen=True, slots=True)
class SecurityFinding:
    finding_id: str
    category: str
    severity: Severity
    location: str
    line: int
    message: str
    remediation: str

    @property
    def fingerprint(self) -> str:
        return f"{self.category}:{self.location}:{self.line}:{self.finding_id}"


@dataclass(frozen=True, slots=True)
class SecurityReport:
    scope_id: str
    findings: tuple[SecurityFinding, ...]

    @property
    def passed(self) -> bool:
        return all(item.severity < Severity.HIGH for item in self.findings)

    @property
    def blocking_findings(self) -> tuple[SecurityFinding, ...]:
        return tuple(
            item for item in self.findings if item.severity >= Severity.HIGH
        )


@dataclass(frozen=True, slots=True)
class RetestResult:
    resolved: frozenset[str]
    remaining: frozenset[str]
    introduced: frozenset[str]

    @property
    def passed(self) -> bool:
        return not self.remaining and not self.introduced


@dataclass(frozen=True, slots=True)
class DependencyAdvisory:
    """Trusted local advisory input for deterministic dependency matching."""

    advisory_id: str
    package: str
    affected_versions: frozenset[str]
    severity: Severity
    remediation: str

    def __post_init__(self) -> None:
        if not self.advisory_id.strip() or not self.package.strip():
            raise SecurityFactoryError("dependency advisory identity and package are required")
        if not self.affected_versions or any(not item.strip() for item in self.affected_versions):
            raise SecurityFactoryError("dependency advisory affected versions are required")
        if not self.remediation.strip():
            raise SecurityFactoryError("dependency advisory remediation is required")


_TEXT_SUFFIXES = frozenset(
    {".py", ".toml", ".txt", ".yaml", ".yml", ".json", ".tf", ".ini", ".cfg"}
)
_SKIP_PARTS = frozenset({".git", "node_modules", ".venv", "venv", "build", "dist"})
_MAX_FILE_BYTES = 1_048_576

_SAST_RULES: tuple[tuple[str, re.Pattern[str], Severity, str, str], ...] = (
    (
        "SAST-EVAL",
        re.compile(r"\beval\s*\("),
        Severity.HIGH,
        "dynamic eval execution detected",
        "replace eval with deterministic parsing or an allowlisted dispatcher",
    ),
    (
        "SAST-EXEC",
        re.compile(r"\bexec\s*\("),
        Severity.HIGH,
        "dynamic exec execution detected",
        "replace exec with explicit code paths",
    ),
    (
        "SAST-SHELL-TRUE",
        re.compile(r"\bshell\s*=\s*True\b"),
        Severity.HIGH,
        "subprocess shell=True detected",
        "invoke an argument vector without a command shell",
    ),
    (
        "SAST-PICKLE-LOADS",
        re.compile(r"\bpickle\.loads?\s*\("),
        Severity.HIGH,
        "unsafe pickle deserialization detected",
        "use a non-executable serialization format with schema validation",
    ),
    (
        "SAST-YAML-LOAD",
        re.compile(r"\byaml\.load\s*\("),
        Severity.MEDIUM,
        "yaml.load requires explicit safe-loader review",
        "prefer yaml.safe_load for untrusted or configuration input",
    ),
)

_SECRET_RULES: tuple[tuple[str, re.Pattern[str], Severity, str], ...] = (
    (
        "SECRET-AWS-ACCESS-KEY",
        re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
        Severity.CRITICAL,
        "revoke/rotate the credential and remove it from repository history",
    ),
    (
        "SECRET-PRIVATE-KEY",
        re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
        Severity.CRITICAL,
        "revoke/rotate the key and store secrets outside Git",
    ),
)

_INFRA_RULES: tuple[tuple[str, re.Pattern[str], Severity, str, str], ...] = (
    (
        "INFRA-PUBLIC-CIDR",
        re.compile(r"(?:0\.0\.0\.0/0|::/0)"),
        Severity.HIGH,
        "world-open network CIDR detected",
        "restrict ingress/egress to the minimum required network scope",
    ),
    (
        "INFRA-WILDCARD-ACTION",
        re.compile(
            r"(?:\"Action\"\s*:\s*\"\*\"|\bAction\s*:\s*\"\*\"|Action\s*=\s*\[?\s*\"\*\")"
        ),
        Severity.HIGH,
        "wildcard infrastructure permission detected",
        "replace wildcard permissions with least-privilege actions",
    ),
)

_REQUIRED_HTTP_HEADERS = MappingProxyType(
    {
        "content-security-policy": "define a restrictive Content-Security-Policy",
        "x-content-type-options": "set X-Content-Type-Options: nosniff",
        "referrer-policy": "set an explicit Referrer-Policy",
    }
)


class SecurityFactory:
    """Deterministic defensive scanners plus authorized local DAST validation."""

    def scan_repository(self, scope: SecurityScope) -> SecurityReport:
        root = scope.repository_root.resolve()
        findings: list[SecurityFinding] = []
        for path in sorted(root.rglob("*")):
            if not path.is_file() or _SKIP_PARTS.intersection(path.parts):
                continue
            if path.stat().st_size > _MAX_FILE_BYTES:
                continue
            if path.suffix.casefold() not in _TEXT_SUFFIXES and path.name not in {
                "requirements.txt",
                "requirements-dev.txt",
            }:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            relative = path.relative_to(root).as_posix()
            findings.extend(self._scan_text(relative, text, path.suffix.casefold()))
        return SecurityReport(scope.scope_id, tuple(findings))

    def analyze_dast_observation(
        self,
        scope: SecurityScope,
        target_url: str,
        status_code: int,
        headers: Mapping[str, str],
    ) -> SecurityReport:
        parsed = urlparse(target_url)
        hostname = parsed.hostname or ""
        if parsed.scheme not in {"http", "https"}:
            raise SecurityFactoryError("DAST target must use http or https")
        if hostname not in scope.allowed_local_targets:
            raise SecurityFactoryError("DAST target is outside authorized local scope")
        if not 100 <= status_code <= 599:
            raise SecurityFactoryError("invalid HTTP status code")

        normalized = {key.casefold(): value for key, value in headers.items()}
        findings: list[SecurityFinding] = []
        for header, remediation in _REQUIRED_HTTP_HEADERS.items():
            if not normalized.get(header, "").strip():
                findings.append(
                    SecurityFinding(
                        f"DAST-MISSING-{header.upper()}",
                        "dast",
                        Severity.MEDIUM,
                        target_url,
                        0,
                        f"missing security header: {header}",
                        remediation,
                    )
                )
        if parsed.scheme == "https" and not normalized.get(
            "strict-transport-security", ""
        ).strip():
            findings.append(
                SecurityFinding(
                    "DAST-MISSING-HSTS",
                    "dast",
                    Severity.MEDIUM,
                    target_url,
                    0,
                    "HTTPS response is missing Strict-Transport-Security",
                    "set an appropriate Strict-Transport-Security policy",
                )
            )
        if status_code >= 500:
            findings.append(
                SecurityFinding(
                    "DAST-SERVER-ERROR",
                    "dast",
                    Severity.MEDIUM,
                    target_url,
                    0,
                    f"observed server error status {status_code}",
                    "inspect server-side error handling and remove sensitive error detail",
                )
            )
        return SecurityReport(scope.scope_id, tuple(findings))

    @staticmethod
    def analyze_dependency_advisories(
        scope_id: str,
        dependencies: Mapping[str, str],
        advisories: tuple[DependencyAdvisory, ...],
    ) -> SecurityReport:
        """Match an exact dependency inventory against trusted local advisory data."""
        if not scope_id.strip():
            raise SecurityFactoryError("explicit security scope ID is required")
        if not dependencies:
            raise SecurityFactoryError("dependency inventory is required")
        if not advisories:
            raise SecurityFactoryError("trusted local dependency advisory data is required")

        normalized: dict[str, str] = {}
        for package, version in dependencies.items():
            package_name = package.strip().casefold()
            exact_version = version.strip()
            if not package_name or not exact_version:
                raise SecurityFactoryError("dependency inventory entries must be exact and non-empty")
            normalized[package_name] = exact_version

        findings: list[SecurityFinding] = []
        for advisory in advisories:
            installed = normalized.get(advisory.package.strip().casefold())
            if installed is None or installed not in advisory.affected_versions:
                continue
            findings.append(
                SecurityFinding(
                    f"SUPPLY-{advisory.advisory_id.strip().upper()}",
                    "supply-chain",
                    advisory.severity,
                    advisory.package.strip(),
                    0,
                    f"installed dependency {advisory.package}=={installed} matches {advisory.advisory_id}",
                    advisory.remediation,
                )
            )
        return SecurityReport(scope_id, tuple(findings))

    @staticmethod
    def retest(before: SecurityReport, after: SecurityReport) -> RetestResult:
        if before.scope_id != after.scope_id:
            raise SecurityFactoryError("retest reports must use the same scope")
        old = {item.fingerprint for item in before.blocking_findings}
        new = {item.fingerprint for item in after.blocking_findings}
        return RetestResult(
            resolved=frozenset(old - new),
            remaining=frozenset(old & new),
            introduced=frozenset(new - old),
        )

    @staticmethod
    def independently_verify(
        report: SecurityReport, *, producer_id: str, verifier_id: str
    ) -> bool:
        if not producer_id or not verifier_id:
            raise SecurityFactoryError("producer and verifier identities are required")
        if producer_id == verifier_id:
            raise SecurityFactoryError("security producer cannot verify its own report")
        return report.passed

    def _scan_text(
        self, location: str, text: str, suffix: str
    ) -> list[SecurityFinding]:
        findings: list[SecurityFinding] = (
            _python_taint_findings(location, text) if suffix == ".py" else []
        )
        lines = text.splitlines()
        for line_number, line in enumerate(lines, start=1):
            for finding_id, pattern, severity, message, remediation in _SAST_RULES:
                if suffix == ".py" and pattern.search(line):
                    findings.append(
                        SecurityFinding(
                            finding_id,
                            "sast",
                            severity,
                            location,
                            line_number,
                            message,
                            remediation,
                        )
                    )
            for finding_id, pattern, severity, remediation in _SECRET_RULES:
                if pattern.search(line):
                    findings.append(
                        SecurityFinding(
                            finding_id,
                            "secret",
                            severity,
                            location,
                            line_number,
                            "credential-like material detected",
                            remediation,
                        )
                    )
            if suffix in {".yaml", ".yml", ".json", ".tf"}:
                for finding_id, pattern, severity, message, remediation in _INFRA_RULES:
                    if pattern.search(line):
                        findings.append(
                            SecurityFinding(
                                finding_id,
                                "infrastructure",
                                severity,
                                location,
                                line_number,
                                message,
                                remediation,
                            )
                        )

        if location.endswith(("requirements.txt", "requirements-dev.txt")):
            findings.extend(self._scan_requirement_lines(location, lines))
        if location.endswith("pyproject.toml"):
            findings.extend(self._scan_pyproject_dependencies(location, lines))
        return findings

    @staticmethod
    def _scan_requirement_lines(location: str, lines: list[str]) -> list[SecurityFinding]:
        return _requirement_findings(location, lines)

    @staticmethod
    def _scan_pyproject_dependencies(location: str, lines: list[str]) -> list[SecurityFinding]:
        return _pyproject_dependency_findings(location, lines)


_TAINT_SOURCE_CALLS = frozenset({"input", "request.args.get", "request.form.get", "request.json.get"})
_TAINT_SINK_CALLS = frozenset({"open", "subprocess.run", "subprocess.call", "subprocess.Popen", "requests.get", "requests.post", "urllib.request.urlopen"})


def _python_taint_findings(location: str, text: str) -> list[SecurityFinding]:
    """Detect direct local untrusted-input flows to sensitive Python sinks."""
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []

    tainted: set[str] = set()
    findings: list[SecurityFinding] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and _is_taint_source(node.value, tainted):
            tainted.update(target.id for target in node.targets if isinstance(target, ast.Name))
        if isinstance(node, ast.Call) and _call_name(node.func) in _TAINT_SINK_CALLS:
            if any(_is_taint_source(argument, tainted) for argument in node.args):
                sink = _call_name(node.func) or "sensitive sink"
                findings.append(SecurityFinding(
                    "SAST-TAINT-UNTRUSTED-TO-SINK", "sast", Severity.HIGH,
                    location, node.lineno,
                    f"untrusted input reaches sensitive sink: {sink}",
                    "validate and constrain untrusted input before the sensitive operation",
                ))
    return findings


def _is_taint_source(node: ast.AST, tainted: set[str]) -> bool:
    return (
        isinstance(node, ast.Name) and node.id in tainted
    ) or (
        isinstance(node, ast.Call) and _call_name(node.func) in _TAINT_SOURCE_CALLS
    )


def _call_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _call_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return None


def _requirement_findings(location: str, lines: list[str]) -> list[SecurityFinding]:
    findings: list[SecurityFinding] = []
    for line_number, raw in enumerate(lines, start=1):
        value = raw.strip()
        if value and not value.startswith(("#", "-r", "--")) and "==" not in value and " @ " not in value:
            findings.append(SecurityFinding("SUPPLY-UNPINNED-DEPENDENCY", "supply-chain", Severity.MEDIUM, location, line_number, f"dependency is not exactly pinned: {value}", "pin an exact reviewed version or immutable artifact reference"))
    return findings


def _pyproject_dependency_findings(location: str, lines: list[str]) -> list[SecurityFinding]:
    findings: list[SecurityFinding] = []
    in_dependencies = False
    for line_number, raw in enumerate(lines, start=1):
        value = raw.strip()
        if value.startswith("dependencies") and "[" in value:
            in_dependencies = True
        elif in_dependencies and value.startswith("]"):
            in_dependencies = False
        elif in_dependencies and value.startswith(("\"", "'")):
            dependency = value.strip(",").strip("\"'")
            if dependency and "==" not in dependency and " @ " not in dependency:
                findings.append(SecurityFinding("SUPPLY-UNPINNED-DEPENDENCY", "supply-chain", Severity.MEDIUM, location, line_number, f"dependency is not exactly pinned: {dependency}", "pin an exact reviewed version or immutable artifact reference"))
    return findings
