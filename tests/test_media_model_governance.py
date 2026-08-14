from __future__ import annotations

import pytest

from src.media_model_governance import (
    CommercialCompatibility,
    MediaModelManifest,
    ModelEligibility,
    ModelGovernanceError,
    NativeWorkerHardware,
    NativeWorkloadRequirements,
    evaluate_native_worker,
    h3_watchlist_candidate,
    ltx2_review_candidate,
    promote_to_approved_native,
    wan22_ti2v_5b_candidate,
)


def test_wan_candidate_remains_review_required_without_checkpoint_evidence() -> None:
    candidate = wan22_ti2v_5b_candidate()

    assert candidate.eligibility is ModelEligibility.REVIEW_REQUIRED
    assert candidate.commercial_compatibility is CommercialCompatibility.VERIFIED_COMPATIBLE
    assert candidate.source_revision == "42bf4cfaa384bc21833865abc2f9e6c0e67233dc"
    assert candidate.checkpoint_revision is None
    assert candidate.checkpoint_digest_sha256 is None
    assert candidate.security_review_ref is None


def test_watchlist_and_review_candidates_are_not_native_approved() -> None:
    assert h3_watchlist_candidate().eligibility is ModelEligibility.WATCHLIST
    assert ltx2_review_candidate().eligibility is ModelEligibility.REVIEW_REQUIRED


def test_native_promotion_requires_valid_exact_checkpoint_digest() -> None:
    candidate = wan22_ti2v_5b_candidate()

    with pytest.raises(ModelGovernanceError, match="SHA-256"):
        promote_to_approved_native(
            candidate,
            checkpoint_revision="checkpoint-rev-001",
            checkpoint_digest_sha256="not-a-digest",
            security_review_ref="evidence://security/wan22-001",
        )


def test_native_promotion_rejects_unverified_commercial_compatibility() -> None:
    candidate = MediaModelManifest(
        publisher="Example",
        model_id="example/model",
        official_source="https://example.invalid/model",
        source_revision="a" * 40,
        checkpoint_revision=None,
        checkpoint_digest_sha256=None,
        model_card_url="https://example.invalid/model-card",
        license_identifier="custom",
        license_evidence_url="https://example.invalid/license",
        commercial_compatibility=CommercialCompatibility.REVIEW_REQUIRED,
        notice_obligations=(),
        runtime_requirements=(),
        minimum_vram_gb=None,
        minimum_ram_gb=None,
        security_review_ref=None,
        eligibility=ModelEligibility.REVIEW_REQUIRED,
    )

    with pytest.raises(ModelGovernanceError, match="commercial compatibility"):
        promote_to_approved_native(
            candidate,
            checkpoint_revision="checkpoint-rev-001",
            checkpoint_digest_sha256="b" * 64,
            security_review_ref="evidence://security/example-001",
        )


def test_generic_four_gb_worker_is_blocked_for_heavier_workload() -> None:
    worker = NativeWorkerHardware(
        worker_id="worker-low-vram",
        gpu_name="test-gpu-4gb",
        vram_gb=4,
        ram_gb=16,
        cuda_available=True,
        healthy=True,
        free_vram_gb=4,
    )
    requirements = NativeWorkloadRequirements(required_vram_gb=8, required_ram_gb=16)

    decision = evaluate_native_worker(worker, requirements)

    assert not decision.eligible
    assert "total VRAM is below workload requirement" in decision.reasons
    assert "free VRAM is below workload requirement" in decision.reasons


def test_worker_health_and_capacity_are_fail_closed() -> None:
    worker = NativeWorkerHardware(
        worker_id="worker-unhealthy",
        gpu_name="test-gpu",
        vram_gb=24,
        ram_gb=64,
        cuda_available=False,
        healthy=False,
        free_vram_gb=3,
    )
    requirements = NativeWorkloadRequirements(required_vram_gb=12, required_ram_gb=32)

    decision = evaluate_native_worker(worker, requirements)

    assert not decision.eligible
    assert decision.reasons == (
        "worker is unhealthy",
        "CUDA is unavailable",
        "free VRAM is below workload requirement",
    )
