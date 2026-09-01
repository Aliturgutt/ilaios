"""Bounded authentication/authorization evidence analysis for ILAIOS Security Factory.

This module evaluates caller-supplied, already-observed authorization outcomes.
It performs no network access, credential use, repository mutation, or exploit execution.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from services.security_factory import SecurityFinding, SecurityReport, Severity


class AuthAuthorizationCaseKind(StrEnum):
    UNAUTHENTICATED = "unauthenticated"
    CROSS_TENANT = "cross_tenant"
    INSUFFICIENT_ROLE = "insufficient_role"
    AUTHORIZED = "authorized"


@dataclass(frozen=True, slots=True)
class AuthAuthorizationObservation:
    case_id: str
    kind: AuthAuthorizationCaseKind
    status_code: int
    location: str = "runtime-observation"

    def __post_init__(self) -> None:
        if not self.case_id or self.case_id != self.case_id.strip():
            raise ValueError("case_id must be non-empty and trimmed")
        if not isinstance(self.status_code, int) or isinstance(self.status_code, bool):
            raise ValueError("status_code must be an integer")
        if self.status_code < 100 or self.status_code > 599:
            raise ValueError("status_code must be a valid HTTP status")
        if not self.location or self.location != self.location.strip():
            raise ValueError("location must be non-empty and trimmed")


def analyze_auth_authorization_observations(
    scope_id: str,
    observations: tuple[AuthAuthorizationObservation, ...],
) -> SecurityReport:
    if not scope_id or scope_id != scope_id.strip():
        raise ValueError("scope_id must be non-empty and trimmed")
    if not observations:
        raise ValueError("at least one auth/authorization observation is required")

    seen: set[str] = set()
    findings: list[SecurityFinding] = []
    for observation in observations:
        if observation.case_id in seen:
            raise ValueError("case_id values must be unique")
        seen.add(observation.case_id)

        denied = observation.status_code in {401, 403}
        allowed = 200 <= observation.status_code < 400

        if observation.kind is AuthAuthorizationCaseKind.UNAUTHENTICATED and not denied:
            findings.append(
                _finding(
                    observation,
                    "AUTH-UNAUTHENTICATED-NOT-DENIED",
                    Severity.HIGH,
                    "unauthenticated request was not denied",
                    "require authentication before protected-resource access",
                )
            )
        elif observation.kind is AuthAuthorizationCaseKind.CROSS_TENANT and not denied:
            findings.append(
                _finding(
                    observation,
                    "AUTH-CROSS-TENANT-NOT-DENIED",
                    Severity.CRITICAL,
                    "cross-tenant request was not denied",
                    "enforce tenant binding before authorization and resource lookup",
                )
            )
        elif observation.kind is AuthAuthorizationCaseKind.INSUFFICIENT_ROLE and not denied:
            findings.append(
                _finding(
                    observation,
                    "AUTH-INSUFFICIENT-ROLE-NOT-DENIED",
                    Severity.HIGH,
                    "insufficiently privileged request was not denied",
                    "enforce the required role or permission before the protected action",
                )
            )
        elif observation.kind is AuthAuthorizationCaseKind.AUTHORIZED and not allowed:
            findings.append(
                _finding(
                    observation,
                    "AUTH-AUTHORIZED-FLOW-FAILED",
                    Severity.MEDIUM,
                    "authorized request did not complete with an allowed status",
                    "verify identity, tenant membership, permission resolution, and route policy",
                )
            )

    return SecurityReport(scope_id, tuple(findings))


def _finding(
    observation: AuthAuthorizationObservation,
    finding_id: str,
    severity: Severity,
    message: str,
    remediation: str,
) -> SecurityFinding:
    return SecurityFinding(
        finding_id=finding_id,
        category="auth-authorization",
        severity=severity,
        location=observation.location,
        line=0,
        message=f"{message}; case_id={observation.case_id}",
        remediation=remediation,
    )
