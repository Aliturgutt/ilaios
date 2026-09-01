"""SF-19 secret scanning policy tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from services.software_factory_secret_scanning import (
    ChangedLine,
    SecretScanningError,
    SoftwareFactorySecretScanning,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


def _scanner() -> SoftwareFactorySecretScanning:
    return SoftwareFactorySecretScanning()


def _github_token() -> str:
    return "gh" + "p_" + ("Ab9" * 12)


def _aws_access_key() -> str:
    return "AK" + "IA" + ("A1B2" * 4)


def test_provider_token_is_blocked_without_secret_value_in_evidence() -> None:
    secret = _github_token()
    report = _scanner().scan_lines(
        (ChangedLine("config.py", 7, f'GITHUB_TOKEN = "{secret}"'),),
        scope="REVIEWED_CHANGESET",
        base_sha="1" * 40,
        head_sha="2" * 40,
    )

    assert report.passed is False
    assert {item.finding_id for item in report.findings} >= {"SF19-GITHUB-TOKEN"}
    assert report.secret_values_emitted is False
    assert secret not in repr(report)


def test_existing_security_factory_aws_detector_is_reused() -> None:
    secret = _aws_access_key()
    report = _scanner().scan_lines(
        (ChangedLine("settings.txt", 3, secret),),
        scope="REVIEWED_CHANGESET",
    )

    assert "SECRET-AWS-ACCESS-KEY" in {
        item.finding_id for item in report.findings
    }
    assert secret not in repr(report)


def test_generic_high_entropy_credential_assignment_is_blocked() -> None:
    candidate = "A7c9D2e4F6g8H1j3K5m7N9p2Q4r6S8t0"
    report = _scanner().scan_lines(
        (ChangedLine("config.toml", 11, f'client_secret = "{candidate}"'),),
        scope="STAGED_CHANGESET",
    )

    assert "SF19-GENERIC-CREDENTIAL-ASSIGNMENT" in {
        item.finding_id for item in report.findings
    }


def test_explicit_placeholder_is_not_treated_as_a_secret() -> None:
    report = _scanner().scan_lines(
        (
            ChangedLine(
                "example.env",
                2,
                'api_key = "placeholder_replace_me_before_runtime"',
            ),
        ),
        scope="REVIEWED_CHANGESET",
    )

    assert report.passed is True
    assert report.findings == ()


def test_diff_parser_scans_only_added_lines() -> None:
    secret = _github_token()
    diff = (
        "diff --git a/config.py b/config.py\n"
        "--- a/config.py\n"
        "+++ b/config.py\n"
        "@@ -4,1 +4,2 @@\n"
        f'-TOKEN = "{secret}"\n'
        "+TOKEN = os.environ['TOKEN']\n"
        "+SAFE = True\n"
    )
    lines = _scanner().parse_added_lines(diff)
    report = _scanner().scan_lines(lines, scope="REVIEWED_CHANGESET")

    assert [(item.path, item.line) for item in lines] == [
        ("config.py", 4),
        ("config.py", 5),
    ]
    assert report.passed is True


def test_added_secret_line_is_blocked() -> None:
    secret = _github_token()
    diff = (
        "diff --git a/config.py b/config.py\n"
        "--- a/config.py\n"
        "+++ b/config.py\n"
        "@@ -0,0 +1 @@\n"
        f'+TOKEN = "{secret}"\n'
    )
    report = _scanner().scan_lines(
        _scanner().parse_added_lines(diff),
        scope="REVIEWED_CHANGESET",
    )

    assert report.passed is False
    assert report.findings[0].path == "config.py"
    assert report.findings[0].line == 1


def test_report_is_deterministic_and_grants_no_authority() -> None:
    lines = (ChangedLine("safe.py", 1, "value = 1"),)
    first = _scanner().scan_lines(
        lines,
        scope="REVIEWED_CHANGESET",
        base_sha="1" * 40,
        head_sha="2" * 40,
    )
    second = _scanner().scan_lines(
        lines,
        scope="REVIEWED_CHANGESET",
        base_sha="1" * 40,
        head_sha="2" * 40,
    )

    assert first == second
    assert first.passed is True
    assert first.acceptance_authorized is False
    assert first.promotion_authorized is False
    assert first.deployment_authorized is False
    assert first.production_applied is False
    assert first.subject_mutated is False
    assert len(first.report_sha256) == 64


def test_exact_commit_sha_is_required_before_git_diff(tmp_path: Path) -> None:
    with pytest.raises(SecretScanningError, match="exact 40-hex"):
        _scanner().scan_diff(
            tmp_path,
            base_sha="master",
            head_sha="2" * 40,
        )


def test_repository_wires_secret_scan_into_required_ci_and_precommit() -> None:
    required = (REPO_ROOT / ".github/workflows/required-ci-gate.yml").read_text(
        encoding="utf-8"
    )
    precommit = (REPO_ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8")

    assert "secret-scan:" in required
    assert "SECRET_SCAN_RESULT" in required
    assert "software_factory_secret_scanning" in required
    assert "ilaios-secret-scan" in precommit
    assert "--staged" in precommit
