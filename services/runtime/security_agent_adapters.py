"""Defensive Security Factory adapters for canonical named-agent execution.

These adapters run inside the existing ``GovernedRuntime`` provider boundary.
They never initiate arbitrary external scans or exploit targets. Repository
specialists use deterministic local analysis; Web/API analysis accepts only
supplied observations for the SecurityFactory localhost/test allowlist; the
verifier independently re-evaluates a serialized report with distinct identity.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from services.security_factory import (
    SecurityFactory,
    SecurityFactoryError,
    SecurityFinding,
    SecurityReport,
    SecurityScope,
    Severity,
)

CODESEC_ADAPTER_KIND = "ilaios.runtime.security.codesec.v1"
WEB_API_ADAPTER_KIND = "ilaios.runtime.security.web-api.v1"
SUPPLY_CHAIN_ADAPTER_KIND = "ilaios.runtime.security.supply-chain.v1"
INFRASTRUCTURE_ADAPTER_KIND = "ilaios.runtime.security.infrastructure.v1"
VERIFIER_ADAPTER_KIND = "ilaios.runtime.security.verifier.v1"

SECURITY_LOCAL_PROVIDERS: Mapping[str, tuple[str, str]] = {
    "ilaios.security.local.codesec": (CODESEC_ADAPTER_KIND, "security.sast"),
    "ilaios.security.local.web-api": (WEB_API_ADAPTER_KIND, "security.web-api"),
    "ilaios.security.local.supply-chain": (
        SUPPLY_CHAIN_ADAPTER_KIND,
        "security.dependency",
    ),
    "ilaios.security.local.infrastructure": (
        INFRASTRUCTURE_ADAPTER_KIND,
        "security.infrastructure",
    ),
    "ilaios.security.local.verifier": (VERIFIER_ADAPTER_KIND, "security.verify"),
}


class SecurityAgentAdapterError(RuntimeError):
    """A defensive agent adapter received invalid or unsafe input."""


class SecurityAgentRuntimeAdapters:
    def __init__(self, factory: SecurityFactory | None = None) -> None:
        self._factory = factory or SecurityFactory()

    def runtime_adapters(self) -> Mapping[str, Callable[[dict[str, Any]], dict[str, Any]]]:
        return {
            CODESEC_ADAPTER_KIND: self._codesec,
            WEB_API_ADAPTER_KIND: self._web_api,
            SUPPLY_CHAIN_ADAPTER_KIND: self._supply_chain,
            INFRASTRUCTURE_ADAPTER_KIND: self._infrastructure,
            VERIFIER_ADAPTER_KIND: self._verify,
        }

    def _codesec(self, payload: dict[str, Any]) -> dict[str, Any]:
        report = self._factory.scan_repository(_scope(payload))
        return _report_json(_filter_report(report, {"sast", "secret"}))

    def _supply_chain(self, payload: dict[str, Any]) -> dict[str, Any]:
        report = self._factory.scan_repository(_scope(payload))
        return _report_json(_filter_report(report, {"supply-chain"}))

    def _infrastructure(self, payload: dict[str, Any]) -> dict[str, Any]:
        report = self._factory.scan_repository(_scope(payload))
        return _report_json(_filter_report(report, {"infrastructure"}))

    def _web_api(self, payload: dict[str, Any]) -> dict[str, Any]:
        scope = _scope(payload)
        target_url = _text(payload, "target_url")
        status_code = payload.get("status_code")
        headers = payload.get("headers")
        if not isinstance(status_code, int) or isinstance(status_code, bool):
            raise SecurityAgentAdapterError("status_code must be an integer")
        if not isinstance(headers, dict) or not all(
            isinstance(key, str) and isinstance(value, str)
            for key, value in headers.items()
        ):
            raise SecurityAgentAdapterError("headers must be a string map")
        try:
            report = self._factory.analyze_dast_observation(
                scope,
                target_url,
                status_code,
                headers,
            )
        except SecurityFactoryError as exc:
            raise SecurityAgentAdapterError("web/api observation is outside defensive scope") from exc
        return _report_json(report)

    def _verify(self, payload: dict[str, Any]) -> dict[str, Any]:
        producer_id = _text(payload, "producer_id")
        verifier_id = _text(payload, "verifier_id")
        report = _report_from_json(payload.get("report"))
        try:
            passed = self._factory.independently_verify(
                report,
                producer_id=producer_id,
                verifier_id=verifier_id,
            )
        except SecurityFactoryError as exc:
            raise SecurityAgentAdapterError("security verification failed closed") from exc
        return {
            "verified": passed,
            "scope_id": report.scope_id,
            "producer_id": producer_id,
            "verifier_id": verifier_id,
            "blocking_finding_count": len(report.blocking_findings),
            "finding_count": len(report.findings),
        }


def _scope(payload: dict[str, Any]) -> SecurityScope:
    scope_id = _text(payload, "scope_id")
    repository_root = _text(payload, "repository_root")
    try:
        return SecurityScope(scope_id, Path(repository_root).resolve())
    except SecurityFactoryError as exc:
        raise SecurityAgentAdapterError("security repository scope is invalid") from exc


def _filter_report(report: SecurityReport, categories: set[str]) -> SecurityReport:
    return SecurityReport(
        report.scope_id,
        tuple(item for item in report.findings if item.category in categories),
    )


def _report_json(report: SecurityReport) -> dict[str, Any]:
    return {
        "scope_id": report.scope_id,
        "passed": report.passed,
        "finding_count": len(report.findings),
        "blocking_finding_count": len(report.blocking_findings),
        "findings": [
            {
                "finding_id": item.finding_id,
                "category": item.category,
                "severity": item.severity.name,
                "location": item.location,
                "line": item.line,
                "message": item.message,
                "remediation": item.remediation,
                "fingerprint": item.fingerprint,
            }
            for item in report.findings
        ],
    }


def _report_from_json(value: object) -> SecurityReport:
    if not isinstance(value, dict):
        raise SecurityAgentAdapterError("verification report must be an object")
    scope_id = value.get("scope_id")
    raw_findings = value.get("findings")
    if not isinstance(scope_id, str) or not scope_id.strip():
        raise SecurityAgentAdapterError("verification report scope is invalid")
    if not isinstance(raw_findings, list):
        raise SecurityAgentAdapterError("verification report findings are invalid")
    findings: list[SecurityFinding] = []
    for raw in raw_findings:
        if not isinstance(raw, dict):
            raise SecurityAgentAdapterError("verification finding must be an object")
        try:
            finding = SecurityFinding(
                finding_id=str(raw["finding_id"]),
                category=str(raw["category"]),
                severity=Severity[str(raw["severity"])],
                location=str(raw["location"]),
                line=int(raw["line"]),
                message=str(raw["message"]),
                remediation=str(raw["remediation"]),
            )
        except (KeyError, ValueError, TypeError) as exc:
            raise SecurityAgentAdapterError("verification finding contract is invalid") from exc
        if not all(
            (finding.finding_id, finding.category, finding.location, finding.message, finding.remediation)
        ) or finding.line < 0:
            raise SecurityAgentAdapterError("verification finding fields are invalid")
        findings.append(finding)
    return SecurityReport(scope_id.strip(), tuple(findings))


def _text(payload: dict[str, Any], field: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value or value != value.strip():
        raise SecurityAgentAdapterError(f"{field} must be non-empty and trimmed")
    return value
