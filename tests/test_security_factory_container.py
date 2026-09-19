from __future__ import annotations

from pathlib import Path

from services.security_factory import SecurityFactory, SecurityScope


def _scope(root: Path) -> SecurityScope:
    return SecurityScope("security-container-test-scope", root)


def test_repository_scan_detects_explicit_root_container_user(tmp_path: Path) -> None:
    (tmp_path / "Dockerfile").write_text(
        "FROM python:3.13-slim\nUSER root\nCMD [\"python\", \"-V\"]\n",
        encoding="utf-8",
    )

    report = SecurityFactory().scan_repository(_scope(tmp_path))
    finding = next(
        item for item in report.findings if item.finding_id == "CONTAINER-ROOT-USER"
    )

    assert finding.category == "container"
    assert finding.line == 2
    assert report.passed is False


def test_repository_scan_accepts_explicit_non_root_container_user(tmp_path: Path) -> None:
    (tmp_path / "Dockerfile").write_text(
        "FROM python:3.13-slim\nUSER 10001:10001\nCMD [\"python\", \"-V\"]\n",
        encoding="utf-8",
    )

    report = SecurityFactory().scan_repository(_scope(tmp_path))

    assert "CONTAINER-ROOT-USER" not in {
        item.finding_id for item in report.findings
    }
