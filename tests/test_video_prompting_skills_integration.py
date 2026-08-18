from datetime import datetime, timezone
from decimal import Decimal

import pytest

from services.ai_governance import ModelRecord, ProviderRecord, RoutingPolicy
from services.integrations.video_prompting_skills import GovernedVideoPromptingSkills
from services.integrations.video_skill_governance import (
    ALL_VIDEO_SKILLS,
    approve_video_skills,
)
from services.provider_catalog import ProviderCatalogSnapshot
from services.provider_state import (
    ProviderHealthState,
    ProviderQuotaState,
    ProviderRuntimeSnapshot,
)
from services.reference_assets import ReferenceAssetRecord, ReferenceAssetRole
from services.routing_intelligence import RoutingIntelligenceRequest
from services.runtime.routing import AgentProfile, RuntimeError, SkillRegistry
from src.video_automation.continuity import ContinuityState, ContinuityUpdate
from src.video_automation.models import Shot
from src.video_automation.scene_planning import CinematicShot
from src.video_automation.video_skills import CreativeDirection


def _agent() -> AgentProfile:
    authorities = frozenset(
        permission for skill in ALL_VIDEO_SKILLS for permission in skill.permissions
    )
    return AgentProfile("video-worker", authorities)


def _shot() -> Shot:
    return Shot(
        shot_id="shot-1",
        scene_id="scene-1",
        shot_type="cinematic",
        camera_description="neutral product camera",
        subject="brushed-metal device",
        action="rotate slowly",
        environment="neutral studio",
        framing="medium shot",
        movement="static",
        estimated_duration_seconds=4.0,
        generation_prompt="reveal the product",
        required_provider_capability="video.generate",
    )


def _direction() -> CreativeDirection:
    return CreativeDirection(
        direction_id="direction-1",
        visual_intent="controlled product reveal",
        shot_scale="medium close-up",
        camera_angle="eye level",
        camera_movement="slow dolly-in",
        lighting="soft neutral key",
        palette=("graphite", "white"),
        pacing="restrained",
        continuity_keys=("product geometry", "material finish"),
    )


def _approved_adapter() -> GovernedVideoPromptingSkills:
    registry = SkillRegistry()
    approve_video_skills(registry)
    return GovernedVideoPromptingSkills(registry, _agent())


def test_prompting_facade_fails_closed_before_skill_approval() -> None:
    adapter = GovernedVideoPromptingSkills(SkillRegistry(), _agent())
    with pytest.raises(RuntimeError, match="not approved"):
        adapter.direct((_shot(),), _direction())


def test_director_delegates_to_canonical_cinematography_executor() -> None:
    result = _approved_adapter().direct((_shot(),), _direction())
    assert result.direction_id == "direction-1"
    assert result.shots[0].generation_prompt.startswith(
        "creative_direction_id: direction-1"
    )


def test_prompt_delegates_to_canonical_shot_prompt_compiler() -> None:
    shot = CinematicShot(
        shot_id="shot-1",
        sequence=1,
        source_beat_id="beat-1",
        text="the product rotates and settles",
        duration_seconds=4.0,
        continuity_note="preserve product identity",
        previous_shot_id=None,
        next_shot_id=None,
        generation_prompt="the product rotates and settles",
    )
    state = ContinuityState(
        shot_id="shot-1",
        timeline="opening shot",
        visual_style="controlled studio realism",
        camera_state="slow dolly-in",
        scene_state="product centered on plinth",
    )
    package = _approved_adapter().compose_prompt(shot, state)
    assert package.shot_id == "shot-1"
    assert "shot: the product rotates and settles" in package.prompt_text
    assert "visual_style: controlled studio realism" in package.prompt_text


def test_continuity_delegates_to_canonical_tracker() -> None:
    adapter = _approved_adapter()
    first = adapter.start_continuity(
        ContinuityState(
            shot_id="shot-1",
            objects=("device closed",),
            scene_state="device centered",
        )
    )
    transition = adapter.advance_continuity(
        first,
        shot_id="shot-2",
        update=ContinuityUpdate(
            timeline="second shot",
            scene_state="device remains centered",
        ),
    )
    assert transition.current.previous_shot_id == "shot-1"
    assert transition.current.objects == ("device closed",)
    assert transition.changed_fields == ("timeline", "scene_state")


def test_reference_skill_exposes_only_already_admitted_metadata() -> None:
    now = datetime(2026, 8, 18, tzinfo=timezone.utc)
    record = ReferenceAssetRecord(
        asset_id="ref-abc123",
        principal_id="principal-1",
        tenant_id="tenant-1",
        sha256="a" * 64,
        mime_type="image/png",
        original_filename="product.png",
        width=1024,
        height=1024,
        size_bytes=2048,
        role=ReferenceAssetRole.PRODUCT,
        instruction="preserve product geometry",
        created_at=now,
    )
    result = _approved_adapter().inspect_references((record,))
    assert result == (record,)
    assert result[0].sha256 == "a" * 64


def test_model_fit_delegates_to_existing_routing_intelligence_only() -> None:
    now = datetime(2026, 8, 18, tzinfo=timezone.utc)
    catalog = ProviderCatalogSnapshot(
        catalog_version="catalog-1",
        observed_at=now,
        providers=(ProviderRecord("provider-a", "adapter-a"),),
        models=(
            ModelRecord(
                "model-a",
                "provider-a",
                frozenset({"video.generate"}),
                8192,
                4096,
            ),
        ),
    )
    runtime_state = ProviderRuntimeSnapshot(
        state_version="state-1",
        observed_at=now,
        health=(
            ProviderHealthState(
                "provider-a",
                now,
                Decimal("1"),
                100,
            ),
        ),
        quota=(
            ProviderQuotaState(
                "provider-a",
                now,
                remaining_requests=10,
                remaining_tokens=100_000,
            ),
        ),
    )
    evidence = _approved_adapter().analyze_model_fit(
        catalog=catalog,
        runtime_state=runtime_state,
        policy=RoutingPolicy(),
        request=RoutingIntelligenceRequest(
            capability="video.generate",
            input_tokens=0,
            output_tokens=0,
        ),
        now=now,
    )
    assert evidence.ranked_model_ids == ("model-a",)
    assert evidence.candidates[0].eligible is True
