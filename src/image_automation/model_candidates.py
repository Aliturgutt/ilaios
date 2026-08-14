"""Native-first Image Factory model candidates with fail-closed promotion state."""

from __future__ import annotations

from src.media_model_governance import (
    CommercialCompatibility,
    MediaModelManifest,
    ModelEligibility,
)


def flux1_schnell_candidate() -> MediaModelManifest:
    """Primary native image candidate; exact runtime checkpoint evidence is pending."""

    return MediaModelManifest(
        publisher="Black Forest Labs",
        model_id="black-forest-labs/FLUX.1-schnell",
        official_source="https://huggingface.co/black-forest-labs/FLUX.1-schnell",
        source_revision=None,
        checkpoint_revision=None,
        checkpoint_digest_sha256=None,
        model_card_url="https://huggingface.co/black-forest-labs/FLUX.1-schnell",
        license_identifier="Apache-2.0",
        license_evidence_url="https://huggingface.co/black-forest-labs/FLUX.1-schnell",
        commercial_compatibility=CommercialCompatibility.VERIFIED_COMPATIBLE,
        notice_obligations=("retain applicable Apache-2.0 notices",),
        runtime_requirements=(
            "governed checkpoint storage outside Git",
            "exact checkpoint revision and digest evidence",
            "security review before native production dispatch",
            "measured hardware benchmark before native production dispatch",
        ),
        minimum_vram_gb=None,
        minimum_ram_gb=None,
        security_review_ref=None,
        eligibility=ModelEligibility.REVIEW_REQUIRED,
    )


def qwen_image_candidate() -> MediaModelManifest:
    """Secondary native image candidate pending exact checkpoint/runtime evidence."""

    return MediaModelManifest(
        publisher="Qwen",
        model_id="Qwen/Qwen-Image",
        official_source="https://huggingface.co/Qwen/Qwen-Image",
        source_revision=None,
        checkpoint_revision=None,
        checkpoint_digest_sha256=None,
        model_card_url="https://huggingface.co/Qwen/Qwen-Image",
        license_identifier="Apache-2.0",
        license_evidence_url="https://huggingface.co/Qwen/Qwen-Image",
        commercial_compatibility=CommercialCompatibility.VERIFIED_COMPATIBLE,
        notice_obligations=("retain applicable Apache-2.0 notices",),
        runtime_requirements=(
            "governed checkpoint storage outside Git",
            "exact checkpoint revision and digest evidence",
            "security review before native production dispatch",
            "measured hardware benchmark before native production dispatch",
        ),
        minimum_vram_gb=None,
        minimum_ram_gb=None,
        security_review_ref=None,
        eligibility=ModelEligibility.REVIEW_REQUIRED,
    )
