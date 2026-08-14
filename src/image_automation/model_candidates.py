"""Image model candidates with fail-closed promotion state.

Licenses below reflect the referenced official project/model sources, but mutable
source revision, checkpoint, security, and measured hardware evidence remain runtime
promotion inputs. Therefore these candidates are not APPROVED_NATIVE here.
"""

from __future__ import annotations

from src.media_model_governance import (
    CommercialCompatibility,
    MediaModelManifest,
    ModelEligibility,
)


FLUX1_SCHNELL_PUBLISHED_SHA256 = (
    "9403429e0052277ac2a87ad800adece5481eecefd9ed334e1f348723621d2a0a"
)


def flux1_schnell_candidate() -> MediaModelManifest:
    return MediaModelManifest(
        publisher="Black Forest Labs",
        model_id="black-forest-labs/FLUX.1-schnell",
        official_source="https://github.com/black-forest-labs/flux",
        source_revision=None,
        checkpoint_revision=None,
        checkpoint_digest_sha256=FLUX1_SCHNELL_PUBLISHED_SHA256,
        model_card_url=(
            "https://github.com/black-forest-labs/flux/blob/main/model_cards/"
            "FLUX.1-schnell.md"
        ),
        license_identifier="Apache-2.0",
        license_evidence_url="https://github.com/black-forest-labs/flux",
        commercial_compatibility=CommercialCompatibility.VERIFIED_COMPATIBLE,
        notice_obligations=("retain Apache-2.0 notices when redistribution applies",),
        runtime_requirements=(),
        minimum_vram_gb=None,
        minimum_ram_gb=None,
        security_review_ref=None,
        eligibility=ModelEligibility.REVIEW_REQUIRED,
    )


def qwen_image_candidate() -> MediaModelManifest:
    return MediaModelManifest(
        publisher="Qwen / Alibaba Cloud",
        model_id="Qwen/Qwen-Image",
        official_source="https://github.com/QwenLM/Qwen-Image",
        source_revision=None,
        checkpoint_revision=None,
        checkpoint_digest_sha256=None,
        model_card_url="https://huggingface.co/Qwen/Qwen-Image",
        license_identifier="Apache-2.0",
        license_evidence_url="https://github.com/QwenLM/Qwen-Image/blob/main/LICENSE",
        commercial_compatibility=CommercialCompatibility.VERIFIED_COMPATIBLE,
        notice_obligations=("retain Apache-2.0 notices when redistribution applies",),
        runtime_requirements=(),
        minimum_vram_gb=None,
        minimum_ram_gb=None,
        security_review_ref=None,
        eligibility=ModelEligibility.REVIEW_REQUIRED,
    )
