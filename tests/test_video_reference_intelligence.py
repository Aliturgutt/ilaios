from __future__ import annotations

import pytest

from services.integrations.video_reference_intelligence import (
    VideoReferenceIntentError,
    VideoReferenceMode,
    derive_video_reference_plan,
)


def test_unqualified_references_are_general_guidance() -> None:
    plan = derive_video_reference_plan(
        "Keep the product identity and visual style consistent with my references.",
        reference_count=3,
    )
    assert plan.mode is VideoReferenceMode.GUIDANCE
    assert plan.reference_count == 3
    assert plan.frame_references == ()


def test_first_frame_intent_is_exact_frame_control() -> None:
    plan = derive_video_reference_plan(
        "Use my image as the first frame and animate forward from it.",
        reference_count=1,
    )
    assert plan.mode is VideoReferenceMode.FRAME_CONTROL
    assert [(item.asset_index, item.frame_type) for item in plan.frame_references] == [
        (0, "first_frame")
    ]


def test_first_and_last_frame_use_ordered_pair() -> None:
    plan = derive_video_reference_plan(
        "Use the first image as the first frame and the second as the last frame.",
        reference_count=2,
    )
    assert [(item.asset_index, item.frame_type) for item in plan.frame_references] == [
        (0, "first_frame"),
        (1, "last_frame"),
    ]


def test_frame_control_rejects_extra_references_instead_of_dropping_them() -> None:
    with pytest.raises(VideoReferenceIntentError, match="silently ignored"):
        derive_video_reference_plan(
            "Use the first image as the first frame.",
            reference_count=2,
        )


def test_reference_plan_honors_twenty_image_contract() -> None:
    plan = derive_video_reference_plan("Use these as visual guidance.", reference_count=20)
    assert plan.reference_count == 20
    with pytest.raises(VideoReferenceIntentError, match="outside supported bounds"):
        derive_video_reference_plan("Use these as visual guidance.", reference_count=21)
