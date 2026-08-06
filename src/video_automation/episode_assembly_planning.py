"""Deterministic episode assembly planning for validated generation assets.

This module consumes an immutable generation validation manifest and produces
an immutable, ordered assembly plan. It does not inspect media, edit media,
render timelines, choose transitions, infer durations, or call providers.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256
from types import MappingProxyType

from .generation_result_validation import (
    EpisodeGenerationValidationManifest,
    GenerationAssetValidationStatus,
)


class EpisodeAssemblyPlanningError(ValueError):
    """Raised when validated generation assets cannot be assembled safely."""


@dataclass(frozen=True, slots=True)
class EpisodeAssemblyClip:
    """Immutable ordered reference to one accepted generated asset."""

    sequence_number: int
    asset_id: str
    dispatch_id: str
    provider_job_id: str
    batch_number: int
    output_index: int
    metadata: Mapping[str, str]

    def __post_init__(self) -> None:
        if self.sequence_number <= 0:
            raise EpisodeAssemblyPlanningError(
                "sequence_number must be greater than zero"
            )
        _require_non_blank("asset_id", self.asset_id)
        _require_non_blank("dispatch_id", self.dispatch_id)
        _require_non_blank("provider_job_id", self.provider_job_id)
        if self.batch_number <= 0:
            raise EpisodeAssemblyPlanningError("batch_number must be greater than zero")
        if self.output_index <= 0:
            raise EpisodeAssemblyPlanningError("output_index must be greater than zero")
        object.__setattr__(self, "metadata", _freeze_metadata(self.metadata))


@dataclass(frozen=True, slots=True)
class EpisodeAssemblyPlan:
    """Immutable deterministic assembly plan for one validated episode."""

    assembly_plan_id: str
    validation_manifest_id: str
    result_manifest_id: str
    execution_state_id: str
    episode_id: str
    clips: tuple[EpisodeAssemblyClip, ...]
    metadata: Mapping[str, str]

    def __post_init__(self) -> None:
        _require_non_blank("assembly_plan_id", self.assembly_plan_id)
        _require_non_blank("validation_manifest_id", self.validation_manifest_id)
        _require_non_blank("result_manifest_id", self.result_manifest_id)
        _require_non_blank("execution_state_id", self.execution_state_id)
        _require_non_blank("episode_id", self.episode_id)
        expected_sequence = tuple(range(1, len(self.clips) + 1))
        actual_sequence = tuple(clip.sequence_number for clip in self.clips)
        if actual_sequence != expected_sequence:
            raise EpisodeAssemblyPlanningError(
                "clip sequence_numbers must be contiguous and start at one"
            )
        asset_ids = tuple(clip.asset_id for clip in self.clips)
        if len(asset_ids) != len(set(asset_ids)):
            raise EpisodeAssemblyPlanningError("assembly clip asset_ids must be unique")
        object.__setattr__(self, "metadata", _freeze_metadata(self.metadata))


class EpisodeAssemblyPlanner:
    """Create an ordered assembly plan from explicitly accepted assets only."""

    def plan(
        self, validation_manifest: EpisodeGenerationValidationManifest
    ) -> EpisodeAssemblyPlan:
        """Build an assembly plan without inspecting or modifying media."""

        if not validation_manifest.all_accepted:
            raise EpisodeAssemblyPlanningError(
                "all generation assets must be accepted before assembly planning"
            )

        clips = tuple(
            EpisodeAssemblyClip(
                sequence_number=index,
                asset_id=asset.asset_id,
                dispatch_id=asset.dispatch_id,
                provider_job_id=asset.provider_job_id,
                batch_number=asset.batch_number,
                output_index=asset.output_index,
                metadata={"validation_status": asset.status.value},
            )
            for index, asset in enumerate(validation_manifest.assets, start=1)
        )

        for asset in validation_manifest.assets:
            if asset.status is not GenerationAssetValidationStatus.ACCEPTED:
                raise EpisodeAssemblyPlanningError(
                    "assembly planning requires accepted assets only"
                )

        canonical = _canonical_assembly_material(validation_manifest, clips)
        digest = sha256(canonical.encode("utf-8")).hexdigest()
        return EpisodeAssemblyPlan(
            assembly_plan_id=f"episode-assembly-{digest[:16]}",
            validation_manifest_id=validation_manifest.validation_manifest_id,
            result_manifest_id=validation_manifest.result_manifest_id,
            execution_state_id=validation_manifest.execution_state_id,
            episode_id=validation_manifest.episode_id,
            clips=clips,
            metadata={"clip_count": str(len(clips))},
        )


def _canonical_assembly_material(
    validation_manifest: EpisodeGenerationValidationManifest,
    clips: tuple[EpisodeAssemblyClip, ...],
) -> str:
    lines = [
        f"validation_manifest_id={validation_manifest.validation_manifest_id}",
        f"result_manifest_id={validation_manifest.result_manifest_id}",
        f"execution_state_id={validation_manifest.execution_state_id}",
        f"episode_id={validation_manifest.episode_id}",
    ]
    lines.extend(
        f"sequence={clip.sequence_number}|asset_id={clip.asset_id}|"
        f"dispatch_id={clip.dispatch_id}|provider_job_id={clip.provider_job_id}|"
        f"batch={clip.batch_number}|output_index={clip.output_index}"
        for clip in clips
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
        raise EpisodeAssemblyPlanningError(f"{name} must not be blank")
