"""Deterministic read-only analyses for ILAIOS security methodology skills.

This module extends the existing SecurityFactory with bounded review workflows.
It never performs network requests, executes repository content, mutates the
target repository, or grants authority.
"""

from __future__ import annotations

import re
from pathlib import Path, PurePosixPath
from typing import Final

from services.security_factory import (
    SecurityFactory,
    SecurityFactoryError,
    SecurityFinding,
    SecurityReport,
    SecurityScope,
    Severity,
)

_MAX_FILE_BYTES: Final = 1_048_576
_SHA1 = re.compile(r"^[0-9a-f]{40}$")
_GITHUB_SHA = re.compile(r"^[0-9a-fA-F]{40}$")

_AI_ACTION_PREFIXES: tuple[str, ...] = (
    "anthropics/claude-code-action@",
    "google-github-actions/run-gemini-cli@",
    "google-gemini/gemini-cli-action@",
    "openai/codex-action@",
    "actions/ai-inference@",
)

_HIGH_PROTECTION_PATH_MARKERS: tuple[str, ...] = (
    "auth",
    "identity",
    "tenant",
    "policy",
    "approval",
    "governance",
    "security",
    "runtime",
    "tool_gateway",
    "tool-gateway",
    "provider",
    ".github/workflows",
)

_THREAT_BOUNDARY_MARKERS: dict[str, tuple[str, ...]] = {
    "identity_and_authentication": ("identity", "auth", "oidc"),
    "tenant_isolation": ("tenant",),
    "policy_and_governance": ("policy", "governance"),
    "approval_boundary": ("approval",),
    "tool_gateway": ("tool_gateway", "tool-gateway", "toolgateway"),
    "evidence_and_audit": ("evidence", "audit"),
    "provider_and_routing": ("provider", "routing"),
    "ci_workflows": (".github/workflows",),
}


class SecurityMethodologyAnalysisError(SecurityFactoryError):
    """A bounded methodology analysis received invalid evidence or scope."""


class SecurityMethodologyAnalyzer:
    """Additive, deterministic analyses over an explicitly authorized repository."""

    def __init__(self, factory: SecurityFactory | None = None) -> None:
        self._factory = factory or SecurityFactory()

    def security_review(self, scope: SecurityScope) -> SecurityReport:
        report = self._factory.scan_repository(scope)
        return _filter_report(report, {"sast", "secret"})

    def differential_review(
        self,
        scope: SecurityScope,
        *,
        base_sha: str,
        head_sha: str,
        changed_paths: tuple[str, ...],
    ) -> SecurityReport:
        _require_sha(base_sha, "base_sha")
        _require_sha(head_sha, "head_sha")
        paths = _validated_changed_paths(scope, changed_paths)
        if not paths:
            return SecurityReport(scope.scope_id, ())

        full = self._factory.scan_repository(scope)
        changed_set = frozenset(paths)
        findings = [
            item for item in full.findings if item.location in changed_set
        ]

        protected_change = any(
            marker in path.casefold()
            for path in paths
            for marker in _HIGH_PROTECTION_PATH_MARKERS
        )
        test_change = any(_is_test_path(path) for path in paths)
        if protected_change and not test_change:
            findings.append(
                SecurityFinding(
                    finding_id="DIFF-PROTECTED-CHANGE-WITHOUT-TEST-EVIDENCE",
                    category="differential-review",
                    severity=Severity.MEDIUM,
                    location=paths[0],
                    line=0,
                    message=(
                        "security-sensitive change set has no changed test path "
                        "in the supplied differential evidence"
                    ),
                    remediation=(
                        "attach relevant regression-test evidence or explain why "
                        "the protected change is test-independent"
                    ),
                )
            )
        return SecurityReport(scope.scope_id, tuple(findings))

    def audit_agentic_actions(self, scope: SecurityScope) -> SecurityReport:
        findings: list[SecurityFinding] = []
        root = scope.repository_root.resolve()
        workflow_root = root / ".github" / "workflows"
        if not workflow_root.is_dir():
            return SecurityReport(scope.scope_id, ())

        for path in sorted(workflow_root.iterdir()):
            if not path.is_file() or path.suffix.casefold() not in {".yml", ".yaml"}:
                continue
            text = _read_bounded_text(path, root)
            if text is None:
                continue
            lines = text.splitlines()
            ai_lines = [
                index
                for index, line in enumerate(lines, start=1)
                if any(prefix in line for prefix in _AI_ACTION_PREFIXES)
            ]
            if not ai_lines:
                continue
            relative = path.relative_to(root).as_posix()

            for index, line in enumerate(lines, start=1):
                stripped = line.strip()
                lower = stripped.casefold()

                if re.search(r"(^|\s)pull_request_target\s*:", stripped):
                    findings.append(
                        _finding(
                            "AGENTIC-PR-TARGET",
                            relative,
                            index,
                            Severity.HIGH,
                            "AI-enabled workflow uses pull_request_target",
                            (
                                "separate untrusted pull-request data from privileged "
                                "workflow execution and require a reviewed handoff"
                            ),
                        )
                    )

                if any(
                    token in lower
                    for token in (
                        "danger-full-access",
                        "safety-strategy: unsafe",
                        "--yolo",
                        "bash(*)",
                    )
                ):
                    findings.append(
                        _finding(
                            "AGENTIC-UNSAFE-EXECUTION-MODE",
                            relative,
                            index,
                            Severity.HIGH,
                            "AI-enabled workflow contains an unsafe execution mode",
                            (
                                "use the narrowest read/write sandbox and explicit "
                                "tool permissions permitted by the task"
                            ),
                        )
                    )

                if re.search(
                    r"(allow-users|allowed_non_write_users)\s*:\s*[\"']?\*[\"']?",
                    stripped,
                    flags=re.IGNORECASE,
                ):
                    findings.append(
                        _finding(
                            "AGENTIC-WILDCARD-CALLER",
                            relative,
                            index,
                            Severity.HIGH,
                            "AI-enabled workflow allows an unrestricted caller set",
                            "replace wildcard caller admission with an explicit allowlist",
                        )
                    )

                if "${{ github.event." in line and _near_prompt(lines, index):
                    findings.append(
                        _finding(
                            "AGENTIC-UNTRUSTED-EVENT-TO-PROMPT",
                            relative,
                            index,
                            Severity.HIGH,
                            (
                                "GitHub event data can flow directly into an AI prompt "
                                "or prompt-adjacent field"
                            ),
                            (
                                "treat event content as untrusted data and pass only "
                                "validated, bounded fields through a non-authoritative channel"
                            ),
                        )
                    )

                if re.search(r"\b(contents|pull-requests|issues)\s*:\s*write\b", lower):
                    findings.append(
                        _finding(
                            "AGENTIC-BROAD-WRITE-PERMISSION",
                            relative,
                            index,
                            Severity.MEDIUM,
                            "AI-enabled workflow grants repository write permission",
                            (
                                "reduce workflow permissions to read-only unless a "
                                "separately approved write step requires escalation"
                            ),
                        )
                    )

                if (
                    re.search(r"\b(eval|exec)\b", lower)
                    and "steps." in lower
                    and ".outputs." in lower
                ):
                    findings.append(
                        _finding(
                            "AGENTIC-AI-OUTPUT-EXECUTION",
                            relative,
                            index,
                            Severity.CRITICAL,
                            "workflow appears to execute a prior step output",
                            (
                                "never evaluate AI-produced text; parse against a strict "
                                "schema and dispatch through an allowlisted operation"
                            ),
                        )
                    )

            env_sources = _attacker_controlled_env(lines)
            for variable, source_line in env_sources.items():
                if _prompt_references_env(lines, variable):
                    findings.append(
                        _finding(
                            "AGENTIC-EVENT-ENV-PROMPT-FLOW",
                            relative,
                            source_line,
                            Severity.HIGH,
                            (
                                "attacker-controlled GitHub event data reaches an "
                                "AI prompt through an environment variable"
                            ),
                            (
                                "validate and bound the event field before prompt use, "
                                "or remove the data path from privileged AI execution"
                            ),
                        )
                    )

        return SecurityReport(scope.scope_id, tuple(_dedupe(findings)))

    def supply_chain_audit(self, scope: SecurityScope) -> SecurityReport:
        base = _filter_report(self._factory.scan_repository(scope), {"supply-chain"})
        findings = list(base.findings)
        root = scope.repository_root.resolve()

        workflow_root = root / ".github" / "workflows"
        if workflow_root.is_dir():
            for path in sorted(workflow_root.iterdir()):
                if not path.is_file() or path.suffix.casefold() not in {".yml", ".yaml"}:
                    continue
                text = _read_bounded_text(path, root)
                if text is None:
                    continue
                relative = path.relative_to(root).as_posix()
                for index, line in enumerate(text.splitlines(), start=1):
                    match = re.search(r"\buses\s*:\s*[\"']?([^\"'\s#]+)", line)
                    if match is None:
                        continue
                    reference = match.group(1)
                    if reference.startswith("./") or reference.startswith("docker://"):
                        continue
                    if "@" not in reference:
                        findings.append(
                            _finding(
                                "SUPPLY-GHA-UNVERSIONED-ACTION",
                                relative,
                                index,
                                Severity.MEDIUM,
                                "GitHub Action reference has no immutable version",
                                "pin the action to a reviewed 40-character commit SHA",
                                category="supply-chain",
                            )
                        )
                        continue
                    _, ref = reference.rsplit("@", 1)
                    if _GITHUB_SHA.fullmatch(ref) is None:
                        findings.append(
                            _finding(
                                "SUPPLY-GHA-MUTABLE-REF",
                                relative,
                                index,
                                Severity.MEDIUM,
                                "GitHub Action reference is mutable",
                                "pin the action to a reviewed 40-character commit SHA",
                                category="supply-chain",
                            )
                        )

        for path in sorted(root.rglob("Dockerfile*")):
            if not path.is_file() or any(
                part in {".git", "node_modules", ".venv", "venv", "build", "dist"}
                for part in path.parts
            ):
                continue
            text = _read_bounded_text(path, root)
            if text is None:
                continue
            relative = path.relative_to(root).as_posix()
            for index, line in enumerate(text.splitlines(), start=1):
                stripped = line.strip()
                if not stripped.upper().startswith("FROM "):
                    continue
                image = stripped.split(maxsplit=1)[1].split()[0]
                if image.casefold().endswith(":latest") and "@sha256:" not in image:
                    findings.append(
                        _finding(
                            "SUPPLY-DOCKER-LATEST",
                            relative,
                            index,
                            Severity.MEDIUM,
                            "container base image uses the mutable latest tag",
                            "pin the base image to a reviewed digest",
                            category="supply-chain",
                        )
                    )

        return SecurityReport(scope.scope_id, tuple(_dedupe(findings)))

    def threat_model(
        self,
        scope: SecurityScope,
    ) -> tuple[SecurityReport, dict[str, tuple[str, ...]]]:
        surface = self.threat_surface(scope)
        findings: list[SecurityFinding] = []
        for boundary, evidence_paths in surface.items():
            if evidence_paths:
                continue
            findings.append(
                SecurityFinding(
                    finding_id=f"THREAT-MODEL-MISSING-{boundary.upper().replace('_', '-')}",
                    category="threat-model",
                    severity=Severity.MEDIUM,
                    location=".",
                    line=0,
                    message=f"no repository evidence found for trust boundary: {boundary}",
                    remediation=(
                        "identify the implementing control and attach its repository "
                        "path or record the boundary as intentionally absent"
                    ),
                )
            )
        return SecurityReport(scope.scope_id, tuple(findings)), surface

    def threat_surface(self, scope: SecurityScope) -> dict[str, tuple[str, ...]]:
        root = scope.repository_root.resolve()
        paths: list[tuple[str, str]] = []
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            try:
                resolved = path.resolve()
                relative = path.relative_to(root).as_posix()
            except (OSError, ValueError) as exc:
                raise SecurityMethodologyAnalysisError(
                    "repository path could not be bounded to authorized scope"
                ) from exc
            if not resolved.is_relative_to(root):
                raise SecurityMethodologyAnalysisError(
                    "repository path resolved outside authorized scope"
                )
            if any(
                part in {".git", "node_modules", ".venv", "venv", "build", "dist"}
                for part in PurePosixPath(relative).parts
            ):
                continue
            paths.append((relative, relative.casefold()))

        surface: dict[str, tuple[str, ...]] = {}
        for boundary, markers in _THREAT_BOUNDARY_MARKERS.items():
            matched = [
                original
                for original, lowered in paths
                if any(marker in lowered for marker in markers)
            ]
            surface[boundary] = tuple(matched[:20])
        return surface


def _validated_changed_paths(
    scope: SecurityScope,
    changed_paths: tuple[str, ...],
) -> tuple[str, ...]:
    root = scope.repository_root.resolve()
    output: list[str] = []
    for raw in changed_paths:
        if not raw or raw != raw.strip() or "\\" in raw:
            raise SecurityMethodologyAnalysisError("changed path must be normalized")
        pure = PurePosixPath(raw)
        if pure.is_absolute() or ".." in pure.parts or "." in pure.parts:
            raise SecurityMethodologyAnalysisError("changed path escapes repository scope")
        candidate = (root / Path(*pure.parts)).resolve()
        if not candidate.is_relative_to(root):
            raise SecurityMethodologyAnalysisError("changed path escapes repository scope")
        output.append(pure.as_posix())
    if len(output) != len(set(output)):
        raise SecurityMethodologyAnalysisError("changed paths must be unique")
    return tuple(output)


def _require_sha(value: str, field: str) -> None:
    if _SHA1.fullmatch(value) is None:
        raise SecurityMethodologyAnalysisError(
            f"{field} must be a lowercase 40-character SHA"
        )


def _is_test_path(path: str) -> bool:
    lower = path.casefold()
    name = PurePosixPath(lower).name
    return (
        "/tests/" in f"/{lower}/"
        or name.startswith("test_")
        or name.endswith(("_test.py", ".test.ts", ".test.tsx", ".spec.ts", ".spec.tsx"))
    )


def _filter_report(report: SecurityReport, categories: set[str]) -> SecurityReport:
    return SecurityReport(
        report.scope_id,
        tuple(item for item in report.findings if item.category in categories),
    )


def _finding(
    finding_id: str,
    location: str,
    line: int,
    severity: Severity,
    message: str,
    remediation: str,
    *,
    category: str = "agentic-action",
) -> SecurityFinding:
    return SecurityFinding(
        finding_id=finding_id,
        category=category,
        severity=severity,
        location=location,
        line=line,
        message=message,
        remediation=remediation,
    )


def _read_bounded_text(path: Path, root: Path) -> str | None:
    try:
        resolved = path.resolve()
        if not resolved.is_relative_to(root.resolve()):
            raise SecurityMethodologyAnalysisError(
                "audited file resolved outside authorized scope"
            )
        if path.stat().st_size > _MAX_FILE_BYTES:
            return None
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return None
    except OSError as exc:
        raise SecurityMethodologyAnalysisError(
            "audited file could not be read safely"
        ) from exc


def _near_prompt(lines: list[str], line_number: int) -> bool:
    start = max(0, line_number - 6)
    end = min(len(lines), line_number + 5)
    return any(
        re.search(r"\b(prompt|system[-_]?prompt)\s*:", line, re.IGNORECASE)
        for line in lines[start:end]
    )


def _attacker_controlled_env(lines: list[str]) -> dict[str, int]:
    result: dict[str, int] = {}
    pattern = re.compile(
        r"^\s*([A-Z_][A-Z0-9_]*)\s*:\s*.*\$\{\{\s*github\.event\.",
        re.IGNORECASE,
    )
    for index, line in enumerate(lines, start=1):
        match = pattern.search(line)
        if match is not None:
            result[match.group(1)] = index
    return result


def _prompt_references_env(lines: list[str], variable: str) -> bool:
    references = (f"${variable}", f"${{{variable}}}")
    for index, line in enumerate(lines, start=1):
        if not any(reference in line for reference in references):
            continue
        if _near_prompt(lines, index):
            return True
    return False


def _dedupe(findings: list[SecurityFinding]) -> list[SecurityFinding]:
    seen: set[str] = set()
    output: list[SecurityFinding] = []
    for finding in findings:
        if finding.fingerprint in seen:
            continue
        seen.add(finding.fingerprint)
        output.append(finding)
    return output
