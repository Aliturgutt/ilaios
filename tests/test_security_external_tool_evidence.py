from __future__ import annotations

import json
from pathlib import Path

import pytest

from services.security_external_tool_evidence import ExternalSecurityEvidenceError, report_from_external_tool, retest_external_tool


def _write(path: Path, value: object) -> Path:
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def test_semgrep_and_trivy_evidence_become_canonical_blocking_findings(tmp_path: Path) -> None:
    semgrep = _write(tmp_path / "semgrep.json", {"results": [{"check_id": "python.lang.security.audit.eval-detected", "path": "unsafe.py", "start": {"line": 4}, "extra": {"severity": "ERROR", "message": "unsafe eval"}}]})
    trivy = _write(tmp_path / "trivy.json", {"Results": [{"Target": "package-lock.json", "Vulnerabilities": [{"VulnerabilityID": "CVE-2099-0001", "Severity": "CRITICAL", "PkgName": "demo", "FixedVersion": "2.0.0", "Title": "critical demo vulnerability"}]}]})

    semgrep_report = report_from_external_tool(scope_id="external-exercise", tool="semgrep", evidence_path=semgrep)
    trivy_report = report_from_external_tool(scope_id="external-exercise", tool="trivy", evidence_path=trivy)

    assert semgrep_report.passed is False
    assert semgrep_report.findings[0].finding_id.startswith("SEMGREP-")
    assert trivy_report.passed is False
    assert trivy_report.findings[0].finding_id == "TRIVY-CVE-2099-0001"


def test_nuclei_zap_and_retest_are_evidence_bound(tmp_path: Path) -> None:
    nuclei = tmp_path / "nuclei.jsonl"
    nuclei.write_text(json.dumps({"template-id": "demo-cve", "matched-at": "http://127.0.0.1:3000", "info": {"name": "demo", "severity": "high"}}) + "\n", encoding="utf-8")
    zap = _write(tmp_path / "zap.json", {"site": [{"@name": "http://127.0.0.1:3000", "alerts": [{"pluginid": "10001", "riskcode": "3", "alert": "demo high", "solution": "fix demo", "instances": [{"uri": "http://127.0.0.1:3000/"}]}]}]})

    before = report_from_external_tool(scope_id="external-exercise", tool="nuclei", evidence_path=nuclei)
    zap_report = report_from_external_tool(scope_id="external-exercise", tool="zap", evidence_path=zap)
    nuclei.write_text("", encoding="utf-8")
    after = report_from_external_tool(scope_id="external-exercise", tool="nuclei", evidence_path=nuclei)

    assert before.passed is False
    assert zap_report.passed is False
    assert retest_external_tool(before=before, after=after).passed is True


def test_external_evidence_fails_closed_for_unknown_tool_or_missing_file(tmp_path: Path) -> None:
    evidence = _write(tmp_path / "evidence.json", {})
    with pytest.raises(ExternalSecurityEvidenceError, match="not allowlisted"):
        report_from_external_tool(scope_id="scope", tool="unknown", evidence_path=evidence)
    with pytest.raises(ExternalSecurityEvidenceError, match="file is required"):
        report_from_external_tool(scope_id="scope", tool="semgrep", evidence_path=tmp_path / "missing.json")
