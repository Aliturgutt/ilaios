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
    assert "7.0 <= float(receipt.get('duration_seconds')) <= 9.0" in text
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


def test_reference_provider_live_e2e_uses_supported_eight_second_contract() -> None:
    root = _repository_root()
    script = (
        root
        / "apps"
        / "desktop"
        / "e2e"
        / "provider_video_reference_finished_product_e2e.py"
    ).read_text(encoding="utf-8")

    assert "exactly 8 seconds long" in script
    assert "7.0 <= float(probe.duration_seconds) <= 9.0" in script
    assert "exactly 4 seconds long" not in script


def test_video_reference_live_status_preserves_repository_security_policy() -> None:
    root = _repository_root()
    findings = [
        finding
        for finding in audit_repository(root)
        if finding.path
        == ".github/workflows/video-reference-production-certification.yml"
    ]
    assert findings == []
