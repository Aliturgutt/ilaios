from pathlib import Path


def test_video_provider_certification_push_trigger_is_desktop_managed_bounded_only() -> None:
    workflow = Path(
        ".github/workflows/video-provider-production-certification.yml"
    ).read_text(encoding="utf-8")

    assert "push:" in workflow
    assert "- master" in workflow
    assert ".github/video-provider-production-certification.trigger" in workflow
    assert (
        "CERT_PROOF_MODE: ${{ github.event_name == 'push' && 'desktop-managed-bounded' || inputs.proof_mode }}"
        in workflow
    )
    assert 'ILAIOS_VIDEO_MANAGED_E2E_MAX_TOTAL_USD: "1.00"' in workflow
    assert "if: ${{ env.CERT_PROOF_MODE == 'desktop-managed-bounded' }}" in workflow
    assert "python apps/desktop/e2e/provider_video_managed_finished_product_e2e.py" in workflow
    assert "statuses: write" in workflow
    assert "ILAIOS Video Provider Production Certification" in workflow


def test_video_provider_certification_status_requires_exact_evidence_contract() -> None:
    workflow = Path(
        ".github/workflows/video-provider-production-certification.yml"
    ).read_text(encoding="utf-8")

    required_fragments = (
        'receipt.get("revision_sha") == os.environ["GITHUB_SHA"]',
        'receipt.get("execution_status") == "ACCEPTED"',
        'receipt.get("provider_cost_mode") == "managed-bounded"',
        'receipt.get("provider_cost_proven") is True',
        "hard_cap == 1_000_000",
        "0 <= provider_cost <= hard_cap",
        'receipt.get("provider_cost_hard_cap_usd") == "1.00"',
        'is_sha256(receipt.get("artifact_sha256"))',
        'receipt.get("artifact_bytes", 0) > 100_000',
        '7.0 <= float(receipt.get("duration_seconds")) <= 9.0',
        'receipt.get("width") == 1920',
        'receipt.get("height") == 1080',
        'receipt.get("video_codec") == "h264"',
        'receipt.get("audio_codec") == "aac"',
        'float(semantic_score) >= float(semantic_threshold)',
        'receipt.get("generated_shot_count") == 2',
        'receipt.get("generation_mode") == "provider-backed-cinematic-video"',
    )
    for fragment in required_fragments:
        assert fragment in workflow
