from pathlib import Path


def test_video_provider_certification_push_trigger_is_managed_bounded_only() -> None:
    workflow = Path(
        ".github/workflows/video-provider-production-certification.yml"
    ).read_text(encoding="utf-8")

    assert "push:" in workflow
    assert "- master" in workflow
    assert ".github/video-provider-production-certification.trigger" in workflow
    assert (
        "CERT_PROOF_MODE: ${{ github.event_name == 'push' && 'managed-bounded' || inputs.proof_mode }}"
        in workflow
    )
    assert 'VIDEO_PROVIDER_MAX_TOTAL_COST_USD: "1.00"' in workflow
    assert "if: ${{ env.CERT_PROOF_MODE == 'managed-bounded' }}" in workflow
    assert "if: ${{ env.CERT_PROOF_MODE == 'free-only' }}" in workflow
    assert "if: ${{ env.CERT_PROOF_MODE == 'desktop-one-prompt' }}" in workflow
