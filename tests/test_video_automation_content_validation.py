"""Tests for canonical M22 content validation."""

from __future__ import annotations

import pytest

from src.video_automation.content_validation import (
    ContentValidationCoordinator,
    ContentValidationError,
    ContentValidationEvidence,
    ContentValidationPolicy,
)


def _policy() -> ContentValidationPolicy:
    return ContentValidationPolicy(
        expected_scene_ids=("scene-1", "scene-2"),
        required_asset_ids=("asset-video", "asset-voice"),
        required_platforms=("youtube_shorts",),
        minimum_duration_seconds=38.0,
        maximum_duration_seconds=42.0,
        required_brand_terms=("Hermes",),
    )


def _evidence() -> ContentValidationEvidence:
    return ContentValidationEvidence(
        job_id="job-1",
        scene_ids=("scene-1", "scene-2"),
        narrated_scene_ids=("scene-1", "scene-2"),
        asset_ids=("asset-video", "asset-voice"),
        caption_count=4,
        duration_seconds=40.0,
        target_platforms=("youtube_shorts",),
        cta_text="Subscribe for the next chapter.",
        brand_text="Hermes presents The Last Origin.",
    )


def test_matching_content_passes() -> None:
    result = ContentValidationCoordinator(
        _policy()
    ).validate(_evidence())

    assert result.passed is True
    assert result.issues == ()
    assert result.job_id == "job-1"


def test_missing_scene_narration_caption_asset_and_cta_fail() -> None:
    evidence = ContentValidationEvidence(
        job_id="job-1",
        scene_ids=("scene-1",),
        narrated_scene_ids=(),
        asset_ids=("asset-video",),
        caption_count=0,
        duration_seconds=40.0,
        target_platforms=("youtube_shorts",),
        cta_text=None,
        brand_text="Hermes",
    )

    result = ContentValidationCoordinator(
        _policy()
    ).validate(evidence)

    codes = tuple(issue.code for issue in result.issues)

    assert result.passed is False
    assert "expected_scene_missing" in codes
    assert "narration_scene_missing" in codes
    assert "captions_missing" in codes
    assert "required_asset_missing" in codes
    assert "cta_missing" in codes


@pytest.mark.parametrize(  # type: ignore[misc, unused-ignore]
    ("duration", "expected_code"),
    (
        (37.9, "duration_too_short"),
        (42.1, "duration_too_long"),
    ),
)
def test_duration_boundaries_fail(
    duration: float,
    expected_code: str,
) -> None:
    evidence = ContentValidationEvidence(
        job_id="job-1",
        scene_ids=("scene-1", "scene-2"),
        narrated_scene_ids=("scene-1", "scene-2"),
        asset_ids=("asset-video", "asset-voice"),
        caption_count=1,
        duration_seconds=duration,
        target_platforms=("youtube_shorts",),
        cta_text="Subscribe.",
        brand_text="Hermes",
    )

    result = ContentValidationCoordinator(
        _policy()
    ).validate(evidence)

    assert expected_code in tuple(
        issue.code for issue in result.issues
    )


def test_platform_and_branding_requirements_fail() -> None:
    evidence = ContentValidationEvidence(
        job_id="job-1",
        scene_ids=("scene-1", "scene-2"),
        narrated_scene_ids=("scene-1", "scene-2"),
        asset_ids=("asset-video", "asset-voice"),
        caption_count=1,
        duration_seconds=40.0,
        target_platforms=("tiktok",),
        cta_text="Subscribe.",
        brand_text="The Last Origin",
    )

    result = ContentValidationCoordinator(
        _policy()
    ).validate(evidence)

    codes = tuple(issue.code for issue in result.issues)

    assert "required_platform_missing" in codes
    assert "branding_term_missing" in codes


def test_unknown_narration_scene_fails() -> None:
    evidence = ContentValidationEvidence(
        job_id="job-1",
        scene_ids=("scene-1", "scene-2"),
        narrated_scene_ids=("scene-1", "scene-2", "scene-3"),
        asset_ids=("asset-video", "asset-voice"),
        caption_count=1,
        duration_seconds=40.0,
        target_platforms=("youtube_shorts",),
        cta_text="Subscribe.",
        brand_text="Hermes",
    )

    result = ContentValidationCoordinator(
        _policy()
    ).validate(evidence)

    assert "narration_scene_unknown" in tuple(
        issue.code for issue in result.issues
    )


def test_validation_is_deterministic() -> None:
    coordinator = ContentValidationCoordinator(_policy())

    first = coordinator.validate(_evidence())
    second = coordinator.validate(_evidence())

    assert first == second
    assert first.validation_id == second.validation_id


def test_policy_rejects_duplicate_values() -> None:
    with pytest.raises(
        ContentValidationError,
        match="unique",
    ):
        ContentValidationPolicy(
            expected_scene_ids=("scene-1", "scene-1"),
            required_asset_ids=(),
            required_platforms=(),
            minimum_duration_seconds=1.0,
            maximum_duration_seconds=2.0,
        )
