"""Native-first Image Factory model candidates with fail-closed promotion state."""

from __future__ import annotations

from src.media_model_governance import (
    CommercialCompatibility,
    MediaModelManifest,
    ModelEligibility,
)

FLUX1_SOURCE_REVISION = "802fb4713906133fcbd0d8dc5351620ca4773036"
QWEN_IMAGE_SOURCE_REVISION = "6b5e1f5cec987d404be5ac6657db3b9aacb56a89"


def flux1_schnell_candidate() -> MediaModelManifest:
    """Primary native image candidate; exact runtime checkpoint evidence is pending."""

    return MediaModelManifest(
        publisher="Black Forest Labs",
        model_id="black-forest-labs/FLUX.1-schnell",
        official_source="https://github.com/black-forest-labs/flux",
        source_revision=FLUX1_SOURCE_REVISION,
        checkpoint_revision=None,
        checkpoint_digest_sha256=None,
        model_card_url="https://huggingface.co/black-forest-labs/FLUX.1-schnell",
        license_identifier="Apache-2.0",
        license_evidence_url="https://github.com/black-forest-labs/flux",
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
        official_source="https://github.com/QwenLM/Qwen-Image",
        source_revision=QWEN_IMAGE_SOURCE_REVISION,
        checkpoint_revision=None,
        checkpoint_digest_sha256=None,
        model_card_url="https://huggingface.co/Qwen/Qwen-Image",
        license_identifier="Apache-2.0",
        license_evidence_url="https://github.com/QwenLM/Qwen-Image/blob/main/LICENSE",
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
