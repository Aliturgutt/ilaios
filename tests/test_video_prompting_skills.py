import pytest

from src.video_automation.prompting_skills import (
    DirectedVideoBrief,
    ModelRoutingRequest,
    ReferenceAsset,
    ReferenceAssetPlanner,
    ReferenceRole,
    VideoContinuityPlanner,
    VideoDirector,
    VideoInputMode,
    VideoModelCandidate,
    VideoModelRoutingAdvisor,
    VideoPromptBrief,
    VideoPromptComposer,
)
from src.video_automation.video_skills import VIDEO_SKILLS, VideoSkillError


def _directed() -> DirectedVideoBrief:
    brief = VideoPromptBrief(
        brief_id="brief-1",
        objective="Show a product handoff without identity drift",
        input_mode=VideoInputMode.REFERENCE,
        duration_seconds=8.0,
        visual_style="restrained documentary realism",
        required_beats=("subject approaches the table", "subject hands over the package"),
        audio_intent="quiet room tone and package contact sound",
        ending_state="package rests in the recipient's hands",
    )
    return VideoDirector().direct(
        brief,
        camera_intent="stable medium tracking shot ending on the handoff",
        continuity_keys=("subject identity", "wardrobe", "package identity"),
    )


def test_native_director_continuity_and_prompt_compose_without_provider_authority() -> None:
    directed = _directed()
    continuity = VideoContinuityPlanner().plan(directed)
    package = VideoPromptComposer().compose(
        directed,
        continuity,
        model_id="model-capability-a",
    )

    assert package.external_duration_seconds == 8.0
    assert package.model_id == "model-capability-a"
    assert "subject approaches the table" in package.prompt_text
    assert "package identity" in package.prompt_text
    assert "8.0" not in package.prompt_text
    assert all(beat.inherited_state == directed.continuity_keys for beat in continuity.beats)


def test_reference_assets_are_content_addressed_bounded_and_role_safe() -> None:
    planner = ReferenceAssetPlanner()
    asset = ReferenceAsset(
        asset_id="asset-1",
        role=ReferenceRole.IDENTITY,
        content_sha256="a" * 64,
        controls=("face identity",),
        exclusions=("background",),
    )
    plan = planner.plan((asset,))
    assert plan.immutable_asset_ids == ("asset-1",)
    assert len(plan.plan_sha256) == 64

    with pytest.raises(VideoSkillError, match="unique IDs and content"):
        planner.plan((asset, asset))

    opening_assets = tuple(
        ReferenceAsset(
            asset_id=f"opening-{index}",
            role=ReferenceRole.OPENING_FRAME,
            content_sha256=f"{index + 1:064x}",
            controls=("opening composition",),
        )
        for index in range(2)
    )
    with pytest.raises(VideoSkillError, match="singular"):
        planner.plan(opening_assets)


def test_model_routing_is_advisory_deterministic_and_provider_neutral() -> None:
    request = ModelRoutingRequest(
        input_mode=VideoInputMode.REFERENCE,
        duration_seconds=8.0,
        require_audio=True,
        require_reference_assets=True,
    )
    candidates = (
        VideoModelCandidate(
            model_id="z-model",
            supported_modes=frozenset({VideoInputMode.REFERENCE}),
            max_duration_seconds=10.0,
            supports_audio=True,
            supports_reference_assets=True,
            supports_first_last_frame=False,
        ),
        VideoModelCandidate(
            model_id="a-model",
            supported_modes=frozenset({VideoInputMode.REFERENCE}),
            max_duration_seconds=20.0,
            supports_audio=True,
            supports_reference_assets=True,
            supports_first_last_frame=True,
        ),
    )

    recommendation = VideoModelRoutingAdvisor().recommend(request, candidates)
    assert recommendation.model_id == "a-model"
    assert recommendation.advisory_only is True
    assert "M05" in recommendation.reason
    assert not hasattr(recommendation, "provider")


def test_five_prompting_skills_are_registered_as_first_party_read_only_runtime_bindings() -> None:
    expected = {
        "ilaios.skill.video.direction.director",
        "ilaios.skill.video.prompt.compose",
        "ilaios.skill.video.reference.plan",
        "ilaios.skill.video.routing.model-advice",
        "ilaios.skill.video.continuity.plan",
    }
    manifests = {skill.skill_id: skill for skill in VIDEO_SKILLS if skill.skill_id in expected}

    assert set(manifests) == expected
    for manifest in manifests.values():
        assert manifest.owner == "ILAIOS"
        assert manifest.source_provenance == "ILAIOS-native"
        assert manifest.risk.value == "read_only"
        assert "prompting_skills" in manifest.implementation
