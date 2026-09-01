from __future__ import annotations

from types import MappingProxyType

import pytest

from src.video_automation.generation_batch_planning import (
    EpisodeGenerationBatchPlan,
    EpisodeGenerationBatchPlanner,
    GenerationBatchPolicy,
)
from src.video_automation.generation_dispatch_planning import (
    EpisodeGenerationDispatchPlan,
    EpisodeGenerationDispatchPlanner,
    GenerationBatchDispatch,
    GenerationDispatchItem,
    GenerationDispatchPlanningError,
    GenerationProviderBinding,
)
from src.video_automation.request_manifest import EpisodeRequestManifestBuilder
from src.video_automation.shot_request_planning import ShotGenerationRequest


def _request(number: int) -> ShotGenerationRequest:
    suffix = f"{number:02d}"
    return ShotGenerationRequest(
        request_id=f"request-{suffix}",
        idempotency_key=(f"{number:x}" * 64)[:64],
        shot_id=f"shot-{suffix}",
        source_beat_id=f"beat-{suffix}",
        prompt_text=f"approved prompt {suffix}",
        duration_seconds=5.0,
        aspect_ratio="9:16",
        frames_per_second=24,
        output_count=1,
        seed=None,
        metadata={},
    )


def _generation_plan(count: int = 5) -> EpisodeGenerationBatchPlan:
    manifest = EpisodeRequestManifestBuilder().build(
        "episode-001", [_request(number) for number in range(1, count + 1)]
    )
    return EpisodeGenerationBatchPlanner(GenerationBatchPolicy(2)).plan(manifest)


def _binding() -> GenerationProviderBinding:
    return GenerationProviderBinding(
        "provider-alpha",
        "model-cinematic-v1",
        max_parallel_requests=2,
    )


def _item(sequence_number: int = 1) -> GenerationDispatchItem:
    return GenerationDispatchItem(
        sequence_number=sequence_number,
        request_id=f"request-{sequence_number}",
        idempotency_key="a" * 64,
        shot_id=f"shot-{sequence_number}",
        prompt_text="approved prompt",
        duration_seconds=5.0,
        aspect_ratio="9:16",
        frames_per_second=24,
        output_count=1,
        seed=None,
    )


def test_binding_preserves_explicit_provider_configuration() -> None:
    binding = _binding()
    assert binding.provider_id == "provider-alpha"
    assert binding.model_id == "model-cinematic-v1"
    assert binding.operation == "video.generate"
    assert binding.max_parallel_requests == 2


def test_planner_creates_one_dispatch_per_batch() -> None:
    plan = EpisodeGenerationDispatchPlanner(_binding()).plan(_generation_plan(5))
    assert plan.dispatch_count == 3
    assert [len(dispatch.items) for dispatch in plan.dispatches] == [2, 2, 1]


def test_planner_preserves_request_order() -> None:
    plan = EpisodeGenerationDispatchPlanner(_binding()).plan(_generation_plan(5))
    assert [
        item.request_id for dispatch in plan.dispatches for item in dispatch.items
    ] == [f"request-{number:02d}" for number in range(1, 6)]


def test_planner_copies_complete_request_contract() -> None:
    item = EpisodeGenerationDispatchPlanner(_binding()).plan(
        _generation_plan(1)
    ).dispatches[0].items[0]
    assert item.shot_id == "shot-01"
    assert item.prompt_text == "approved prompt 01"
    assert item.duration_seconds == 5.0
    assert item.aspect_ratio == "9:16"
    assert item.frames_per_second == 24
    assert item.output_count == 1
    assert item.seed is None


def test_dispatch_uses_explicit_binding_without_selection() -> None:
    dispatch = EpisodeGenerationDispatchPlanner(_binding()).plan(
        _generation_plan(1)
    ).dispatches[0]
    assert dispatch.provider_id == "provider-alpha"
    assert dispatch.model_id == "model-cinematic-v1"
    assert dispatch.operation == "video.generate"
    assert dispatch.max_parallel_requests == 2


def test_dispatch_ids_are_stable_for_identical_inputs() -> None:
    planner = EpisodeGenerationDispatchPlanner(_binding())
    assert planner.plan(_generation_plan()).dispatch_plan_id == planner.plan(
        _generation_plan()
    ).dispatch_plan_id


def test_binding_change_changes_dispatch_plan_id() -> None:
    generation_plan = _generation_plan()
    first = EpisodeGenerationDispatchPlanner(_binding()).plan(generation_plan)
    second = EpisodeGenerationDispatchPlanner(
        GenerationProviderBinding("provider-beta", "model-cinematic-v1")
    ).plan(generation_plan)
    assert first.dispatch_plan_id != second.dispatch_plan_id


def test_plan_metadata_is_auditable_and_immutable() -> None:
    plan = EpisodeGenerationDispatchPlanner(_binding()).plan(_generation_plan())
    assert plan.metadata["provider_id"] == "provider-alpha"
    assert plan.metadata["model_id"] == "model-cinematic-v1"
    assert isinstance(plan.metadata, MappingProxyType)
    with pytest.raises(TypeError):
        plan.metadata["provider_id"] = "changed"  # type: ignore[index]


def test_dispatch_metadata_is_immutable() -> None:
    dispatch = EpisodeGenerationDispatchPlanner(_binding()).plan(
        _generation_plan()
    ).dispatches[0]
    assert isinstance(dispatch.metadata, MappingProxyType)
    with pytest.raises(TypeError):
        dispatch.metadata["episode_id"] = "changed"  # type: ignore[index]


def test_binding_rejects_blank_provider_id() -> None:
    with pytest.raises(GenerationDispatchPlanningError, match="provider_id"):
        GenerationProviderBinding(" ", "model-1")


def test_binding_rejects_non_positive_parallel_limit() -> None:
    with pytest.raises(
        GenerationDispatchPlanningError, match="max_parallel_requests"
    ):
        GenerationProviderBinding("provider-1", "model-1", max_parallel_requests=0)


def test_item_rejects_non_positive_sequence_number() -> None:
    with pytest.raises(GenerationDispatchPlanningError, match="sequence_number"):
        _item(0)


def test_dispatch_rejects_empty_items() -> None:
    with pytest.raises(GenerationDispatchPlanningError, match="items"):
        GenerationBatchDispatch(
            "dispatch-1", "batch-1", 1, "provider-1", "model-1",
            "video.generate", 1, (), {}
        )


def test_dispatch_rejects_descending_item_order() -> None:
    with pytest.raises(GenerationDispatchPlanningError, match="ascending"):
        GenerationBatchDispatch(
            "dispatch-1", "batch-1", 1, "provider-1", "model-1",
            "video.generate", 1, (_item(2), _item(1)), {}
        )


def test_plan_rejects_incorrect_dispatch_count() -> None:
    dispatch = GenerationBatchDispatch(
        "dispatch-1", "batch-1", 1, "provider-1", "model-1",
        "video.generate", 1, (_item(),), {}
    )
    with pytest.raises(GenerationDispatchPlanningError, match="dispatch_count"):
        EpisodeGenerationDispatchPlan(
            "plan-1", "generation-plan-1", "manifest-1", "episode-1",
            (dispatch,), 2, 1, {}
        )


def test_plan_copies_metadata_before_freezing() -> None:
    dispatch = GenerationBatchDispatch(
        "dispatch-1", "batch-1", 1, "provider-1", "model-1",
        "video.generate", 1, (_item(),), {}
    )
    metadata = {"key": "value"}
    plan = EpisodeGenerationDispatchPlan(
        "plan-1", "generation-plan-1", "manifest-1", "episode-1",
        (dispatch,), 1, 1, metadata
    )
    metadata["key"] = "changed"
    assert plan.metadata["key"] == "value"


def test_planning_contains_no_execution_result_or_media() -> None:
    plan = EpisodeGenerationDispatchPlanner(_binding()).plan(_generation_plan())
    assert not hasattr(plan, "result")
    assert not hasattr(plan, "media")
