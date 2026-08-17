"""Failure-mode analysis for ILAIOS system-design artifacts."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FailureScenario:
    component: str
    failure_mode: str
    critical: bool
    redundant: bool
    detection_defined: bool
    recovery_defined: bool
    bounded_retry: bool | None = None
    blast_radius: str = "unknown"


@dataclass(frozen=True, slots=True)
class FailureFinding:
    code: str
    severity: str
    component: str
    message: str
    residual_risk: str


def analyze_failures(
    scenarios: tuple[FailureScenario, ...],
) -> tuple[FailureFinding, ...]:
    """Analyze declared failures and expose missing containment/recovery controls."""

    findings: list[FailureFinding] = []
    for scenario in scenarios:
        if not scenario.component.strip() or not scenario.failure_mode.strip():
            raise ValueError("component and failure_mode must be non-empty")
        if scenario.critical and not scenario.redundant:
            findings.append(
                FailureFinding(
                    code="CRITICAL_SINGLE_POINT_OF_FAILURE",
                    severity="critical",
                    component=scenario.component,
                    message=(
                        f"Critical component has no declared redundancy for "
                        f"{scenario.failure_mode}."
                    ),
                    residual_risk="failure may become service-wide",
                )
            )
        if not scenario.detection_defined:
            findings.append(
                FailureFinding(
                    code="FAILURE_DETECTION_MISSING",
                    severity="high",
                    component=scenario.component,
                    message="No deterministic detection signal is defined.",
                    residual_risk="failure may remain latent",
                )
            )
        if not scenario.recovery_defined:
            findings.append(
                FailureFinding(
                    code="RECOVERY_PATH_MISSING",
                    severity="high",
                    component=scenario.component,
                    message="No bounded recovery path is defined.",
                    residual_risk="manual or indefinite outage",
                )
            )
        if scenario.bounded_retry is False:
            findings.append(
                FailureFinding(
                    code="UNBOUNDED_RETRY_AMPLIFICATION",
                    severity="critical",
                    component=scenario.component,
                    message="Retry behavior is explicitly unbounded.",
                    residual_risk="cascading load amplification",
                )
            )
        if scenario.blast_radius == "unknown":
            findings.append(
                FailureFinding(
                    code="BLAST_RADIUS_UNKNOWN",
                    severity="medium",
                    component=scenario.component,
                    message=(
                        "Failure-domain or tenant blast radius has not been bounded."
                    ),
                    residual_risk="impact scope cannot be proven",
                )
            )
    return tuple(findings)
