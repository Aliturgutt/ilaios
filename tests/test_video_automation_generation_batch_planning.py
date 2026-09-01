from __future__ import annotations

from types import MappingProxyType

import pytest

from src.video_automation.generation_batch_planning import (
    EpisodeGenerationBatchPlan,
    EpisodeGenerationBatchPlanner,
    GenerationBatch,
    GenerationBatchPlanningError,
    GenerationBatchPolicy,
)
from src.video_automation.request_manifest import (
    EpisodeRequestManifest,
    EpisodeRequestManifestBuilder,
    ShotRequestEntry,
)
from src.video_automation.shot_request_planning import ShotGenerationRequest


def _request(number: int, *, duration: float = 5.0) -> ShotGenerationRequest:
    suffix = f"{number:02d}"
    return ShotGenerationRequest(
        request_id=f"request-{suffix}",
        idempotency_key=(f"{number:x}" * 64)[:64],
        shot_id=f"shot-{suffix}",
        source_beat_id=f"beat-{suffix}",
        prompt_text=f"shot: approved prompt {suffix}",
        duration_seconds=duration,
        aspect_ratio="9:16",
        frames_per_second=24,
        output_count=1,
        seed=None,
        metadata={},
    )


def _manifest(count: int = 5) -> EpisodeRequestManifest:
    return EpisodeRequestManifestBuilder().build(
        "episode-001", [_request(number) for number in range(1, count + 1)]
    )


def test_default_policy_uses_four_requests_per_batch() -> None:
    assert GenerationBatchPolicy().max_requests_per_batch == 4


def test_planner_partitions_requests_by_explicit_limit() -> None:
    plan = EpisodeGenerationBatchPlanner(GenerationBatchPolicy(2)).plan(_manifest(5))
    assert [len(batch.entries) for batch in plan.batches] == [2, 2, 1]


def test_planner_preserves_manifest_request_order() -> None:
    plan = EpisodeGenerationBatchPlanner(GenerationBatchPolicy(2)).plan(_manifest(5))
    assert [
        entry.request.request_id for batch in plan.batches for entry in batch.entries
    ] == [f"request-{number:02d}" for number in range(1, 6)]


def test_planner_assigns_contiguous_batch_numbers() -> None:
    plan = EpisodeGenerationBatchPlanner(GenerationBatchPolicy(2)).plan(_manifest(5))
    assert [batch.batch_number for batch in plan.batches] == [1, 2, 3]


def test_plan_counts_batches_and_requests() -> None:
    plan = EpisodeGenerationBatchPlanner(GenerationBatchPolicy(2)).plan(_manifest(5))
    assert plan.batch_count == 3
    assert plan.request_count == 5


def test_plan_preserves_manifest_duration() -> None:
    manifest = EpisodeRequestManifestBuilder().build(
        "episode-001", [_request(1, duration=4.5), _request(2, duration=5.5)]
    )
    plan = EpisodeGenerationBatchPlanner().plan(manifest)
    assert plan.total_duration_seconds == 10.0
    assert plan.batches[0].total_duration_seconds == 10.0


def test_plan_id_is_stable_for_identical_inputs() -> None:
    planner = EpisodeGenerationBatchPlanner(GenerationBatchPolicy(2))
    assert planner.plan(_manifest()).plan_id == planner.plan(_manifest()).plan_id


def test_policy_change_changes_plan_id() -> None:
    manifest = _manifest()
    first = EpisodeGenerationBatchPlanner(GenerationBatchPolicy(2)).plan(manifest)
    second = EpisodeGenerationBatchPlanner(GenerationBatchPolicy(3)).plan(manifest)
    assert first.plan_id != second.plan_id


def test_metadata_contains_auditable_boundaries() -> None:
    plan = EpisodeGenerationBatchPlanner(GenerationBatchPolicy(2)).plan(_manifest(5))
    assert plan.metadata["first_request_id"] == "request-01"
    assert plan.metadata["last_request_id"] == "request-05"
    assert plan.metadata["max_requests_per_batch"] == "2"


def test_metadata_is_immutable() -> None:
    plan = EpisodeGenerationBatchPlanner().plan(_manifest())
    assert isinstance(plan.metadata, MappingProxyType)
    with pytest.raises(TypeError):
        plan.metadata["new"] = "value"  # type: ignore[index]


def test_policy_rejects_non_positive_batch_size() -> None:
    with pytest.raises(GenerationBatchPlanningError, match="max_requests_per_batch"):
        GenerationBatchPolicy(0)


def test_batch_rejects_non_positive_batch_number() -> None:
    with pytest.raises(GenerationBatchPlanningError, match="batch_number"):
        GenerationBatch("batch-1", 0, (ShotRequestEntry(1, _request(1)),), 5.0)


def test_batch_rejects_empty_entries() -> None:
    with pytest.raises(GenerationBatchPlanningError, match="entries"):
        GenerationBatch("batch-1", 1, (), 5.0)


def test_batch_rejects_descending_manifest_order() -> None:
    with pytest.raises(GenerationBatchPlanningError, match="ascending"):
        GenerationBatch(
            "batch-1",
            1,
            (ShotRequestEntry(2, _request(2)), ShotRequestEntry(1, _request(1))),
            10.0,
        )


def test_plan_rejects_incorrect_batch_count() -> None:
    batch = GenerationBatch("batch-1", 1, (ShotRequestEntry(1, _request(1)),), 5.0)
    with pytest.raises(GenerationBatchPlanningError, match="batch_count"):
        EpisodeGenerationBatchPlan(
            "plan-1", "manifest-1", "episode-1", (batch,), 2, 1, 5.0, {}
        )


def test_plan_copies_metadata_before_freezing() -> None:
    batch = GenerationBatch("batch-1", 1, (ShotRequestEntry(1, _request(1)),), 5.0)
    metadata = {"key": "value"}
    plan = EpisodeGenerationBatchPlan(
        "plan-1", "manifest-1", "episode-1", (batch,), 1, 1, 5.0, metadata
    )
    metadata["key"] = "changed"
    assert plan.metadata["key"] == "value"


def test_planning_contains_no_provider_or_execution_result() -> None:
    plan = EpisodeGenerationBatchPlanner().plan(_manifest())
    assert not hasattr(plan, "provider")
    assert not hasattr(plan, "result")
