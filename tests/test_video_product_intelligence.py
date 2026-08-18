from __future__ import annotations

import pytest

from services.integrations.video_product_intelligence import (
    VideoProductIntentError,
    VideoProductMode,
    derive_video_product_spec,
    validate_video_product_inputs,
)


def test_reference_images_promote_reference_to_video_mode() -> None:
    spec = derive_video_product_spec(
        "Create a premium cinematic product launch video.",
        reference_count=3,
    )
    assert spec.mode is VideoProductMode.REFERENCE_TO_VIDEO
    assert spec.reference_count == 3
    assert "video.reference" in spec.required_capabilities
    assert spec.source_video_required is False


def test_series_intent_keeps_canonical_series_continuity_requirement() -> None:
    spec = derive_video_product_spec(
        "Create episode 4 of the existing cinematic series.",
        reference_count=2,
    )
    assert spec.mode is VideoProductMode.SERIES
    assert spec.series_continuity_required is True
    assert spec.continuity_policy == "canonical-series-state-required"
    assert "video.series-continuity" in spec.required_capabilities
    assert "video.reference" in spec.required_capabilities


def test_revision_never_degrades_to_new_generation_without_source_video() -> None:
    spec = derive_video_product_spec(
        "Revise the existing video and make the final scene shorter.",
        reference_count=1,
    )
    assert spec.mode is VideoProductMode.REVISION
    with pytest.raises(VideoProductIntentError, match="requires an authenticated source video"):
        validate_video_product_inputs(spec, source_video_present=False)


def test_localization_never_degrades_to_new_generation_without_source_video() -> None:
    spec = derive_video_product_spec("Dub the existing video into Turkish.")
    assert spec.mode is VideoProductMode.LOCALIZATION
    assert "video.localize" in spec.required_capabilities
    with pytest.raises(VideoProductIntentError, match="source video"):
        validate_video_product_inputs(spec, source_video_present=False)


def test_aspect_ratio_resolution_is_bounded_and_explicit() -> None:
    assert derive_video_product_spec("Create a vertical TikTok video.").aspect_ratio == "9:16"
    assert derive_video_product_spec("Create a square campaign video.").aspect_ratio == "1:1"
    assert derive_video_product_spec("Create a cinematic launch video.").aspect_ratio == "16:9"


def test_reference_count_and_input_bounds_fail_closed() -> None:
    with pytest.raises(VideoProductIntentError, match="reference count"):
        derive_video_product_spec("Create a video.", reference_count=21)
    with pytest.raises(VideoProductIntentError, match="normalized"):
        derive_video_product_spec(" Create a video. ")
