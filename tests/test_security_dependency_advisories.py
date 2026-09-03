from __future__ import annotations

import pytest

from services.security_dependency_advisories import (
    DependencyAdvisory,
    analyze_dependency_advisories,
)
from services.security_factory import SecurityFactoryError, Severity


def test_dependency_advisory_blocks_exact_affected_version() -> None:
    report = analyze_dependency_advisories(
        scope_id="security-cve-fixture",
        installed_versions={"ExamplePkg": "1.2.3"},
        advisories=(
            DependencyAdvisory(
                advisory_id="GHSA-test-0001",
                package="examplepkg",
                affected_versions=frozenset({"1.2.3"}),
                severity=Severity.HIGH,
                remediation="upgrade to a reviewed non-affected version",
            ),
        ),
    )

    assert report.passed is False
    assert len(report.blocking_findings) == 1
    finding = report.blocking_findings[0]
    assert finding.finding_id == "SUPPLY-ADVISORY-GHSA-test-0001"
    assert finding.location == "dependency:ExamplePkg==1.2.3"
    assert finding.category == "supply-chain"


def test_dependency_advisory_does_not_flag_unaffected_or_absent_packages() -> None:
    report = analyze_dependency_advisories(
        scope_id="security-cve-fixture",
        installed_versions={"examplepkg": "2.0.0"},
        advisories=(
            DependencyAdvisory(
                advisory_id="CVE-2099-0001",
                package="examplepkg",
                affected_versions=frozenset({"1.2.3"}),
                severity=Severity.CRITICAL,
                remediation="upgrade",
            ),
            DependencyAdvisory(
                advisory_id="CVE-2099-0002",
                package="not-installed",
                affected_versions=frozenset({"9.9.9"}),
                severity=Severity.HIGH,
                remediation="upgrade",
            ),
        ),
    )

    assert report.passed is True
    assert report.findings == ()


def test_dependency_advisory_input_fails_closed() -> None:
    with pytest.raises(SecurityFactoryError, match="affected_versions"):
        DependencyAdvisory(
            advisory_id="CVE-2099-0003",
            package="examplepkg",
            affected_versions=frozenset(),
            severity=Severity.HIGH,
            remediation="upgrade",
        )

    with pytest.raises(SecurityFactoryError, match="duplicate dependency package"):
        analyze_dependency_advisories(
            scope_id="security-cve-fixture",
            installed_versions={"ExamplePkg": "1.0.0", "examplepkg": "1.0.0"},
            advisories=(),
        )
