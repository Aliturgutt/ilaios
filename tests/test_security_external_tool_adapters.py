from __future__ import annotations

import pytest

from services.security_external_tool_adapters import (
    SecurityExternalToolAdapterError,
    normalize_external_tool_result,
    retest_external_tool_result,
)


SHA1 = "1" * 40
SHA2 = "2" * 40


def _finding(*, severity: str = "high") -> dict[str, object]:
    return {
        "id": "TEST-1",
        "severity": severity,
        "location": "fixture.py",
        "line": 7,
        "message": "validated test finding",
        "remediation": "remove the unsafe fixture",
    }


def test_allows_only_zap_nuclei_semgrep_trivy() -> None:
    for tool in ("zap", "nuclei", "semgrep", "trivy"):
        evidence = normalize_external_tool_result(
            tool=tool,
            scope_id="security-external-tool-test",
            target="file:///workspace",
            source_sha=SHA1,
            raw_findings=(_finding(),),
        )
        assert evidence.tool == tool
        assert evidence.report.passed is False

    with pytest.raises(SecurityExternalToolAdapterError, match="not allowlisted"):
        normalize_external_tool_result(
            tool="unknown",
            scope_id="security-external-tool-test",
            target="file:///workspace",
            source_sha=SHA1,
            raw_findings=(),
        )


def test_production_target_fails_closed_but_local_and_explicit_staging_are_allowed() -> None:
    with pytest.raises(SecurityExternalToolAdapterError, match="forbidden"):
        normalize_external_tool_result(
            tool="zap",
            scope_id="security-external-tool-test",
            target="https://ilaios.com",
            source_sha=SHA1,
            raw_findings=(),
        )

    local = normalize_external_tool_result(
        tool="zap",
        scope_id="security-external-tool-test",
        target="http://127.0.0.1:8080",
        source_sha=SHA1,
        raw_findings=(),
    )
    assert local.report.passed is True

    staging = normalize_external_tool_result(
        tool="nuclei",
        scope_id="security-external-tool-test",
        target="https://staging.example.test",
        source_sha=SHA1,
        raw_findings=(),
        allow_staging_hosts=frozenset({"staging.example.test"}),
    )
    assert staging.report.passed is True


def test_external_tool_retest_requires_same_scope_tool_target_and_new_sha() -> None:
    before = normalize_external_tool_result(
        tool="semgrep",
        scope_id="security-external-tool-test",
        target="file:///workspace",
        source_sha=SHA1,
        raw_findings=(_finding(),),
    )
    after = normalize_external_tool_result(
        tool="semgrep",
        scope_id="security-external-tool-test",
        target="file:///workspace",
        source_sha=SHA2,
        raw_findings=(),
    )

    result = retest_external_tool_result(before, after)
    assert result.passed is True
    assert result.resolved
    assert not result.remaining
    assert not result.introduced

    with pytest.raises(SecurityExternalToolAdapterError, match="source SHA must advance"):
        retest_external_tool_result(before, before)
