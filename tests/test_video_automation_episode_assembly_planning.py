from __future__ import annotations

from types import MappingProxyType

import pytest

from src.video_automation.episode_assembly_planning import (
    EpisodeAssemblyClip,
    EpisodeAssemblyPlan,
    EpisodeAssemblyPlanner,
    EpisodeAssemblyPlanningError,
)
from src.video_automation.generation_result_validation import (
    EpisodeGenerationValidationManifest,
    GenerationAssetValidationStatus,
    ValidatedGenerationAsset,
)


def _validated_asset(number: int, *, accepted: bool = True) -> ValidatedGenerationAsset:
    status = (
        GenerationAssetValidationStatus.ACCEPTED
        if accepted
        else GenerationAssetValidationStatus.REJECTED
    )
    return ValidatedGenerationAsset(
        asset_id=f"asset-{number:02d}",
        dispatch_id=f"dispatch-{number:02d}",
        provider_job_id=f"job-{number:02d}",
        batch_number=number,
        output_index=1,
        status=status,
        checks=("decode", "dimensions"),
        rejection_code=None if accepted else "invalid-output",
        metadata={"validator": "external"},
    )


def _manifest(count: int = 2) -> EpisodeGenerationValidationManifest:
    assets = tuple(_validated_asset(number) for number in range(1, count + 1))
    return EpisodeGenerationValidationManifest(
        validation_manifest_id="generation-validation-001",
        result_manifest_id="generation-result-001",
        execution_state_id="execution-state-001",
        episode_id="episode-001",
        assets=assets,
        accepted_count=count,
        rejected_count=0,
        metadata={"asset_count": str(count)},
    )


def test_plan_preserves_asset_order() -> None:
    plan = EpisodeAssemblyPlanner().plan(_manifest(3))
    assert [clip.asset_id for clip in plan.clips] == [
        "asset-01",
        "asset-02",
        "asset-03",
    ]


def test_plan_assigns_contiguous_sequence_numbers() -> None:
    plan = EpisodeAssemblyPlanner().plan(_manifest(3))
    assert [clip.sequence_number for clip in plan.clips] == [1, 2, 3]


def test_plan_copies_identity_fields() -> None:
    plan = EpisodeAssemblyPlanner().plan(_manifest(1))
    clip = plan.clips[0]
    assert clip.dispatch_id == "dispatch-01"
    assert clip.provider_job_id == "job-01"
    assert clip.batch_number == 1
    assert clip.output_index == 1


def test_plan_builds_deterministic_identifier() -> None:
    planner = EpisodeAssemblyPlanner()
    first = planner.plan(_manifest(2))
    second = planner.plan(_manifest(2))
    assert first.assembly_plan_id == second.assembly_plan_id


def test_plan_identifier_changes_with_order() -> None:
    manifest = _manifest(2)
    reversed_manifest = EpisodeGenerationValidationManifest(
        manifest.validation_manifest_id,
        manifest.result_manifest_id,
        manifest.execution_state_id,
        manifest.episode_id,
        tuple(reversed(manifest.assets)),
        2,
        0,
        {},
    )
    assert (
        EpisodeAssemblyPlanner().plan(manifest).assembly_plan_id
        != EpisodeAssemblyPlanner().plan(reversed_manifest).assembly_plan_id
    )


def test_plan_rejects_rejected_assets() -> None:
    manifest = EpisodeGenerationValidationManifest(
        "generation-validation-001",
        "generation-result-001",
        "execution-state-001",
        "episode-001",
        (_validated_asset(1, accepted=False),),
        0,
        1,
        {},
    )
    with pytest.raises(EpisodeAssemblyPlanningError, match="must be accepted"):
        EpisodeAssemblyPlanner().plan(manifest)


def test_plan_accepts_empty_fully_accepted_manifest() -> None:
    manifest = EpisodeGenerationValidationManifest(
        "generation-validation-empty",
        "generation-result-empty",
        "execution-state-empty",
        "episode-empty",
        (),
        0,
        0,
        {},
    )
    plan = EpisodeAssemblyPlanner().plan(manifest)
    assert plan.clips == ()


def test_plan_metadata_is_immutable() -> None:
    plan = EpisodeAssemblyPlanner().plan(_manifest(1))
    assert isinstance(plan.metadata, MappingProxyType)
    with pytest.raises(TypeError):
        plan.metadata["clip_count"] = "2"  # type: ignore[index]


def test_clip_metadata_is_immutable() -> None:
    clip = EpisodeAssemblyPlanner().plan(_manifest(1)).clips[0]
    assert isinstance(clip.metadata, MappingProxyType)
    with pytest.raises(TypeError):
        clip.metadata["validation_status"] = "rejected"  # type: ignore[index]


def test_clip_rejects_non_positive_sequence_number() -> None:
    with pytest.raises(EpisodeAssemblyPlanningError, match="sequence_number"):
        EpisodeAssemblyClip(0, "asset", "dispatch", "job", 1, 1, {})


def test_clip_rejects_non_positive_batch_number() -> None:
    with pytest.raises(EpisodeAssemblyPlanningError, match="batch_number"):
        EpisodeAssemblyClip(1, "asset", "dispatch", "job", 0, 1, {})


def test_clip_rejects_non_positive_output_index() -> None:
    with pytest.raises(EpisodeAssemblyPlanningError, match="output_index"):
        EpisodeAssemblyClip(1, "asset", "dispatch", "job", 1, 0, {})


def test_clip_rejects_blank_asset_id() -> None:
    with pytest.raises(EpisodeAssemblyPlanningError, match="asset_id"):
        EpisodeAssemblyClip(1, " ", "dispatch", "job", 1, 1, {})


def test_plan_rejects_non_contiguous_sequences() -> None:
    clip = EpisodeAssemblyClip(2, "asset", "dispatch", "job", 1, 1, {})
    with pytest.raises(EpisodeAssemblyPlanningError, match="contiguous"):
        EpisodeAssemblyPlan(
            "assembly-01",
            "validation-01",
            "result-01",
            "state-01",
            "episode-01",
            (clip,),
            {},
        )


def test_plan_rejects_duplicate_asset_ids() -> None:
    first = EpisodeAssemblyClip(1, "asset", "dispatch-1", "job-1", 1, 1, {})
    second = EpisodeAssemblyClip(2, "asset", "dispatch-2", "job-2", 2, 1, {})
    with pytest.raises(EpisodeAssemblyPlanningError, match="unique"):
        EpisodeAssemblyPlan(
            "assembly-01",
            "validation-01",
            "result-01",
            "state-01",
            "episode-01",
            (first, second),
            {},
        )


def test_plan_copies_manifest_identity() -> None:
    plan = EpisodeAssemblyPlanner().plan(_manifest(1))
    assert plan.validation_manifest_id == "generation-validation-001"
    assert plan.result_manifest_id == "generation-result-001"
    assert plan.execution_state_id == "execution-state-001"
    assert plan.episode_id == "episode-001"


def test_plan_records_accepted_validation_status() -> None:
    clip = EpisodeAssemblyPlanner().plan(_manifest(1)).clips[0]
    assert clip.metadata["validation_status"] == "accepted"
