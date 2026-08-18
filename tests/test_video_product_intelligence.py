from __future__ import annotations

import pytest

from services.integrations.video_product_intelligence import (
    VideoProductIntentError,
    VideoProductMode,
    admit_current_desktop_video_product,
    derive_video_product_spec,
)


def test_reference_images_promote_reference_to_video_without_changing_runtime_authority() -> None:
    spec = derive_video_product_spec(
        "Create a premium cinematic product launch video.",
        reference_count=3,
    )
    assert spec.mode is VideoProductMode.REFERENCE_TO_VIDEO
    assert spec.reference_count == 3
    assert spec.source_video_required is False
    assert spec.series_state_required is False
    assert spec.aspect_ratio == "16:9"


def test_revision_cannot_degrade_to_new_generation_without_source_video() -> None:
    with pytest.raises(VideoProductIntentError, match="authenticated source video"):
        admit_current_desktop_video_product(
            "Edit this video and make the final scene shorter.",
        )


def test_bound_source_video_is_recognized_but_not_false_claimed_as_edit_execution() -> None:
    with pytest.raises(VideoProductIntentError, match="not materialized"):
        admit_current_desktop_video_product(
            "Edit this video and make the final scene shorter.",
            source_video_present=True,
        )


def test_bound_source_video_is_never_silently_ignored_by_create_mode() -> None:
    with pytest.raises(VideoProductIntentError, match="silently ignore source media"):
        admit_current_desktop_video_product(
            "Create a new cinematic launch video.",
            source_video_present=True,
        )


def test_localization_cannot_degrade_to_new_generation_without_source_video() -> None:
    with pytest.raises(VideoProductIntentError, match="authenticated source video"):
        admit_current_desktop_video_product(
            "Dub this video into Turkish.",
        )


def test_bound_source_localization_still_fails_until_real_dubbing_is_materialized() -> None:
    with pytest.raises(VideoProductIntentError, match="not materialized"):
        admit_current_desktop_video_product(
            "Dub this video into Turkish.",
            source_video_present=True,
        )


def test_episode_request_cannot_invent_series_state() -> None:
    spec = derive_video_product_spec("Create episode 4 with the same characters.")
    assert spec.mode is VideoProductMode.SERIES_CONTINUATION
    with pytest.raises(VideoProductIntentError, match="SeriesState"):
        admit_current_desktop_video_product(
            "Create episode 4 with the same characters.",
        )


def test_bound_series_state_is_not_false_claimed_as_execution() -> None:
    with pytest.raises(VideoProductIntentError, match="not materialized"):
        admit_current_desktop_video_product(
            "Create episode 4 with the same characters.",
            series_state_present=True,
        )


def test_vertical_and_square_requests_fail_before_current_16_9_materialization() -> None:
    with pytest.raises(VideoProductIntentError, match="9:16"):
        admit_current_desktop_video_product(
            "Create a vertical video for a product launch.",
        )
    with pytest.raises(VideoProductIntentError, match="1:1"):
        admit_current_desktop_video_product(
            "Create a square video for the campaign.",
        )


def test_explicit_platform_shape_is_bounded_and_truthful() -> None:
    assert derive_video_product_spec("Create a video for TikTok.").aspect_ratio == "9:16"
    assert derive_video_product_spec("Create an Instagram Reel.").aspect_ratio == "9:16"
    assert derive_video_product_spec("Create a YouTube Short.").aspect_ratio == "9:16"
    assert derive_video_product_spec("Create a cinematic 16:9 launch video.").aspect_ratio == "16:9"


def test_content_words_do_not_false_trigger_product_or_output_modes() -> None:
    editing_tutorial = derive_video_product_spec(
        "Create a cinematic video about video editing techniques."
    )
    portrait_subject = derive_video_product_spec(
        "Create a cinematic video showing a portrait of a woman in a gallery."
    )
    film_reel = derive_video_product_spec(
        "Create a cinematic video showing an old film reel on a projector."
    )
    machine_part = derive_video_product_spec(
        "Create a video explaining part 2 of the machine assembly."
    )
    assert editing_tutorial.mode is VideoProductMode.CREATE
    assert portrait_subject.aspect_ratio == "16:9"
    assert film_reel.aspect_ratio == "16:9"
    assert machine_part.mode is VideoProductMode.CREATE


def test_conflicting_output_shapes_fail_closed() -> None:
    with pytest.raises(VideoProductIntentError, match="conflicting aspect ratios"):
        derive_video_product_spec("Create a 16:9 video and also make it 9:16.")


def test_reference_count_bound_matches_current_governed_store_contract() -> None:
    assert derive_video_product_spec("Create a video.", reference_count=20).reference_count == 20
    with pytest.raises(VideoProductIntentError, match="reference count"):
        derive_video_product_spec("Create a video.", reference_count=21)
