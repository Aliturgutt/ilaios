"""Normalize approved external security-tool evidence into the canonical SecurityReport.

This module does not launch scanners or authorize targets. It only consumes local evidence
files produced by an already-authorized execution context and converts findings into the
existing SecurityFactory evidence contract.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from services.security_factory import (
    RetestResult,
    SecurityFactory,
    SecurityFactoryError,
    SecurityFinding,
    SecurityReport,
    Severity,
)


class ExternalSecurityEvidenceError(SecurityFactoryError):
    """External scanner evidence failed closed."""


def report_from_external_tool(*, scope_id: str, tool: str, evidence_path: Path) -> SecurityReport:
    if not scope_id.strip():
        raise ExternalSecurityEvidenceError("explicit security scope ID is required")
    path = evidence_path.resolve()
    if not path.is_file():
        raise ExternalSecurityEvidenceError("external security evidence file is required")
    normalized_tool = tool.strip().casefold()
    if normalized_tool == "semgrep":
        findings = _semgrep(path)
    elif normalized_tool == "trivy":
        findings = _trivy(path)
    elif normalized_tool == "nuclei":
        findings = _nuclei(path)
    elif normalized_tool == "zap":
        findings = _zap(path)
    else:
        raise ExternalSecurityEvidenceError("external security tool is not allowlisted")
    return SecurityReport(scope_id.strip(), tuple(findings))


def retest_external_tool(*, before: SecurityReport, after: SecurityReport) -> RetestResult:
    return SecurityFactory.retest(before, after)


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ExternalSecurityEvidenceError("external security evidence is invalid JSON") from exc


def _severity(value: object, *, default: Severity = Severity.MEDIUM) -> Severity:
    text = str(value or "").strip().upper()
    aliases = {
        "CRITICAL": Severity.CRITICAL,
        "HIGH": Severity.HIGH,
        "ERROR": Severity.HIGH,
        "MEDIUM": Severity.MEDIUM,
        "MODERATE": Severity.MEDIUM,
        "WARNING": Severity.MEDIUM,
        "LOW": Severity.LOW,
        "INFO": Severity.INFO,
        "INFORMATIONAL": Severity.INFO,
    }
    return aliases.get(text, default)


def _finding(
    tool: str,
    finding_id: str,
    severity: Severity,
    location: str,
    message: str,
    remediation: str,
    line: int = 0,
) -> SecurityFinding:
    return SecurityFinding(
        finding_id=f"{tool.upper()}-{finding_id}"[:180],
        category=f"external-{tool}",
        severity=severity,
        location=location or tool,
        line=max(0, line),
        message=message or f"{tool} security finding",
        remediation=remediation
        or "review and remediate the scanner finding, then rerun the same bounded exercise",
    )


def _semgrep(path: Path) -> list[SecurityFinding]:
    data = _load_json(path)
    results = data.get("results", []) if isinstance(data, dict) else []
    findings: list[SecurityFinding] = []
    for item in results:
        if not isinstance(item, dict):
            continue
        extra_raw = item.get("extra")
        extra: dict[str, Any] = extra_raw if isinstance(extra_raw, dict) else {}
        start_raw = item.get("start")
        start: dict[str, Any] = start_raw if isinstance(start_raw, dict) else {}
        findings.append(
            _finding(
                "semgrep",
                str(item.get("check_id") or "RULE"),
                _severity(extra.get("severity")),
                str(item.get("path") or "repository"),
                str(extra.get("message") or item.get("check_id") or "Semgrep finding"),
                str(extra.get("fix") or "apply the reviewed Semgrep remediation"),
                int(start.get("line") or 0),
            )
        )
    return findings


def _trivy(path: Path) -> list[SecurityFinding]:
    data = _load_json(path)
    results = data.get("Results", []) if isinstance(data, dict) else []
    findings: list[SecurityFinding] = []
    for result in results:
        if not isinstance(result, dict):
            continue
        target = str(result.get("Target") or "repository")
        for item in result.get("Vulnerabilities") or []:
            if not isinstance(item, dict):
                continue
            findings.append(
                _finding(
                    "trivy",
                    str(item.get("VulnerabilityID") or "VULN"),
                    _severity(item.get("Severity")),
                    target,
                    str(item.get("Title") or item.get("Description") or "Trivy vulnerability"),
                    f"upgrade {item.get('PkgName') or 'affected package'} to {item.get('FixedVersion') or 'a reviewed fixed version'}",
                )
            )
        for item in result.get("Misconfigurations") or []:
            if not isinstance(item, dict):
                continue
            findings.append(
                _finding(
                    "trivy",
                    str(item.get("ID") or "MISCONFIG"),
                    _severity(item.get("Severity")),
                    target,
                    str(item.get("Title") or item.get("Message") or "Trivy misconfiguration"),
                    str(
                        item.get("Resolution")
                        or "apply the reviewed Trivy configuration remediation"
                    ),
                )
            )
    return findings


def _nuclei(path: Path) -> list[SecurityFinding]:
    findings: list[SecurityFinding] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as exc:
        raise ExternalSecurityEvidenceError("Nuclei evidence could not be read") from exc
    for raw in lines:
        if not raw.strip():
            continue
        try:
            item = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ExternalSecurityEvidenceError("Nuclei evidence contains invalid JSONL") from exc
        if not isinstance(item, dict):
            continue
        info_raw = item.get("info")
        info: dict[str, Any] = info_raw if isinstance(info_raw, dict) else {}
        findings.append(
            _finding(
                "nuclei",
                str(item.get("template-id") or item.get("templateID") or "TEMPLATE"),
                _severity(info.get("severity")),
                str(item.get("matched-at") or item.get("host") or "authorized-target"),
                str(info.get("name") or "Nuclei finding"),
                str(
                    info.get("remediation")
                    or "review the matched Nuclei template and remediate the affected surface"
                ),
            )
        )
    return findings


def _zap(path: Path) -> list[SecurityFinding]:
    data = _load_json(path)
    sites = data.get("site", []) if isinstance(data, dict) else []
    findings: list[SecurityFinding] = []
    risk = {
        "3": Severity.HIGH,
        "2": Severity.MEDIUM,
        "1": Severity.LOW,
        "0": Severity.INFO,
    }
    for site in sites:
        if not isinstance(site, dict):
            continue
        for alert in site.get("alerts") or []:
            if not isinstance(alert, dict):
                continue
            instances = alert.get("instances") or [{}]
            first_instance = instances[0] if isinstance(instances, list) and instances else {}
            instance: dict[str, Any] = (
                first_instance if isinstance(first_instance, dict) else {}
            )
            findings.append(
                _finding(
                    "zap",
                    str(alert.get("pluginid") or alert.get("alertRef") or "ALERT"),
                    risk.get(str(alert.get("riskcode")), _severity(alert.get("riskdesc"))),
                    str(instance.get("uri") or site.get("@name") or "authorized-target"),
                    str(alert.get("alert") or alert.get("name") or "ZAP finding"),
                    str(alert.get("solution") or "apply the reviewed ZAP remediation"),
                )
            )
    return findings
