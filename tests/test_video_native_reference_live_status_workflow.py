from __future__ import annotations

from pathlib import Path

from services.github_workflow_security_audit import audit_repository


def _repository_root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_native_reference_live_workflow_is_exact_sha_fail_closed() -> None:
    root = _repository_root()
    path = (
        root
        / ".github"
        / "workflows"
        / "video-native-reference-production-certification.yml"
    )
    text = path.read_text(encoding="utf-8")

    assert "  contents: read\n  statuses: write\n" in text
    assert "pull_request:" not in text
    assert "environment: Production" in text
    assert "ILAIOS_VIDEO_QA_MODEL_ID: openrouter/free" in text
    assert "ILAIOS_VIDEO_QA_MODEL_ID: google/gemma-3-27b-it:free" not in text
    assert "ref: ${{ github.sha }}" in text
    assert "ILAIOS Video Native Reference Live Certification" in text
    assert "Native reference live E2E accepted: exact-SHA PASS" in text
    assert "Native reference live E2E failed closed" in text
    assert "provider_native_reference_url_used') is True" in text
    assert "native_reference_mode')=='input-references'" in text
    assert "native_reference_relay_released') is True" in text
    assert "0<=cost<=1_000_000" in text
    assert "logo_asset_lock_repaired_artifact_sha256" in text
    assert "logo_asset_lock_source_sha256" in text
    assert "reference_consistency_passed') is True" in text
    assert "receipt.get('revision_sha')==os.environ['GITHUB_SHA']" in text
    assert "contents: write" not in text

    status_step = text.split(
        "      - name: Publish sanitized native-reference exact-SHA status\n", 1
    )[1]
    assert "ILAIOS_REFERENCE_RELAY_UPLOAD_TOKEN" not in status_step
    assert "OPENROUTER_API_KEY" not in status_step
    assert "generated_content" not in status_step
    assert "prompt" not in status_step.lower()


def test_native_reference_live_e2e_requires_real_relay_fetch_and_logo_case() -> None:
    root = _repository_root()
    script = (
        root
        / "apps"
        / "desktop"
        / "e2e"
        / "provider_video_native_reference_finished_product_e2e.py"
    ).read_text(encoding="utf-8")

    assert "ReceiptBoundNativeReferenceManagedDesktopVideoRuntime" in script
    assert "ILAIOS_REFERENCE_RELAY_UPLOAD_URL" in script
    assert "ILAIOS_REFERENCE_RELAY_UPLOAD_TOKEN" in script
    assert "provider_native_reference_url_used" in script
    assert "native_reference_mode" in script
    assert "input-references" in script
    assert "ReferenceAssetRole.PRODUCT" in script
    assert "ReferenceAssetRole.LOGO" in script
    assert "logo_asset_lock_repaired_artifact_sha256" in script
    assert "/v1/reference-relay-access/" in script
    assert "fetch_count" in script
    assert "7.0 <= float(probe.duration_seconds) <= 9.0" in script


def test_native_reference_live_workflow_preserves_repository_security_policy() -> None:
    root = _repository_root()
    findings = [
        finding
        for finding in audit_repository(root)
        if finding.path
        == ".github/workflows/video-native-reference-production-certification.yml"
    ]
    assert findings == []
