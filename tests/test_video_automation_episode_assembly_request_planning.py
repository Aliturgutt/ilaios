from __future__ import annotations

from types import MappingProxyType

import pytest

from src.video_automation.episode_assembly_planning import (
    EpisodeAssemblyClip,
    EpisodeAssemblyPlan,
)
from src.video_automation.episode_assembly_request_planning import (
    EpisodeAssemblyOutputPolicy,
    EpisodeAssemblyRequest,
    EpisodeAssemblyRequestClip,
    EpisodeAssemblyRequestPlanner,
    EpisodeAssemblyRequestPlanningError,
)


def _plan(count: int = 2) -> EpisodeAssemblyPlan:
    clips = tuple(
        EpisodeAssemblyClip(
            sequence_number=number,
            asset_id=f"asset-{number:02d}",
            dispatch_id=f"dispatch-{number:02d}",
            provider_job_id=f"job-{number:02d}",
            batch_number=number,
            output_index=1,
            metadata={"validation_status": "accepted"},
        )
        for number in range(1, count + 1)
    )
    return EpisodeAssemblyPlan(
        assembly_plan_id="assembly-plan-001",
        validation_manifest_id="validation-001",
        result_manifest_id="result-001",
        execution_state_id="execution-001",
        episode_id="episode-001",
        clips=clips,
        metadata={"clip_count": str(count)},
    )


def _policy() -> EpisodeAssemblyOutputPolicy:
    return EpisodeAssemblyOutputPolicy(
        container_format="mp4",
        video_codec="h264",
        audio_codec="aac",
        width=1080,
        height=1920,
        frame_rate=30,
    )


def test_plan_preserves_clip_order() -> None:
    request = EpisodeAssemblyRequestPlanner().plan(_plan(3), _policy())
    assert [clip.asset_id for clip in request.clips] == [
        "asset-01",
        "asset-02",
        "asset-03",
    ]


def test_plan_copies_clip_identity_fields() -> None:
    clip = EpisodeAssemblyRequestPlanner().plan(_plan(1), _policy()).clips[0]
    assert clip.dispatch_id == "dispatch-01"
    assert clip.provider_job_id == "job-01"
    assert clip.batch_number == 1
    assert clip.output_index == 1


def test_plan_copies_plan_identity() -> None:
    request = EpisodeAssemblyRequestPlanner().plan(_plan(1), _policy())
    assert request.assembly_plan_id == "assembly-plan-001"
    assert request.validation_manifest_id == "validation-001"
    assert request.episode_id == "episode-001"


def test_plan_preserves_explicit_output_policy() -> None:
    policy = _policy()
    request = EpisodeAssemblyRequestPlanner().plan(_plan(1), policy)
    assert request.output_policy is policy


def test_plan_builds_deterministic_identifier() -> None:
    planner = EpisodeAssemblyRequestPlanner()
    assert planner.plan(_plan(2), _policy()).request_id == planner.plan(
        _plan(2), _policy()
    ).request_id


def test_identifier_changes_when_policy_changes() -> None:
    first = EpisodeAssemblyRequestPlanner().plan(_plan(1), _policy())
    second_policy = EpisodeAssemblyOutputPolicy("mov", "prores", "pcm", 1080, 1920, 30)
    second = EpisodeAssemblyRequestPlanner().plan(_plan(1), second_policy)
    assert first.request_id != second.request_id


def test_identifier_changes_when_clip_order_changes() -> None:
    plan = _plan(2)
    reversed_clips = (
        EpisodeAssemblyClip(1, "asset-02", "dispatch-02", "job-02", 2, 1, {}),
        EpisodeAssemblyClip(2, "asset-01", "dispatch-01", "job-01", 1, 1, {}),
    )
    reordered = EpisodeAssemblyPlan(
        plan.assembly_plan_id,
        plan.validation_manifest_id,
        plan.result_manifest_id,
        plan.execution_state_id,
        plan.episode_id,
        reversed_clips,
        {},
    )
    assert EpisodeAssemblyRequestPlanner().plan(
        plan, _policy()
    ).request_id != EpisodeAssemblyRequestPlanner().plan(reordered, _policy()).request_id


def test_plan_rejects_empty_assembly_plan() -> None:
    empty = EpisodeAssemblyPlan(
        "assembly-empty", "validation", "result", "execution", "episode", (), {}
    )
    with pytest.raises(EpisodeAssemblyRequestPlanningError, match="at least one clip"):
        EpisodeAssemblyRequestPlanner().plan(empty, _policy())


def test_request_metadata_is_immutable() -> None:
    request = EpisodeAssemblyRequestPlanner().plan(_plan(1), _policy())
    assert isinstance(request.metadata, MappingProxyType)
    with pytest.raises(TypeError):
        request.metadata["clip_count"] = "2"  # type: ignore[index]


def test_policy_rejects_blank_container_format() -> None:
    with pytest.raises(EpisodeAssemblyRequestPlanningError, match="container_format"):
        EpisodeAssemblyOutputPolicy(" ", "h264", "aac", 1080, 1920, 30)


def test_policy_rejects_non_positive_width() -> None:
    with pytest.raises(EpisodeAssemblyRequestPlanningError, match="width"):
        EpisodeAssemblyOutputPolicy("mp4", "h264", "aac", 0, 1920, 30)


def test_policy_rejects_non_positive_height() -> None:
    with pytest.raises(EpisodeAssemblyRequestPlanningError, match="height"):
        EpisodeAssemblyOutputPolicy("mp4", "h264", "aac", 1080, 0, 30)


def test_policy_rejects_non_positive_frame_rate() -> None:
    with pytest.raises(EpisodeAssemblyRequestPlanningError, match="frame_rate"):
        EpisodeAssemblyOutputPolicy("mp4", "h264", "aac", 1080, 1920, 0)


def test_clip_rejects_blank_asset_id() -> None:
    with pytest.raises(EpisodeAssemblyRequestPlanningError, match="asset_id"):
        EpisodeAssemblyRequestClip(1, " ", "dispatch", "job", 1, 1)


def test_request_rejects_non_contiguous_sequences() -> None:
    clip = EpisodeAssemblyRequestClip(2, "asset", "dispatch", "job", 1, 1)
    with pytest.raises(EpisodeAssemblyRequestPlanningError, match="contiguous"):
        EpisodeAssemblyRequest(
            "request",
            "assembly",
            "validation",
            "episode",
            (clip,),
            _policy(),
            {},
        )


def test_request_rejects_duplicate_asset_ids() -> None:
    first = EpisodeAssemblyRequestClip(1, "asset", "dispatch-1", "job-1", 1, 1)
    second = EpisodeAssemblyRequestClip(2, "asset", "dispatch-2", "job-2", 2, 1)
    with pytest.raises(EpisodeAssemblyRequestPlanningError, match="unique"):
        EpisodeAssemblyRequest(
            "request",
            "assembly",
            "validation",
            "episode",
            (first, second),
            _policy(),
            {},
        )


def test_plan_records_clip_count_metadata() -> None:
    request = EpisodeAssemblyRequestPlanner().plan(_plan(3), _policy())
    assert request.metadata["clip_count"] == "3"
