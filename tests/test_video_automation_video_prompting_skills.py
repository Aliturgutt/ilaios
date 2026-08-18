import pytest

from src.video_automation.video_prompting_skills import (
    ContinuityPlanner,
    DirectorBrief,
    DirectorPlan,
    ModelCapabilityProfile,
    ModelRoutingAdvisor,
    ModelRoutingRequest,
    PromptForm,
    ReferenceAssetPlanner,
    ReferenceDirective,
    ReferenceKind,
    VideoDirector,
    VideoInputMode,
    VideoPromptComposer,
    VideoPromptRequest,
    VideoPromptSkillError,
)


def _director_plan() -> DirectorPlan:
    brief = DirectorBrief(
        "brief-1",
        "reveal the product without changing its geometry",
        "a brushed-metal device",
        "a neutral studio",
        ("the device rotates slowly", "the device settles facing camera"),
        "slow dolly-in that stops before the final hold",
        "soft neutral key light with controlled reflections",
        "faint room tone and one restrained mechanical contact sound",
        "the device is centered, still, and fully readable",
        ("same product geometry", "same material finish"),
    )
    return VideoDirector().plan(brief)


def test_director_is_deterministic_and_preserves_explicit_continuity() -> None:
    first = _director_plan()
    second = _director_plan()
    assert first == second
    assert first.continuity_invariants == (
        "same product geometry",
        "same material finish",
    )
    assert len(first.plan_sha256) == 64


def test_reference_asset_planner_rejects_duplicate_identity_and_conflicts() -> None:
    planner = ReferenceAssetPlanner()
    directive = ReferenceDirective(
        "image-1",
        ReferenceKind.IMAGE,
        "product identity and material appearance",
        ("product geometry", "material finish"),
        ("background", "camera angle"),
        "a" * 64,
    )
    plan = planner.plan((directive,))
    assert plan.directives == (directive,)
    with pytest.raises(VideoPromptSkillError, match="reference_id"):
        planner.plan((directive, directive))
    with pytest.raises(VideoPromptSkillError, match="conflict"):
        ReferenceDirective(
            "image-2",
            ReferenceKind.IMAGE,
            "wardrobe",
            ("lighting",),
            ("lighting",),
        )


def test_continuity_planner_rejects_duplicate_invariants() -> None:
    planner = ContinuityPlanner()
    with pytest.raises(VideoPromptSkillError, match="unique"):
        planner.build(
            continuity_id="continuity-1",
            invariants=("same jacket", "same jacket"),
            ending_state="subject exits frame right",
        )


def test_prompt_composer_anchors_i2v_and_keeps_provider_controls_out() -> None:
    plan = _director_plan()
    continuity = ContinuityPlanner().build(
        continuity_id="continuity-1",
        invariants=plan.continuity_invariants,
        object_state=("device remains intact",),
        screen_direction=("camera remains on the same action axis",),
        ending_state=plan.ending_state,
    )
    result = VideoPromptComposer().compose(
        VideoPromptRequest(
            "prompt-1",
            VideoInputMode.IMAGE_TO_VIDEO,
            PromptForm.SINGLE_SHOT,
            plan.shot_intent,
            plan.action_arc,
            plan.camera_intent,
            plan.visual_treatment,
            plan.audio_intent,
            plan.ending_state,
            continuity=continuity,
        )
    )
    assert "OPENING ANCHOR:" in result.prompt
    assert "ACTION:" in result.prompt
    assert "CONTINUITY:" in result.prompt
    lowered = result.prompt.lower()
    for forbidden in ("model name:", "model version:", "aspect ratio:", "resolution:"):
        assert forbidden not in lowered


def test_reference_driven_prompt_requires_admitted_reference_plan() -> None:
    plan = _director_plan()
    with pytest.raises(VideoPromptSkillError, match="reference-driven"):
        VideoPromptRequest(
            "prompt-1",
            VideoInputMode.REFERENCE_TO_VIDEO,
            PromptForm.TIMED_SEQUENCE,
            plan.shot_intent,
            plan.action_arc,
            plan.camera_intent,
            plan.visual_treatment,
            plan.audio_intent,
            plan.ending_state,
        )


def test_model_routing_advisor_is_capability_only_and_deterministic() -> None:
    profiles = (
        ModelCapabilityProfile(
            "model-b",
            frozenset(
                {
                    VideoInputMode.TEXT_TO_VIDEO,
                    VideoInputMode.REFERENCE_TO_VIDEO,
                }
            ),
            True,
            True,
            True,
            True,
        ),
        ModelCapabilityProfile(
            "model-a",
            frozenset({VideoInputMode.TEXT_TO_VIDEO}),
            False,
            False,
            False,
            False,
        ),
        ModelCapabilityProfile(
            "model-c",
            frozenset(
                {
                    VideoInputMode.TEXT_TO_VIDEO,
                    VideoInputMode.REFERENCE_TO_VIDEO,
                }
            ),
            True,
            True,
            False,
            True,
        ),
    )
    advice = ModelRoutingAdvisor().advise(
        ModelRoutingRequest(
            VideoInputMode.REFERENCE_TO_VIDEO,
            PromptForm.TIMED_SEQUENCE,
            requires_native_audio=True,
            requires_reference_assets=True,
        ),
        profiles,
    )
    assert advice.candidate_model_ids == ("model-b", "model-c")
    assert all("provider" not in reason.lower() for reason in advice.rationale)


def test_model_routing_advisor_fails_closed_without_capability_match() -> None:
    with pytest.raises(VideoPromptSkillError, match="no model capability"):
        ModelRoutingAdvisor().advise(
            ModelRoutingRequest(
                VideoInputMode.FIRST_LAST_FRAME,
                PromptForm.MULTI_SHOT,
                requires_native_audio=True,
                requires_reference_assets=True,
            ),
            (
                ModelCapabilityProfile(
                    "model-a",
                    frozenset({VideoInputMode.TEXT_TO_VIDEO}),
                    False,
                    False,
                    False,
                    False,
                ),
            ),
        )
