from __future__ import annotations

from pathlib import Path

from services.security_factory import SecurityFactory, SecurityScope, Severity


def _scope(root: Path) -> SecurityScope:
    return SecurityScope("security-injection-test-scope", root)


def test_repository_scan_detects_request_argument_command_injection_flow(
    tmp_path: Path,
) -> None:
    (tmp_path / "unsafe_request.py").write_text(
        "from flask import request\n"
        "import subprocess\n"
        "command = request.args.get('cmd')\n"
        "subprocess.run(command)\n",
        encoding="utf-8",
    )

    report = SecurityFactory().scan_repository(_scope(tmp_path))
    findings = [
        item
        for item in report.findings
        if item.finding_id == "SAST-TAINT-UNTRUSTED-TO-SINK"
    ]

    assert len(findings) == 1
    assert findings[0].category == "sast"
    assert findings[0].severity == Severity.HIGH
    assert findings[0].location == "unsafe_request.py"
    assert findings[0].line == 4
    assert "subprocess.run" in findings[0].message
    assert report.passed is False


def test_repository_scan_does_not_flag_constant_command_fixture(tmp_path: Path) -> None:
    (tmp_path / "safe_request.py").write_text(
        "import subprocess\n"
        "command = 'status'\n"
        "subprocess.run(command)\n",
        encoding="utf-8",
    )

    report = SecurityFactory().scan_repository(_scope(tmp_path))

    assert "SAST-TAINT-UNTRUSTED-TO-SINK" not in {
        item.finding_id for item in report.findings
    }
    assert report.passed is True
