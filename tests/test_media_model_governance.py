from __future__ import annotations

from dataclasses import replace

import pytest

from src.media_model_governance import (
    CommercialCompatibility,
    MediaModelManifest,
    ModelEligibility,
    ModelGovernanceError,
    promote_to_approved_native,
)


def _candidate() -> MediaModelManifest:
    return MediaModelManifest(
        publisher="Example Publisher",
        model_id="example/native-video-v1",
        official_source="https://example.invalid/official-model",
        source_revision="source-revision-001",
        checkpoint_revision=None,
        checkpoint_digest_sha256=None,
        model_card_url="https://example.invalid/model-card",
        license_identifier="Apache-2.0",
        license_evidence_url="https://example.invalid/license",
        commercial_compatibility=CommercialCompatibility.VERIFIED_COMPATIBLE,
        notice_obligations=("retain license notice",),
        runtime_requirements=("CUDA-compatible accelerator",),
        minimum_vram_gb=None,
        minimum_ram_gb=None,
        security_review_ref=None,
        eligibility=ModelEligibility.REVIEW_REQUIRED,
    )


def test_native_promotion_requires_exact_checkpoint_security_and_hardware_evidence() -> None:
    promoted = promote_to_approved_native(
        _candidate(),
        checkpoint_revision="checkpoint-revision-001",
        checkpoint_digest_sha256="a" * 64,
        security_review_ref="evidence://security/native-video-v1",
        minimum_vram_gb=24,
        minimum_ram_gb=64,
    )

    assert promoted.eligibility is ModelEligibility.APPROVED_NATIVE
    assert promoted.checkpoint_digest_sha256 == "a" * 64
    assert promoted.minimum_vram_gb == 24
    assert promoted.minimum_ram_gb == 64


def test_native_promotion_rejects_unverified_commercial_compatibility() -> None:
    candidate = replace(
        _candidate(),
        commercial_compatibility=CommercialCompatibility.REVIEW_REQUIRED,
    )
    with pytest.raises(ModelGovernanceError, match="commercial compatibility"):
        promote_to_approved_native(
            candidate,
            checkpoint_revision="checkpoint-revision-001",
            checkpoint_digest_sha256="b" * 64,
            security_review_ref="evidence://security/review",
            minimum_vram_gb=24,
            minimum_ram_gb=64,
        )


def test_native_promotion_rejects_invalid_digest() -> None:
    with pytest.raises(ModelGovernanceError, match="SHA-256"):
        promote_to_approved_native(
            _candidate(),
            checkpoint_revision="checkpoint-revision-001",
            checkpoint_digest_sha256="not-a-digest",
            security_review_ref="evidence://security/native-video-v1",
            minimum_vram_gb=24,
            minimum_ram_gb=64,
        )
