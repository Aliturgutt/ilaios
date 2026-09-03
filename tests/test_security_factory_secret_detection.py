from __future__ import annotations

from pathlib import Path

from services.security_factory import SecurityFactory, SecurityScope, Severity


def _scope(root: Path) -> SecurityScope:
    return SecurityScope("secret-detection-test-scope", root)


def test_secret_detection_flags_aws_access_key_and_private_key(tmp_path: Path) -> None:
    aws_key = "AKIA" + ("A" * 16)
    private_key_marker = "-----BEGIN " + "PRIVATE KEY-----"
    (tmp_path / "secrets.txt").write_text(
        f"AWS_ACCESS_KEY_ID={aws_key}\n{private_key_marker}\n",
        encoding="utf-8",
    )

    report = SecurityFactory().scan_repository(_scope(tmp_path))
    findings = {item.finding_id: item for item in report.findings}

    assert findings["SECRET-AWS-ACCESS-KEY"].severity is Severity.CRITICAL
    assert findings["SECRET-PRIVATE-KEY"].severity is Severity.CRITICAL
    assert report.passed is False


def test_secret_detection_does_not_flag_non_secret_lookalikes(tmp_path: Path) -> None:
    (tmp_path / "safe.txt").write_text(
        "AKIA-too-short\n-----BEGIN PUBLIC KEY-----\n",
        encoding="utf-8",
    )

    report = SecurityFactory().scan_repository(_scope(tmp_path))
    ids = {item.finding_id for item in report.findings}

    assert "SECRET-AWS-ACCESS-KEY" not in ids
    assert "SECRET-PRIVATE-KEY" not in ids
