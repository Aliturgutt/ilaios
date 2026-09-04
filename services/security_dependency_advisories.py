"""Offline dependency advisory analysis for the canonical ILAIOS Security Factory.

This module never performs network access. Callers must supply the reviewed dependency
versions and advisory records from an authorized source; findings are returned through
the existing SecurityFinding/SecurityReport evidence types.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from services.security_factory import SecurityFactoryError, SecurityFinding, SecurityReport, Severity


@dataclass(frozen=True, slots=True)
class DependencyAdvisory:
    advisory_id: str
    package: str
    affected_versions: frozenset[str]
    severity: Severity
    remediation: str

    def __post_init__(self) -> None:
        if not self.advisory_id.strip():
            raise SecurityFactoryError("dependency advisory ID is required")
        if not self.package.strip():
            raise SecurityFactoryError("dependency advisory package is required")
        if not self.affected_versions:
            raise SecurityFactoryError("dependency advisory affected_versions is required")
        if any(not item.strip() for item in self.affected_versions):
            raise SecurityFactoryError("dependency advisory versions must be non-empty")
        if not self.remediation.strip():
            raise SecurityFactoryError("dependency advisory remediation is required")


def analyze_dependency_advisories(
    *,
    scope_id: str,
    installed_versions: Mapping[str, str],
    advisories: Sequence[DependencyAdvisory],
) -> SecurityReport:
    """Evaluate caller-supplied advisories against exact installed dependency versions."""
    if not scope_id.strip():
        raise SecurityFactoryError("explicit security scope ID is required")

    normalized: dict[str, tuple[str, str]] = {}
    for package, version in installed_versions.items():
        package_name = package.strip()
        package_version = version.strip()
        if not package_name or not package_version:
            raise SecurityFactoryError("dependency package and version must be non-empty")
        key = package_name.casefold()
        if key in normalized:
            raise SecurityFactoryError("duplicate dependency package after normalization")
        normalized[key] = (package_name, package_version)

    findings: list[SecurityFinding] = []
    seen_advisories: set[str] = set()
    for advisory in advisories:
        if advisory.advisory_id in seen_advisories:
            raise SecurityFactoryError("duplicate dependency advisory ID")
        seen_advisories.add(advisory.advisory_id)

        installed = normalized.get(advisory.package.casefold())
        if installed is None:
            continue
        package_name, package_version = installed
        if package_version not in advisory.affected_versions:
            continue
        findings.append(
            SecurityFinding(
                finding_id=f"SUPPLY-ADVISORY-{advisory.advisory_id}",
                category="supply-chain",
                severity=advisory.severity,
                location=f"dependency:{package_name}=={package_version}",
                line=0,
                message=(
                    f"installed dependency matches reviewed advisory {advisory.advisory_id}"
                ),
                remediation=advisory.remediation,
            )
        )

    return SecurityReport(scope_id=scope_id, findings=tuple(findings))
