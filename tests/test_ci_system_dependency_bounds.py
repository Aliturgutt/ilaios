from __future__ import annotations

from pathlib import Path


def _workflow(name: str) -> str:
    return (
        Path(__file__).resolve().parents[1] / ".github" / "workflows" / name
    ).read_text(encoding="utf-8")


def test_platform_ci_system_dependency_install_is_bounded() -> None:
    text = _workflow("platform-ci.yml")

    assert "if ! command -v ffmpeg" in text
    assert "https://archive.ubuntu.com/ubuntu" in text
    assert "Acquire::Retries=3" in text
    assert "Acquire::ForceIPv4=true" in text
    assert "Acquire::http::Timeout=15" in text
    assert "Acquire::https::Timeout=15" in text
    assert "Acquire::Languages=none" in text
    assert "sudo timeout 180 apt-get" in text
    assert "ffmpeg -version" in text
    assert "ffprobe -version" in text


def test_malware_scan_dependency_install_and_signature_refresh_are_bounded() -> None:
    text = _workflow("malware-scan.yml")

    assert "https://archive.ubuntu.com/ubuntu" in text
    assert "Acquire::Retries=3" in text
    assert "Acquire::ForceIPv4=true" in text
    assert "Acquire::http::Timeout=15" in text
    assert "Acquire::https::Timeout=15" in text
    assert "Acquire::Languages=none" in text
    assert text.count("sudo timeout 180 apt-get") == 2
    assert "sudo timeout 180 freshclam --stdout" in text
    assert "clamscan --recursive --infected --no-summary" in text
    assert "ILAIOS_REPOSITORY_MALWARE_SCAN=PASS" in text
