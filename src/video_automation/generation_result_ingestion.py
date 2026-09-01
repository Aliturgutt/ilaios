"""Deterministic ingestion of completed generation execution results.

This module converts an already-terminal generation execution state into an
immutable episode result manifest. It does not call providers, fetch media,
download assets, inspect media contents, retry failed work, or infer outcomes.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256
from types import MappingProxyType

from .generation_execution_tracking import (
    EpisodeGenerationExecutionState,
    GenerationDispatchExecution,
    GenerationExecutionStatus,
)


class GenerationResultIngestionError(ValueError):
    """Raised when execution results cannot be ingested deterministically."""


@dataclass(frozen=True, slots=True)
class GenerationResultAsset:
    """Immutable reference to one externally produced generation asset."""

    asset_id: str
    dispatch_id: str
    provider_job_id: str
    batch_number: int
    output_index: int
    metadata: Mapping[str, str]

    def __post_init__(self) -> None:
        _require_non_blank("asset_id", self.asset_id)
        _require_non_blank("dispatch_id", self.dispatch_id)
        _require_non_blank("provider_job_id", self.provider_job_id)
        if self.batch_number <= 0:
            raise GenerationResultIngestionError(
                "batch_number must be greater than zero"
            )
        if self.output_index <= 0:
            raise GenerationResultIngestionError(
                "output_index must be greater than zero"
            )
        object.__setattr__(self, "metadata", _freeze_metadata(self.metadata))


@dataclass(frozen=True, slots=True)
class EpisodeGenerationResultManifest:
    """Immutable result manifest derived from one terminal execution state."""

    result_manifest_id: str
    execution_state_id: str
    dispatch_plan_id: str
    generation_plan_id: str
    request_manifest_id: str
    episode_id: str
    assets: tuple[GenerationResultAsset, ...]
    dispatch_count: int
    succeeded_count: int
    failed_count: int
    cancelled_count: int
    metadata: Mapping[str, str]

    def __post_init__(self) -> None:
        _require_non_blank("result_manifest_id", self.result_manifest_id)
        _require_non_blank("execution_state_id", self.execution_state_id)
        _require_non_blank("dispatch_plan_id", self.dispatch_plan_id)
        _require_non_blank("generation_plan_id", self.generation_plan_id)
        _require_non_blank("request_manifest_id", self.request_manifest_id)
        _require_non_blank("episode_id", self.episode_id)
        if self.dispatch_count <= 0:
            raise GenerationResultIngestionError(
                "dispatch_count must be greater than zero"
            )
        for name, value in (
            ("succeeded_count", self.succeeded_count),
            ("failed_count", self.failed_count),
            ("cancelled_count", self.cancelled_count),
        ):
            if value < 0:
                raise GenerationResultIngestionError(f"{name} must not be negative")
        if (
            self.succeeded_count + self.failed_count + self.cancelled_count
            != self.dispatch_count
        ):
            raise GenerationResultIngestionError(
                "terminal dispatch counts must equal dispatch_count"
            )
        asset_ids = tuple(asset.asset_id for asset in self.assets)
        if len(asset_ids) != len(set(asset_ids)):
            raise GenerationResultIngestionError("asset_ids must be unique")
        object.__setattr__(self, "metadata", _freeze_metadata(self.metadata))


class EpisodeGenerationResultIngester:
    """Build a result manifest from explicit terminal execution records."""

    def ingest(
        self, execution_state: EpisodeGenerationExecutionState
    ) -> EpisodeGenerationResultManifest:
        """Ingest terminal execution records without performing external I/O."""

        if not execution_state.is_terminal:
            raise GenerationResultIngestionError(
                "execution_state must be terminal before result ingestion"
            )

        assets: list[GenerationResultAsset] = []
        seen_asset_ids: set[str] = set()
        for record in execution_state.records:
            if record.status is not GenerationExecutionStatus.SUCCEEDED:
                continue
            _validate_succeeded_record(record)
            assert record.provider_job_id is not None
            for output_index, asset_id in enumerate(record.output_asset_ids, start=1):
                if asset_id in seen_asset_ids:
                    raise GenerationResultIngestionError(
                        f"duplicate output asset_id across dispatches: {asset_id}"
                    )
                seen_asset_ids.add(asset_id)
                assets.append(
                    GenerationResultAsset(
                        asset_id=asset_id,
                        dispatch_id=record.dispatch_id,
                        provider_job_id=record.provider_job_id,
                        batch_number=record.batch_number,
                        output_index=output_index,
                        metadata={"source_status": record.status.value},
                    )
                )

        canonical = _canonical_manifest_material(execution_state, tuple(assets))
        digest = sha256(canonical.encode("utf-8")).hexdigest()
        return EpisodeGenerationResultManifest(
            result_manifest_id=f"generation-result-{digest[:16]}",
            execution_state_id=execution_state.execution_state_id,
            dispatch_plan_id=execution_state.dispatch_plan_id,
            generation_plan_id=execution_state.generation_plan_id,
            request_manifest_id=execution_state.manifest_id,
            episode_id=execution_state.episode_id,
            assets=tuple(assets),
            dispatch_count=len(execution_state.records),
            succeeded_count=execution_state.completed_count,
            failed_count=execution_state.failed_count,
            cancelled_count=execution_state.cancelled_count,
            metadata={"asset_count": str(len(assets))},
        )


def _validate_succeeded_record(record: GenerationDispatchExecution) -> None:
    if record.provider_job_id is None:
        raise GenerationResultIngestionError(
            "succeeded execution record must contain provider_job_id"
        )
    if not record.output_asset_ids:
        raise GenerationResultIngestionError(
            "succeeded execution record must contain output_asset_ids"
        )


def _canonical_manifest_material(
    execution_state: EpisodeGenerationExecutionState,
    assets: tuple[GenerationResultAsset, ...],
) -> str:
    lines = [
        f"execution_state_id={execution_state.execution_state_id}",
        f"dispatch_plan_id={execution_state.dispatch_plan_id}",
        f"generation_plan_id={execution_state.generation_plan_id}",
        f"request_manifest_id={execution_state.manifest_id}",
        f"episode_id={execution_state.episode_id}",
        f"completed={execution_state.completed_count}",
        f"failed={execution_state.failed_count}",
        f"cancelled={execution_state.cancelled_count}",
    ]
    lines.extend(
        f"asset_id={asset.asset_id}|dispatch_id={asset.dispatch_id}|"
        f"provider_job_id={asset.provider_job_id}|batch={asset.batch_number}|"
        f"output_index={asset.output_index}"
        for asset in assets
    )
    return "\n".join(lines)


def _freeze_metadata(metadata: Mapping[str, str]) -> Mapping[str, str]:
    normalized = dict(metadata)
    for key, value in normalized.items():
        _require_non_blank("metadata key", key)
        _require_non_blank(f"metadata value for {key}", value)
    return MappingProxyType(normalized)


def _require_non_blank(name: str, value: str) -> None:
    if not value.strip():
        raise GenerationResultIngestionError(f"{name} must not be blank")
