from __future__ import annotations

from types import MappingProxyType

import pytest

from src.video_automation.prompt_compilation import PromptSection, ShotPromptPackage
from src.video_automation.shot_request_planning import (
    ShotGenerationPolicy,
    ShotGenerationRequest,
    ShotGenerationRequestPlanner,
    ShotRequestPlanningError,
)


def _package(*, prompt_text: str = "shot: A rover crosses the frozen plain.") -> ShotPromptPackage:
    return ShotPromptPackage(
        shot_id="episode-001-shot-004",
        source_beat_id="beat-002",
        duration_seconds=5.0,
        sections=(PromptSection("shot", "A rover crosses the frozen plain."),),
        prompt_text=prompt_text,
    )


def test_default_policy_is_explicit_and_vertical() -> None:
    policy = ShotGenerationPolicy()
    assert policy.aspect_ratio == "9:16"
    assert policy.frames_per_second == 24
    assert policy.output_count == 1
    assert policy.seed is None


def test_plan_preserves_approved_prompt_and_identifiers() -> None:
    request = ShotGenerationRequestPlanner().plan(_package())
    assert request.shot_id == "episode-001-shot-004"
    assert request.source_beat_id == "beat-002"
    assert request.prompt_text == _package().prompt_text
    assert request.duration_seconds == 5.0


def test_plan_applies_only_explicit_policy_values() -> None:
    policy = ShotGenerationPolicy(
        aspect_ratio="16:9", frames_per_second=30, output_count=2, seed=44
    )
    request = ShotGenerationRequestPlanner(policy).plan(_package())
    assert request.aspect_ratio == "16:9"
    assert request.frames_per_second == 30
    assert request.output_count == 2
    assert request.seed == 44


def test_request_id_is_stable_for_identical_inputs() -> None:
    planner = ShotGenerationRequestPlanner()
    first = planner.plan(_package())
    second = planner.plan(_package())
    assert first.request_id == second.request_id
    assert first.idempotency_key == second.idempotency_key


def test_prompt_change_changes_idempotency_key() -> None:
    planner = ShotGenerationRequestPlanner()
    first = planner.plan(_package())
    second = planner.plan(_package(prompt_text="shot: The rover stops."))
    assert first.idempotency_key != second.idempotency_key


def test_policy_change_changes_idempotency_key() -> None:
    first = ShotGenerationRequestPlanner().plan(_package())
    second = ShotGenerationRequestPlanner(
        ShotGenerationPolicy(frames_per_second=30)
    ).plan(_package())
    assert first.idempotency_key != second.idempotency_key


def test_metadata_contains_auditable_source_hash() -> None:
    request = ShotGenerationRequestPlanner().plan(_package())
    assert request.metadata["shot_id"] == request.shot_id
    assert request.metadata["source_beat_id"] == request.source_beat_id
    assert len(request.metadata["prompt_sha256"]) == 64


def test_metadata_is_immutable() -> None:
    request = ShotGenerationRequestPlanner().plan(_package())
    assert isinstance(request.metadata, MappingProxyType)
    with pytest.raises(TypeError):
        request.metadata["new"] = "value"  # type: ignore[index]


def test_negative_seed_fails_closed() -> None:
    with pytest.raises(ShotRequestPlanningError, match="seed"):
        ShotGenerationPolicy(seed=-1)


def test_zero_frames_per_second_fails_closed() -> None:
    with pytest.raises(ShotRequestPlanningError, match="frames_per_second"):
        ShotGenerationPolicy(frames_per_second=0)


def test_zero_output_count_fails_closed() -> None:
    with pytest.raises(ShotRequestPlanningError, match="output_count"):
        ShotGenerationPolicy(output_count=0)


def test_blank_aspect_ratio_fails_closed() -> None:
    with pytest.raises(ShotRequestPlanningError, match="aspect_ratio"):
        ShotGenerationPolicy(aspect_ratio=" ")


def test_request_rejects_blank_request_id() -> None:
    with pytest.raises(ShotRequestPlanningError, match="request_id"):
        ShotGenerationRequest(
            request_id=" ",
            idempotency_key="a" * 64,
            shot_id="shot-1",
            source_beat_id="beat-1",
            prompt_text="shot: approved",
            duration_seconds=5.0,
            aspect_ratio="9:16",
            frames_per_second=24,
            output_count=1,
            seed=None,
            metadata={},
        )


def test_request_rejects_non_positive_duration() -> None:
    with pytest.raises(ShotRequestPlanningError, match="duration_seconds"):
        ShotGenerationRequest(
            request_id="request-1",
            idempotency_key="a" * 64,
            shot_id="shot-1",
            source_beat_id="beat-1",
            prompt_text="shot: approved",
            duration_seconds=0.0,
            aspect_ratio="9:16",
            frames_per_second=24,
            output_count=1,
            seed=None,
            metadata={},
        )


def test_request_copies_metadata_before_freezing() -> None:
    metadata = {"key": "value"}
    request = ShotGenerationRequest(
        request_id="request-1",
        idempotency_key="a" * 64,
        shot_id="shot-1",
        source_beat_id="beat-1",
        prompt_text="shot: approved",
        duration_seconds=5.0,
        aspect_ratio="9:16",
        frames_per_second=24,
        output_count=1,
        seed=None,
        metadata=metadata,
    )
    metadata["key"] = "changed"
    assert request.metadata["key"] == "value"


def test_blank_metadata_values_fail_closed() -> None:
    with pytest.raises(ShotRequestPlanningError, match="metadata value"):
        ShotGenerationRequest(
            request_id="request-1",
            idempotency_key="a" * 64,
            shot_id="shot-1",
            source_beat_id="beat-1",
            prompt_text="shot: approved",
            duration_seconds=5.0,
            aspect_ratio="9:16",
            frames_per_second=24,
            output_count=1,
            seed=None,
            metadata={"key": " "},
        )


def test_planning_performs_no_provider_selection() -> None:
    request = ShotGenerationRequestPlanner().plan(_package())
    assert not hasattr(request, "provider")
    assert not hasattr(request, "provider_id")
