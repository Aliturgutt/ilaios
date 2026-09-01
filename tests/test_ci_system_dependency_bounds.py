from __future__ import annotations

from pathlib import Path


def _workflow(name: str) -> str:
    return (
        Path(__file__).resolve().parents[1] / ".github" / "workflows" / name
    ).read_text(encoding="utf-8")


def test_platform_ci_system_dependency_install_is_bounded() -> None:
    text = _workflow("platform-ci.yml")

    assert "timeout-minutes: 30" in text
    assert "/etc/apt/apt-mirrors.txt" in text
    assert "https://archive.ubuntu.com/ubuntu/" in text
    assert "Acquire::Retries=3" in text
    assert "Acquire::http::Timeout=15" in text
    assert "Acquire::https::Timeout=15" in text
    assert "sudo timeout 180s apt-get" in text
    assert "sudo timeout 600s env DEBIAN_FRONTEND=noninteractive apt-get" in text
    assert "ffmpeg -version" in text
    assert "ffprobe -version" in text
    assert "python -m ruff check ." in text
    assert "python -m mypy --strict services src tests" in text


def test_malware_scan_dependency_install_and_signature_refresh_are_bounded() -> None:
    text = _workflow("malware-scan.yml")

    assert "/etc/apt/apt-mirrors.txt" in text
    assert "https://archive.ubuntu.com/ubuntu/" in text
    assert "Acquire::Retries=3" in text
    assert "Acquire::http::Timeout=15" in text
    assert "Acquire::https::Timeout=15" in text
    assert "sudo timeout 180s apt-get" in text
    assert "sudo timeout 240s env DEBIAN_FRONTEND=noninteractive apt-get" in text
    assert "for attempt in 1 2 3" in text
    assert "sudo timeout 90s freshclam --stdout" in text
    assert "ClamAV signature refresh failed after bounded retries" in text
    assert "clamscan --recursive --infected --no-summary" in text
    assert "ILAIOS_REPOSITORY_MALWARE_SCAN=PASS" in text
