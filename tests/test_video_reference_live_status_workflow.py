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


def test_video_reference_live_status_preserves_repository_security_policy() -> None:
    root = _repository_root()
    findings = [
        finding
        for finding in audit_repository(root)
        if finding.path
        == ".github/workflows/video-reference-production-certification.yml"
    ]
    assert findings == []
