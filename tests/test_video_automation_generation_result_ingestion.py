from __future__ import annotations

from types import MappingProxyType

import pytest

from src.video_automation.generation_execution_tracking import (
    EpisodeGenerationExecutionState,
    GenerationDispatchExecution,
    GenerationExecutionStatus,
)
from src.video_automation.generation_result_ingestion import (
    EpisodeGenerationResultIngester,
    EpisodeGenerationResultManifest,
    GenerationResultAsset,
    GenerationResultIngestionError,
)


def _record(
    number: int,
    status: GenerationExecutionStatus,
    assets: tuple[str, ...] = (),
) -> GenerationDispatchExecution:
    provider_job_id = None
    error_code = None
    if status is GenerationExecutionStatus.SUCCEEDED:
        provider_job_id = f"job-{number:02d}"
    elif status is GenerationExecutionStatus.FAILED:
        error_code = "provider_error"
    return GenerationDispatchExecution(
        dispatch_id=f"dispatch-{number:02d}",
        batch_id=f"batch-{number:02d}",
        batch_number=number,
        status=status,
        revision=1,
        provider_job_id=provider_job_id,
        output_asset_ids=assets,
        error_code=error_code,
        error_message=None,
        metadata={},
    )


def _state(
    records: tuple[GenerationDispatchExecution, ...],
) -> EpisodeGenerationExecutionState:
    return EpisodeGenerationExecutionState(
        execution_state_id="execution-state-001",
        dispatch_plan_id="dispatch-plan-001",
        generation_plan_id="generation-plan-001",
        manifest_id="request-manifest-001",
        episode_id="episode-001",
        records=records,
        completed_count=sum(
            record.status is GenerationExecutionStatus.SUCCEEDED
            for record in records
        ),
        failed_count=sum(
            record.status is GenerationExecutionStatus.FAILED for record in records
        ),
        cancelled_count=sum(
            record.status is GenerationExecutionStatus.CANCELLED
            for record in records
        ),
        metadata={},
    )


def test_ingest_collects_successful_output_assets() -> None:
    state = _state(
        (
            _record(1, GenerationExecutionStatus.SUCCEEDED, ("asset-a", "asset-b")),
            _record(2, GenerationExecutionStatus.FAILED),
        )
    )
    manifest = EpisodeGenerationResultIngester().ingest(state)
    assert [asset.asset_id for asset in manifest.assets] == ["asset-a", "asset-b"]


def test_ingest_preserves_dispatch_and_output_order() -> None:
    state = _state(
        (
            _record(1, GenerationExecutionStatus.SUCCEEDED, ("asset-a", "asset-b")),
            _record(2, GenerationExecutionStatus.SUCCEEDED, ("asset-c",)),
        )
    )
    manifest = EpisodeGenerationResultIngester().ingest(state)
    assert [(asset.batch_number, asset.output_index) for asset in manifest.assets] == [
        (1, 1),
        (1, 2),
        (2, 1),
    ]


def test_ingest_is_deterministic() -> None:
    state = _state((_record(1, GenerationExecutionStatus.SUCCEEDED, ("asset-a",)),))
    ingester = EpisodeGenerationResultIngester()
    assert ingester.ingest(state).result_manifest_id == ingester.ingest(
        state
    ).result_manifest_id


def test_ingest_retains_source_identifiers() -> None:
    manifest = EpisodeGenerationResultIngester().ingest(
        _state((_record(1, GenerationExecutionStatus.CANCELLED),))
    )
    assert manifest.execution_state_id == "execution-state-001"
    assert manifest.dispatch_plan_id == "dispatch-plan-001"
    assert manifest.generation_plan_id == "generation-plan-001"
    assert manifest.request_manifest_id == "request-manifest-001"
    assert manifest.episode_id == "episode-001"


def test_ingest_records_terminal_counts() -> None:
    manifest = EpisodeGenerationResultIngester().ingest(
        _state(
            (
                _record(1, GenerationExecutionStatus.SUCCEEDED, ("asset-a",)),
                _record(2, GenerationExecutionStatus.FAILED),
                _record(3, GenerationExecutionStatus.CANCELLED),
            )
        )
    )
    assert manifest.dispatch_count == 3
    assert manifest.succeeded_count == 1
    assert manifest.failed_count == 1
    assert manifest.cancelled_count == 1


def test_ingest_allows_terminal_state_without_successes() -> None:
    manifest = EpisodeGenerationResultIngester().ingest(
        _state(
            (
                _record(1, GenerationExecutionStatus.FAILED),
                _record(2, GenerationExecutionStatus.CANCELLED),
            )
        )
    )
    assert manifest.assets == ()
    assert manifest.metadata["asset_count"] == "0"


def test_ingest_rejects_non_terminal_state() -> None:
    state = _state((_record(1, GenerationExecutionStatus.PENDING),))
    with pytest.raises(GenerationResultIngestionError, match="must be terminal"):
        EpisodeGenerationResultIngester().ingest(state)


def test_ingest_rejects_duplicate_asset_ids_across_dispatches() -> None:
    state = _state(
        (
            _record(1, GenerationExecutionStatus.SUCCEEDED, ("asset-a",)),
            _record(2, GenerationExecutionStatus.SUCCEEDED, ("asset-a",)),
        )
    )
    with pytest.raises(GenerationResultIngestionError, match="duplicate output"):
        EpisodeGenerationResultIngester().ingest(state)


def test_result_asset_metadata_is_immutable() -> None:
    asset = GenerationResultAsset(
        "asset-a", "dispatch-01", "job-01", 1, 1, {"kind": "video"}
    )
    assert isinstance(asset.metadata, MappingProxyType)
    with pytest.raises(TypeError):
        asset.metadata["kind"] = "changed"  # type: ignore[index]


def test_manifest_metadata_is_immutable() -> None:
    manifest = EpisodeGenerationResultIngester().ingest(
        _state((_record(1, GenerationExecutionStatus.CANCELLED),))
    )
    assert isinstance(manifest.metadata, MappingProxyType)
    with pytest.raises(TypeError):
        manifest.metadata["asset_count"] = "1"  # type: ignore[index]


def test_result_asset_rejects_blank_asset_id() -> None:
    with pytest.raises(GenerationResultIngestionError, match="asset_id"):
        GenerationResultAsset(" ", "dispatch-01", "job-01", 1, 1, {})


def test_result_asset_rejects_non_positive_batch_number() -> None:
    with pytest.raises(GenerationResultIngestionError, match="batch_number"):
        GenerationResultAsset("asset-a", "dispatch-01", "job-01", 0, 1, {})


def test_result_asset_rejects_non_positive_output_index() -> None:
    with pytest.raises(GenerationResultIngestionError, match="output_index"):
        GenerationResultAsset("asset-a", "dispatch-01", "job-01", 1, 0, {})


def test_manifest_rejects_duplicate_asset_ids() -> None:
    first = GenerationResultAsset("asset-a", "dispatch-01", "job-01", 1, 1, {})
    second = GenerationResultAsset("asset-a", "dispatch-02", "job-02", 2, 1, {})
    with pytest.raises(GenerationResultIngestionError, match="asset_ids"):
        EpisodeGenerationResultManifest(
            "result-1",
            "state-1",
            "dispatch-plan-1",
            "generation-plan-1",
            "request-manifest-1",
            "episode-1",
            (first, second),
            2,
            2,
            0,
            0,
            {},
        )


def test_manifest_rejects_inconsistent_terminal_counts() -> None:
    with pytest.raises(GenerationResultIngestionError, match="must equal"):
        EpisodeGenerationResultManifest(
            "result-1",
            "state-1",
            "dispatch-plan-1",
            "generation-plan-1",
            "request-manifest-1",
            "episode-1",
            (),
            2,
            1,
            0,
            0,
            {},
        )


def test_asset_contains_provider_job_id_from_execution_record() -> None:
    manifest = EpisodeGenerationResultIngester().ingest(
        _state((_record(1, GenerationExecutionStatus.SUCCEEDED, ("asset-a",)),))
    )
    assert manifest.assets[0].provider_job_id == "job-01"


def test_asset_metadata_records_explicit_source_status() -> None:
    manifest = EpisodeGenerationResultIngester().ingest(
        _state((_record(1, GenerationExecutionStatus.SUCCEEDED, ("asset-a",)),))
    )
    assert manifest.assets[0].metadata["source_status"] == "succeeded"
