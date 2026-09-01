from __future__ import annotations

import pytest

from services.integrations.video_creative_direction import (
    GovernedCinematographyExecutor,
)
from services.integrations.video_skill_governance import approve_video_skills
from services.runtime.routing import AgentProfile, RuntimeError, SkillRegistry
from src.video_automation.asset_planning import AssetPlanner
from src.video_automation.creative_direction_execution import (
    CinematographyExecutionError,
    CinematographyExecutor,
)
from src.video_automation.models import MediaType, Shot
from src.video_automation.video_skills import CreativeDirection


def _shot(*, shot_id: str = "scene-001-shot-001") -> Shot:
    return Shot(
        shot_id=shot_id,
        scene_id="scene-001",
        shot_type="cinematic",
        camera_description="hero enters a rain-soaked station",
        subject="hero",
        action="enters the station",
        environment="rain-soaked station",
        framing="medium shot",
        movement="static",
        estimated_duration_seconds=5.0,
        generation_prompt="hero enters a rain-soaked station",
        required_provider_capability="video.generate",
    )


def _direction() -> CreativeDirection:
    return CreativeDirection(
        direction_id="direction-001",
        visual_intent="tense grounded realism",
        shot_scale="wide shot",
        camera_angle="low angle",
        camera_movement="slow dolly-in",
        lighting="cold practical lights with controlled contrast",
        palette=("graphite", "cold blue"),
        pacing="measured escalation",
        continuity_keys=("hero-costume", "station-weather"),
    )


def test_executor_applies_direction_without_mutating_story_identity() -> None:
    source = _shot()
    result = CinematographyExecutor().execute((source,), _direction())
    directed = result.shots[0]

    assert directed.shot_id == source.shot_id
    assert directed.scene_id == source.scene_id
    assert directed.subject == source.subject
    assert directed.action == source.action
    assert directed.environment == source.environment
    assert directed.estimated_duration_seconds == source.estimated_duration_seconds
    assert directed.required_provider_capability == source.required_provider_capability
    assert directed.framing == "wide shot"
    assert directed.movement == "slow dolly-in"
    assert "camera_angle=low angle" in directed.camera_description
    assert "lighting=cold practical lights with controlled contrast" in directed.camera_description


def test_executor_compiles_every_direction_field_into_generation_prompt() -> None:
    directed = CinematographyExecutor().execute((_shot(),), _direction()).shots[0]
    lines = directed.generation_prompt.splitlines()
    assert lines == [
        "creative_direction_id: direction-001",
        "narrative_prompt: hero enters a rain-soaked station",
        "visual_intent: tense grounded realism",
        "shot_scale: wide shot",
        "camera_angle: low angle",
        "camera_movement: slow dolly-in",
        "lighting: cold practical lights with controlled contrast",
        "palette: graphite | cold blue",
        "pacing: measured escalation",
        "continuity_keys: hero-costume | station-weather",
    ]


def test_directed_prompt_flows_into_m10_asset_planning() -> None:
    directed = CinematographyExecutor().execute((_shot(),), _direction()).shots
    request = AssetPlanner().plan(
        job_id="job-001",
        shots=directed,
        media_type_by_capability={"video.generate": MediaType.VIDEO},
    )[0]
    assert request.description == directed[0].generation_prompt
    assert request.required_capability == "video.generate"
    assert request.metadata["scene_id"] == "scene-001"


def test_execution_is_deterministic_and_content_addressed() -> None:
    executor = CinematographyExecutor()
    first = executor.execute((_shot(),), _direction())
    second = executor.execute((_shot(),), _direction())
    assert first == second
    assert len(first.execution_sha256) == 64


def test_executor_rejects_duplicate_shots_and_double_application() -> None:
    executor = CinematographyExecutor()
    with pytest.raises(CinematographyExecutionError, match="shot_id values"):
        executor.execute((_shot(), _shot()), _direction())

    directed = executor.execute((_shot(),), _direction()).shots[0]
    with pytest.raises(CinematographyExecutionError, match="already has"):
        executor.execute((directed,), _direction())


def test_executor_rejects_unbounded_direction_collections() -> None:
    duplicate_palette = CreativeDirection(
        direction_id="direction-002",
        visual_intent="clean",
        shot_scale="medium",
        camera_angle="eye-level",
        camera_movement="static",
        lighting="soft",
        palette=("blue", "blue"),
        pacing="steady",
        continuity_keys=("subject",),
    )
    with pytest.raises(CinematographyExecutionError, match="palette values must be unique"):
        CinematographyExecutor().execute((_shot(),), duplicate_palette)

    blank_continuity = CreativeDirection(
        direction_id="direction-003",
        visual_intent="clean",
        shot_scale="medium",
        camera_angle="eye-level",
        camera_movement="static",
        lighting="soft",
        palette=("blue",),
        pacing="steady",
        continuity_keys=(" ",),
    )
    with pytest.raises(CinematographyExecutionError, match="continuity_keys"):
        CinematographyExecutor().execute((_shot(),), blank_continuity)


def test_governed_execution_requires_canonical_registry_approval() -> None:
    registry = SkillRegistry()
    agent = AgentProfile("video-director", frozenset({"manifest.read"}))
    governed = GovernedCinematographyExecutor(registry, agent)
    with pytest.raises(RuntimeError, match="skill is not approved"):
        governed.execute((_shot(),), _direction())


def test_governed_execution_uses_existing_registry_and_authority_chain() -> None:
    registry = SkillRegistry()
    approve_video_skills(registry)
    agent = AgentProfile("video-director", frozenset({"manifest.read"}))
    result = GovernedCinematographyExecutor(registry, agent).execute(
        (_shot(),), _direction()
    )
    assert result.direction_id == "direction-001"
    assert result.shots[0].movement == "slow dolly-in"


def test_governed_execution_rejects_agent_authority_expansion() -> None:
    registry = SkillRegistry()
    approve_video_skills(registry)
    agent = AgentProfile("video-director", frozenset({"media.read"}))
    with pytest.raises(RuntimeError, match="expand agent authority"):
        GovernedCinematographyExecutor(registry, agent).execute(
            (_shot(),), _direction()
        )
