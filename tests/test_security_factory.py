from __future__ import annotations

from pathlib import Path

import pytest

from services.security_factory import (
    SecurityFactory,
    SecurityFactoryError,
    SecurityReport,
    SecurityScope,
    Severity,
)


def _scope(root: Path) -> SecurityScope:
    return SecurityScope("security-test-scope", root)


def test_scope_fails_closed_for_external_network_or_missing_root(tmp_path: Path) -> None:
    with pytest.raises(SecurityFactoryError, match="external-network"):
        SecurityScope("scope", tmp_path, external_network_allowed=True)
    with pytest.raises(SecurityFactoryError, match="must exist"):
        SecurityScope("scope", tmp_path / "missing")


def test_repository_scan_detects_blocking_and_supply_chain_findings(tmp_path: Path) -> None:
    (tmp_path / "unsafe.py").write_text(
        "import subprocess\n"
        "eval('1 + 1')\n"
        "subprocess.run('echo test', shell=True)\n",
        encoding="utf-8",
    )
    (tmp_path / "infra.yaml").write_text(
        "cidr: 0.0.0.0/0\nAction: \"*\"\n",
        encoding="utf-8",
    )
    (tmp_path / "requirements.txt").write_text(
        "requests\npytest==9.1.1\n",
        encoding="utf-8",
    )
    (tmp_path / "fixture.txt").write_text(
        "-----BEGIN PRIVATE KEY-----\n",
        encoding="utf-8",
    )

    report = SecurityFactory().scan_repository(_scope(tmp_path))
    ids = {item.finding_id for item in report.findings}

    assert {
        "SAST-EVAL",
        "SAST-SHELL-TRUE",
        "INFRA-PUBLIC-CIDR",
        "INFRA-WILDCARD-ACTION",
        "SUPPLY-UNPINNED-DEPENDENCY",
        "SECRET-PRIVATE-KEY",
    } <= ids
    assert report.passed is False
    assert all(item.severity >= Severity.HIGH for item in report.blocking_findings)


def test_pyproject_dependency_scan_detects_unpinned_dependency(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\ndependencies = [\n  "requests",\n  "pytest==9.1.1",\n]\n',
        encoding="utf-8",
    )
    report = SecurityFactory().scan_repository(_scope(tmp_path))
    supply = [
        item
        for item in report.findings
        if item.finding_id == "SUPPLY-UNPINNED-DEPENDENCY"
    ]
    assert len(supply) == 1
    assert "requests" in supply[0].message


def test_dast_observation_is_local_only_and_non_destructive(tmp_path: Path) -> None:
    factory = SecurityFactory()
    scope = _scope(tmp_path)

    with pytest.raises(SecurityFactoryError, match="outside authorized local scope"):
        factory.analyze_dast_observation(
            scope,
            "https://example.com",
            200,
            {},
        )

    report = factory.analyze_dast_observation(
        scope,
        "http://127.0.0.1:8080/health",
        200,
        {},
    )
    assert report.passed is True
    assert {item.category for item in report.findings} == {"dast"}
    assert len(report.findings) == 3

    clean = factory.analyze_dast_observation(
        scope,
        "http://localhost:8080/health",
        200,
        {
            "Content-Security-Policy": "default-src 'none'",
            "X-Content-Type-Options": "nosniff",
            "Referrer-Policy": "no-referrer",
        },
    )
    assert clean == SecurityReport(scope.scope_id, ())


def test_https_dast_requires_hsts(tmp_path: Path) -> None:
    report = SecurityFactory().analyze_dast_observation(
        _scope(tmp_path),
        "https://localhost/",
        200,
        {
            "Content-Security-Policy": "default-src 'none'",
            "X-Content-Type-Options": "nosniff",
            "Referrer-Policy": "no-referrer",
        },
    )
    assert [item.finding_id for item in report.findings] == ["DAST-MISSING-HSTS"]


def test_independent_verifier_cannot_equal_producer(tmp_path: Path) -> None:
    report = SecurityFactory().scan_repository(_scope(tmp_path))
    with pytest.raises(SecurityFactoryError, match="cannot verify its own report"):
        SecurityFactory.independently_verify(
            report,
            producer_id="ilaios.agent.security.codesec.v1",
            verifier_id="ilaios.agent.security.codesec.v1",
        )
    assert SecurityFactory.independently_verify(
        report,
        producer_id="ilaios.agent.security.codesec.v1",
        verifier_id="ilaios.agent.security.verifier.v1",
    )


def test_retest_requires_blocking_findings_to_be_removed(tmp_path: Path) -> None:
    unsafe = tmp_path / "unsafe.py"
    unsafe.write_text("eval('1')\n", encoding="utf-8")
    factory = SecurityFactory()
    scope = _scope(tmp_path)
    before = factory.scan_repository(scope)
    assert before.passed is False

    unsafe.write_text("value = 1\n", encoding="utf-8")
    after = factory.scan_repository(scope)
    result = factory.retest(before, after)

    assert result.passed is True
    assert result.resolved
    assert not result.remaining
    assert not result.introduced
