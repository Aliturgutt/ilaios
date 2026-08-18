from __future__ import annotations

from pathlib import Path

from services.github_workflow_security_audit import audit_repository


def _repository_root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_video_reference_live_workflow_publishes_sanitized_exact_sha_status() -> None:
    root = _repository_root()
    path = root / ".github" / "workflows" / "video-reference-production-certification.yml"
    text = path.read_text(encoding="utf-8")

    assert "  contents: read\n  statuses: write\n" in text
    assert "pull_request:" not in text
    assert "environment: Production" in text
    assert "ref: ${{ github.sha }}" in text
    assert "receipt.get('revision_sha') == os.environ['GITHUB_SHA']" in text
    assert "ILAIOS Video Reference Live Certification" in text
    assert "Reference live E2E accepted: exact-SHA PASS" in text
    assert "Reference live E2E failed closed" in text
    assert "VIDEO_REFERENCE_COMMIT_STATUS=" in text
    assert "/statuses/{os.environ['GITHUB_SHA']}" in text
    assert "provider_native_reference_url_used') is False" in text
    assert "reference_conditioning_mode') == 'private-multimodal-brief'" in text
    assert "contents: write" not in text

    status_step = text.split(
        "      - name: Publish sanitized live-reference commit status\n", 1
    )[1]
    assert "OPENROUTER_API_KEY" not in status_step
    assert "frozen.text" not in status_step
    assert "reference_bytes" not in status_step
    assert "generated_content" not in status_step
    assert "prompt" not in status_step.lower()
    assert "'state': state" in status_step
    assert "'target_url': os.environ['VIDEO_REFERENCE_STATUS_TARGET_URL']" in status_step
    assert "'description': description" in status_step
    assert "'context': 'ILAIOS Video Reference Live Certification'" in status_step


def test_video_reference_live_workflow_matches_current_video_duration_contract() -> None:
    root = _repository_root()
    workflow = (
        root / ".github" / "workflows" / "video-reference-production-certification.yml"
    ).read_text(encoding="utf-8")
    e2e = (
        root / "apps" / "desktop" / "e2e" / "provider_video_reference_finished_product_e2e.py"
    ).read_text(encoding="utf-8")

    assert "exactly 8 seconds long" in e2e
    assert "7.0 <= float(probe.duration_seconds) <= 9.0" in e2e
    assert 'generated_shot_count", 0)) != 2' in e2e
    assert "expected two provider terminal records" in e2e
    assert "len(generation_ids) != 2" in e2e
    assert '"provider_generation_ids": generation_ids' in e2e
    assert "exactly 4 seconds long" not in e2e
    assert "3.0 <= float(probe.duration_seconds) <= 5.0" not in e2e

    assert "7.0 <= float(receipt.get('duration_seconds')) <= 9.0" in workflow
    assert "receipt.get('generated_shot_count') == 2" in workflow
    assert "len(generation_ids) == 2" in workflow
    assert "len(set(generation_ids)) == 2" in workflow
    assert "3.0 <= float(receipt.get('duration_seconds')) <= 5.0" not in workflow


def test_video_reference_live_workflow_uses_bounded_runtime_dependency_install() -> None:
    root = _repository_root()
    text = (
        root / ".github" / "workflows" / "video-reference-production-certification.yml"
    ).read_text(encoding="utf-8")

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


def test_video_reference_live_status_preserves_repository_security_policy() -> None:
    root = _repository_root()
    findings = [
        finding
        for finding in audit_repository(root)
        if finding.path
        == ".github/workflows/video-reference-production-certification.yml"
    ]
    assert findings == []
