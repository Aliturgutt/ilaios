from __future__ import annotations

from types import MappingProxyType

import pytest

from src.video_automation.generation_batch_planning import (
    EpisodeGenerationBatchPlanner,
    GenerationBatchPolicy,
)
from src.video_automation.generation_dispatch_planning import (
    EpisodeGenerationDispatchPlan,
    EpisodeGenerationDispatchPlanner,
    GenerationProviderBinding,
)
from src.video_automation.generation_execution_tracking import (
    EpisodeGenerationExecutionState,
    EpisodeGenerationExecutionTracker,
    GenerationDispatchExecution,
    GenerationExecutionStatus,
    GenerationExecutionTrackingError,
    GenerationExecutionUpdate,
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


def _dispatch_plan(count: int = 3) -> EpisodeGenerationDispatchPlan:
    manifest = EpisodeRequestManifestBuilder().build(
        "episode-001", [_request(number) for number in range(1, count + 1)]
    )
    generation_plan = EpisodeGenerationBatchPlanner(
        GenerationBatchPolicy(max_requests_per_batch=1)
    ).plan(manifest)
    return EpisodeGenerationDispatchPlanner(
        GenerationProviderBinding("provider-alpha", "model-cinematic-v1")
    ).plan(generation_plan)


def _record(
    status: GenerationExecutionStatus = GenerationExecutionStatus.PENDING,
) -> GenerationDispatchExecution:
    provider_job_id = None
    output_asset_ids: tuple[str, ...] = ()
    error_code = None
    if status in {
        GenerationExecutionStatus.SUBMITTED,
        GenerationExecutionStatus.RUNNING,
        GenerationExecutionStatus.SUCCEEDED,
    }:
        provider_job_id = "job-001"
    if status is GenerationExecutionStatus.SUCCEEDED:
        output_asset_ids = ("asset-001",)
    if status is GenerationExecutionStatus.FAILED:
        error_code = "provider_error"
    return GenerationDispatchExecution(
        dispatch_id="dispatch-001",
        batch_id="batch-001",
        batch_number=1,
        status=status,
        revision=0,
        provider_job_id=provider_job_id,
        output_asset_ids=output_asset_ids,
        error_code=error_code,
        error_message=None,
        metadata={},
    )


def test_initialize_creates_pending_record_per_dispatch() -> None:
    state = EpisodeGenerationExecutionTracker().initialize(_dispatch_plan(3))
    assert len(state.records) == 3
    assert all(
        record.status is GenerationExecutionStatus.PENDING
        for record in state.records
    )


def test_initialize_preserves_dispatch_order() -> None:
    plan = _dispatch_plan(3)
    state = EpisodeGenerationExecutionTracker().initialize(plan)
    assert [record.dispatch_id for record in state.records] == [
        dispatch.dispatch_id for dispatch in plan.dispatches
    ]


def test_initialize_is_deterministic() -> None:
    plan = _dispatch_plan()
    tracker = EpisodeGenerationExecutionTracker()
    assert tracker.initialize(plan).execution_state_id == tracker.initialize(
        plan
    ).execution_state_id


def test_apply_advances_pending_to_submitted() -> None:
    plan = _dispatch_plan(1)
    tracker = EpisodeGenerationExecutionTracker()
    current = tracker.initialize(plan)
    updated = tracker.apply(
        plan,
        current,
        GenerationExecutionUpdate(
            plan.dispatches[0].dispatch_id,
            GenerationExecutionStatus.SUBMITTED,
            provider_job_id="job-001",
        ),
    )
    assert updated.records[0].status is GenerationExecutionStatus.SUBMITTED
    assert updated.records[0].revision == 1


def test_apply_preserves_unmodified_records() -> None:
    plan = _dispatch_plan(2)
    tracker = EpisodeGenerationExecutionTracker()
    current = tracker.initialize(plan)
    updated = tracker.apply(
        plan,
        current,
        GenerationExecutionUpdate(
            plan.dispatches[0].dispatch_id,
            GenerationExecutionStatus.CANCELLED,
        ),
    )
    assert updated.records[1] == current.records[1]


def test_succeeded_update_records_assets_and_count() -> None:
    plan = _dispatch_plan(1)
    tracker = EpisodeGenerationExecutionTracker()
    submitted = tracker.apply(
        plan,
        tracker.initialize(plan),
        GenerationExecutionUpdate(
            plan.dispatches[0].dispatch_id,
            GenerationExecutionStatus.SUBMITTED,
            provider_job_id="job-001",
        ),
    )
    succeeded = tracker.apply(
        plan,
        submitted,
        GenerationExecutionUpdate(
            plan.dispatches[0].dispatch_id,
            GenerationExecutionStatus.SUCCEEDED,
            provider_job_id="job-001",
            output_asset_ids=("asset-001",),
        ),
    )
    assert succeeded.completed_count == 1
    assert succeeded.records[0].output_asset_ids == ("asset-001",)
    assert succeeded.is_terminal


def test_failed_update_records_error_and_count() -> None:
    plan = _dispatch_plan(1)
    tracker = EpisodeGenerationExecutionTracker()
    submitted = tracker.apply(
        plan,
        tracker.initialize(plan),
        GenerationExecutionUpdate(
            plan.dispatches[0].dispatch_id,
            GenerationExecutionStatus.SUBMITTED,
            provider_job_id="job-001",
        ),
    )
    failed = tracker.apply(
        plan,
        submitted,
        GenerationExecutionUpdate(
            plan.dispatches[0].dispatch_id,
            GenerationExecutionStatus.FAILED,
            error_code="provider_error",
            error_message="generation rejected",
        ),
    )
    assert failed.failed_count == 1
    assert failed.records[0].error_code == "provider_error"


def test_terminal_state_rejects_further_transition() -> None:
    plan = _dispatch_plan(1)
    tracker = EpisodeGenerationExecutionTracker()
    cancelled = tracker.apply(
        plan,
        tracker.initialize(plan),
        GenerationExecutionUpdate(
            plan.dispatches[0].dispatch_id,
            GenerationExecutionStatus.CANCELLED,
        ),
    )
    with pytest.raises(GenerationExecutionTrackingError, match="invalid transition"):
        tracker.apply(
            plan,
            cancelled,
            GenerationExecutionUpdate(
                plan.dispatches[0].dispatch_id,
                GenerationExecutionStatus.SUBMITTED,
                provider_job_id="job-001",
            ),
        )


def test_apply_rejects_unknown_dispatch() -> None:
    plan = _dispatch_plan(1)
    tracker = EpisodeGenerationExecutionTracker()
    with pytest.raises(GenerationExecutionTrackingError, match="unknown dispatch_id"):
        tracker.apply(
            plan,
            tracker.initialize(plan),
            GenerationExecutionUpdate(
                "unknown-dispatch",
                GenerationExecutionStatus.CANCELLED,
            ),
        )


def test_apply_rejects_state_from_other_plan() -> None:
    first = _dispatch_plan(1)
    second = _dispatch_plan(2)
    tracker = EpisodeGenerationExecutionTracker()
    with pytest.raises(GenerationExecutionTrackingError, match="does not belong"):
        tracker.apply(
            second,
            tracker.initialize(first),
            GenerationExecutionUpdate(
                second.dispatches[0].dispatch_id,
                GenerationExecutionStatus.CANCELLED,
            ),
        )


def test_submitted_update_requires_provider_job_id() -> None:
    with pytest.raises(GenerationExecutionTrackingError, match="provider_job_id"):
        GenerationExecutionUpdate(
            "dispatch-001", GenerationExecutionStatus.SUBMITTED
        )


def test_succeeded_update_requires_output_asset() -> None:
    with pytest.raises(GenerationExecutionTrackingError, match="output_asset_ids"):
        GenerationExecutionUpdate(
            "dispatch-001",
            GenerationExecutionStatus.SUCCEEDED,
            provider_job_id="job-001",
        )


def test_failed_update_requires_error_code() -> None:
    with pytest.raises(GenerationExecutionTrackingError, match="error_code"):
        GenerationExecutionUpdate(
            "dispatch-001", GenerationExecutionStatus.FAILED
        )


def test_non_failed_update_rejects_error_details() -> None:
    with pytest.raises(GenerationExecutionTrackingError, match="error details"):
        GenerationExecutionUpdate(
            "dispatch-001",
            GenerationExecutionStatus.CANCELLED,
            error_code="unexpected",
        )


def test_update_metadata_is_immutable() -> None:
    update = GenerationExecutionUpdate(
        "dispatch-001",
        GenerationExecutionStatus.CANCELLED,
        metadata={"reason": "operator_request"},
    )
    assert isinstance(update.metadata, MappingProxyType)
    with pytest.raises(TypeError):
        update.metadata["reason"] = "changed"  # type: ignore[index]


def test_record_reports_terminal_status() -> None:
    assert _record(GenerationExecutionStatus.SUCCEEDED).is_terminal
    assert not _record(GenerationExecutionStatus.PENDING).is_terminal


def test_state_rejects_incorrect_completed_count() -> None:
    record = _record(GenerationExecutionStatus.SUCCEEDED)
    with pytest.raises(GenerationExecutionTrackingError, match="completed_count"):
        EpisodeGenerationExecutionState(
            "state-1",
            "dispatch-plan-1",
            "generation-plan-1",
            "manifest-1",
            "episode-1",
            (record,),
            0,
            0,
            0,
            {},
        )
