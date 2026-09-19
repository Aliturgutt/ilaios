"""Controlled external security-tool adapters for the canonical ILAIOS Security Factory.

This module does not create a second security authority. It only normalizes
already-executed, explicitly authorized tool results from ZAP, Nuclei, Semgrep,
and Trivy into the existing SecurityReport / SecurityFinding evidence model.
Production targets are rejected fail-closed; callers must use local/staging scope.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable
from urllib.parse import urlparse

from services.security_factory import (
    RetestResult,
    SecurityFactory,
    SecurityFactoryError,
    SecurityFinding,
    SecurityReport,
    Severity,
)


class SecurityExternalToolAdapterError(SecurityFactoryError):
    """External security-tool evidence failed closed."""


@dataclass(frozen=True, slots=True)
class SecurityToolEvidence:
    tool: str
    scope_id: str
    target: str
    source_sha: str
    findings: tuple[SecurityFinding, ...]

    @property
    def report(self) -> SecurityReport:
        return SecurityReport(self.scope_id, self.findings)


_ALLOWED_TOOLS = frozenset({"zap", "nuclei", "semgrep", "trivy"})
_ALLOWED_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})
_SEVERITY = {
    "info": Severity.INFO,
    "informational": Severity.INFO,
    "low": Severity.LOW,
    "medium": Severity.MEDIUM,
    "moderate": Severity.MEDIUM,
    "high": Severity.HIGH,
    "critical": Severity.CRITICAL,
    "error": Severity.HIGH,
    "warning": Severity.MEDIUM,
}


def normalize_external_tool_result(
    *,
    tool: str,
    scope_id: str,
    target: str,
    source_sha: str,
    raw_findings: Iterable[dict[str, Any]],
    allow_staging_hosts: frozenset[str] = frozenset(),
) -> SecurityToolEvidence:
    """Normalize bounded tool observations into canonical Security evidence.

    The adapter is deliberately non-executing: it cannot launch scanners, mutate
    infrastructure, bypass authorization, or broaden target scope. External tool
    execution remains a governed Tool Gateway concern.
    """

    normalized_tool = tool.strip().casefold()
    if normalized_tool not in _ALLOWED_TOOLS:
        raise SecurityExternalToolAdapterError("external security tool is not allowlisted")
    if not scope_id.strip():
        raise SecurityExternalToolAdapterError("explicit security scope ID is required")
    if len(source_sha) != 40 or any(char not in "0123456789abcdef" for char in source_sha):
        raise SecurityExternalToolAdapterError("source_sha must be a lowercase 40-character SHA")

    _validate_target(target, allow_staging_hosts)

    findings: list[SecurityFinding] = []
    for index, raw in enumerate(raw_findings, start=1):
        if not isinstance(raw, dict):
            raise SecurityExternalToolAdapterError("tool finding must be an object")
        severity_name = str(raw.get("severity", "medium")).strip().casefold()
        severity = _SEVERITY.get(severity_name)
        if severity is None:
            raise SecurityExternalToolAdapterError("tool finding severity is unsupported")

        finding_id = str(raw.get("id") or f"{normalized_tool.upper()}-{index}").strip()
        location = str(raw.get("location") or target).strip()
        message = str(raw.get("message") or raw.get("title") or "external tool finding").strip()
        remediation = str(raw.get("remediation") or "review and remediate the validated finding").strip()
        line_raw = raw.get("line", 0)
        try:
            line = int(line_raw)
        except (TypeError, ValueError) as exc:
            raise SecurityExternalToolAdapterError("tool finding line is invalid") from exc
        if not finding_id or not location or not message or not remediation or line < 0:
            raise SecurityExternalToolAdapterError("tool finding fields are invalid")

        findings.append(
            SecurityFinding(
                finding_id=f"EXT-{normalized_tool.upper()}-{finding_id}",
                category=f"external-{normalized_tool}",
                severity=severity,
                location=location,
                line=line,
                message=message,
                remediation=remediation,
            )
        )

    return SecurityToolEvidence(
        tool=normalized_tool,
        scope_id=scope_id.strip(),
        target=target,
        source_sha=source_sha,
        findings=tuple(findings),
    )


def retest_external_tool_result(
    before: SecurityToolEvidence, after: SecurityToolEvidence
) -> RetestResult:
    if before.tool != after.tool:
        raise SecurityExternalToolAdapterError("retest must use the same external tool")
    if before.target != after.target or before.source_sha == after.source_sha:
        raise SecurityExternalToolAdapterError(
            "retest target must match and source SHA must advance"
        )
    if before.scope_id != after.scope_id:
        raise SecurityExternalToolAdapterError("retest scope must match")
    return SecurityFactory.retest(before.report, after.report)


def _validate_target(target: str, allow_staging_hosts: frozenset[str]) -> None:
    parsed = urlparse(target)
    if parsed.scheme not in {"http", "https", "file"}:
        raise SecurityExternalToolAdapterError("security tool target scheme is not allowed")
    if parsed.scheme == "file":
        return
    hostname = parsed.hostname or ""
    allowed = _ALLOWED_HOSTS | allow_staging_hosts
    if hostname not in allowed:
        raise SecurityExternalToolAdapterError(
            "production or unapproved external target is forbidden"
        )
