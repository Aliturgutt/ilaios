"""Defensive Security Factory adapters for canonical named-agent execution."""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from services.security_auth_authorization_analysis import (
    AuthAuthorizationCaseKind,
    AuthAuthorizationObservation,
    analyze_auth_authorization_observations,
)
from services.security_factory import (
    SecurityFactory,
    SecurityFactoryError,
    SecurityFinding,
    SecurityReport,
    SecurityScope,
    Severity,
)
from services.security_methodology_analysis import (
    SecurityMethodologyAnalysisError,
    SecurityMethodologyAnalyzer,
)
from services.security_methodology_skills import (
    AGENTIC_ACTION_AUDIT_SKILL_ID,
    AUTH_AUTHORIZATION_TESTING_SKILL_ID,
    DIFFERENTIAL_REVIEW_SKILL_ID,
    SECURITY_REVIEW_SKILL_ID,
    SUPPLY_CHAIN_AUDIT_SKILL_ID,
    THREAT_MODEL_SKILL_ID,
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

_PRIMARY_CODESEC_SKILL = "ilaios.skill.security.sast.v1"
_PRIMARY_WEB_API_SKILL = "ilaios.skill.security.web-api.v1"
_PRIMARY_SUPPLY_CHAIN_SKILL = "ilaios.skill.security.supply-chain.v1"
_PRIMARY_INFRASTRUCTURE_SKILL = "ilaios.skill.security.infrastructure.v1"
_PRIMARY_VERIFIER_SKILL = "ilaios.skill.security.verify.v1"
_RESERVED_SKILL_KEY = "_ilaios_skill"
_SHA1 = re.compile(r"^[0-9a-f]{40}$")


class SecurityAgentAdapterError(RuntimeError):
    """A defensive agent adapter received invalid or unsafe input."""


class SecurityAgentRuntimeAdapters:
    def __init__(self, factory: SecurityFactory | None = None) -> None:
        self._factory = factory or SecurityFactory()
        self._methodology = SecurityMethodologyAnalyzer(self._factory)

    def runtime_adapters(
        self,
    ) -> Mapping[str, Callable[[dict[str, Any]], dict[str, Any]]]:
        return {
            CODESEC_ADAPTER_KIND: self._codesec,
            WEB_API_ADAPTER_KIND: self._web_api,
            SUPPLY_CHAIN_ADAPTER_KIND: self._supply_chain,
            INFRASTRUCTURE_ADAPTER_KIND: self._infrastructure,
            VERIFIER_ADAPTER_KIND: self._verify,
        }

    def _codesec(self, payload: dict[str, Any]) -> dict[str, Any]:
        scope = _scope(payload)
        skill_id = _skill_id(payload, default=_PRIMARY_CODESEC_SKILL)
        try:
            if skill_id == SECURITY_REVIEW_SKILL_ID:
                return _report_json(self._methodology.security_review(scope))
            if skill_id == DIFFERENTIAL_REVIEW_SKILL_ID:
                return _report_json(
                    self._methodology.differential_review(
                        scope,
                        base_sha=_sha(payload, "base_sha"),
                        head_sha=_sha(payload, "head_sha"),
                        changed_paths=_string_tuple(payload, "changed_paths"),
                    )
                )
            if skill_id == THREAT_MODEL_SKILL_ID:
                report, surface = self._methodology.threat_model(scope)
                output = _report_json(report)
                output["threat_surface"] = {
                    key: list(value) for key, value in sorted(surface.items())
                }
                return output
        except SecurityMethodologyAnalysisError as exc:
            raise SecurityAgentAdapterError(
                "security methodology input or scope failed closed"
            ) from exc

        if skill_id != _PRIMARY_CODESEC_SKILL:
            raise SecurityAgentAdapterError("CodeSec skill is not authorized")
        report = self._factory.scan_repository(scope)
        return _report_json(_filter_report(report, {"sast", "secret"}))

    def _supply_chain(self, payload: dict[str, Any]) -> dict[str, Any]:
        scope = _scope(payload)
        skill_id = _skill_id(payload, default=_PRIMARY_SUPPLY_CHAIN_SKILL)
        if skill_id == SUPPLY_CHAIN_AUDIT_SKILL_ID:
            try:
                return _report_json(self._methodology.supply_chain_audit(scope))
            except SecurityMethodologyAnalysisError as exc:
                raise SecurityAgentAdapterError(
                    "supply-chain methodology failed closed"
                ) from exc
        if skill_id != _PRIMARY_SUPPLY_CHAIN_SKILL:
            raise SecurityAgentAdapterError(
                "SupplyChainSec skill is not authorized"
            )
        report = self._factory.scan_repository(scope)
        return _report_json(_filter_report(report, {"supply-chain"}))

    def _infrastructure(self, payload: dict[str, Any]) -> dict[str, Any]:
        scope = _scope(payload)
        skill_id = _skill_id(payload, default=_PRIMARY_INFRASTRUCTURE_SKILL)
        if skill_id == AGENTIC_ACTION_AUDIT_SKILL_ID:
            try:
                return _report_json(self._methodology.audit_agentic_actions(scope))
            except SecurityMethodologyAnalysisError as exc:
                raise SecurityAgentAdapterError(
                    "agentic action audit failed closed"
                ) from exc
        if skill_id != _PRIMARY_INFRASTRUCTURE_SKILL:
            raise SecurityAgentAdapterError(
                "InfrastructureSec skill is not authorized"
            )
        report = self._factory.scan_repository(scope)
        return _report_json(_filter_report(report, {"infrastructure", "container"}))

    def _web_api(self, payload: dict[str, Any]) -> dict[str, Any]:
        skill_id = _skill_id(payload, default=_PRIMARY_WEB_API_SKILL)
        scope = _scope(payload)
        if skill_id == AUTH_AUTHORIZATION_TESTING_SKILL_ID:
            return _report_json(
                analyze_auth_authorization_observations(
                    scope.scope_id,
                    _auth_authorization_observations(payload),
                )
            )
        if skill_id != _PRIMARY_WEB_API_SKILL:
            raise SecurityAgentAdapterError("WebAPISec skill is not authorized")
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
            raise SecurityAgentAdapterError(
                "web/api observation is outside defensive scope"
            ) from exc
        return _report_json(report)

    def _verify(self, payload: dict[str, Any]) -> dict[str, Any]:
        if (
            _skill_id(payload, default=_PRIMARY_VERIFIER_SKILL)
            != _PRIMARY_VERIFIER_SKILL
        ):
            raise SecurityAgentAdapterError(
                "SecurityVerifier skill is not authorized"
            )
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
            raise SecurityAgentAdapterError(
                "security verification failed closed"
            ) from exc
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
        raise SecurityAgentAdapterError(
            "security repository scope is invalid"
        ) from exc


def _skill_id(payload: dict[str, Any], *, default: str) -> str:
    raw = payload.get(_RESERVED_SKILL_KEY)
    if raw is None:
        return default
    if not isinstance(raw, dict):
        raise SecurityAgentAdapterError("runtime skill metadata is invalid")
    skill_id = raw.get("skill_id")
    if not isinstance(skill_id, str) or not skill_id or skill_id != skill_id.strip():
        raise SecurityAgentAdapterError("runtime skill identity is invalid")
    return skill_id


def _auth_authorization_observations(
    payload: dict[str, Any],
) -> tuple[AuthAuthorizationObservation, ...]:
    raw_observations = payload.get("observations")
    if not isinstance(raw_observations, list) or not raw_observations:
        raise SecurityAgentAdapterError("observations must be a non-empty list")
    observations: list[AuthAuthorizationObservation] = []
    try:
        for raw in raw_observations:
            if not isinstance(raw, dict):
                raise ValueError("observation must be an object")
            case_id = raw.get("case_id")
            kind = raw.get("kind")
            status_code = raw.get("status_code")
            location = raw.get("location", "runtime-observation")
            if not isinstance(case_id, str) or not isinstance(kind, str):
                raise ValueError("observation identity is invalid")
            if not isinstance(status_code, int) or isinstance(status_code, bool):
                raise ValueError("observation status_code is invalid")
            if not isinstance(location, str):
                raise ValueError("observation location is invalid")
            observations.append(
                AuthAuthorizationObservation(
                    case_id=case_id,
                    kind=AuthAuthorizationCaseKind(kind),
                    status_code=status_code,
                    location=location,
                )
            )
        return tuple(observations)
    except (TypeError, ValueError) as exc:
        raise SecurityAgentAdapterError(
            "auth/authorization observations failed closed"
        ) from exc


def _sha(payload: dict[str, Any], field: str) -> str:
    value = _text(payload, field)
    if _SHA1.fullmatch(value) is None:
        raise SecurityAgentAdapterError(
            f"{field} must be a lowercase 40-character SHA"
        )
    return value


def _string_tuple(payload: dict[str, Any], field: str) -> tuple[str, ...]:
    value = payload.get(field)
    if not isinstance(value, list) or not all(
        isinstance(item, str) and item and item == item.strip()
        for item in value
    ):
        raise SecurityAgentAdapterError(f"{field} must be a list of strings")
    return tuple(value)


def _filter_report(
    report: SecurityReport,
    categories: set[str],
) -> SecurityReport:
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
        raise SecurityAgentAdapterError(
            "verification report must be an object"
        )
    scope_id = value.get("scope_id")
    raw_findings = value.get("findings")
    if not isinstance(scope_id, str) or not scope_id.strip():
        raise SecurityAgentAdapterError(
            "verification report scope is invalid"
        )
    if not isinstance(raw_findings, list):
        raise SecurityAgentAdapterError(
            "verification report findings are invalid"
        )
    findings: list[SecurityFinding] = []
    for raw in raw_findings:
        if not isinstance(raw, dict):
            raise SecurityAgentAdapterError(
                "verification finding must be an object"
            )
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
            raise SecurityAgentAdapterError(
                "verification finding contract is invalid"
            ) from exc
        if not all(
            (
                finding.finding_id,
                finding.category,
                finding.location,
                finding.message,
                finding.remediation,
            )
        ) or finding.line < 0:
            raise SecurityAgentAdapterError(
                "verification finding fields are invalid"
            )
        findings.append(finding)
    return SecurityReport(scope_id.strip(), tuple(findings))


def _text(payload: dict[str, Any], field: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value or value != value.strip():
        raise SecurityAgentAdapterError(
            f"{field} must be non-empty and trimmed"
        )
    return value
