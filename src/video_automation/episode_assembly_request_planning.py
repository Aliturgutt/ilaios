"""Deterministic episode assembly request planning.

This module converts an immutable episode assembly plan into an immutable,
provider-independent assembly request. It does not inspect or edit media,
render outputs, choose codecs, infer dimensions, or call external providers.
All output policy is supplied explicitly by the caller.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256
from types import MappingProxyType

from .episode_assembly_planning import EpisodeAssemblyPlan


class EpisodeAssemblyRequestPlanningError(ValueError):
    """Raised when an episode assembly request cannot be planned safely."""


@dataclass(frozen=True, slots=True)
class EpisodeAssemblyOutputPolicy:
    """Explicit immutable output requirements for an assembly request."""

    container_format: str
    video_codec: str
    audio_codec: str
    width: int
    height: int
    frame_rate: int

    def __post_init__(self) -> None:
        _require_non_blank("container_format", self.container_format)
        _require_non_blank("video_codec", self.video_codec)
        _require_non_blank("audio_codec", self.audio_codec)
        if self.width <= 0:
            raise EpisodeAssemblyRequestPlanningError("width must be greater than zero")
        if self.height <= 0:
            raise EpisodeAssemblyRequestPlanningError("height must be greater than zero")
        if self.frame_rate <= 0:
            raise EpisodeAssemblyRequestPlanningError(
                "frame_rate must be greater than zero"
            )


@dataclass(frozen=True, slots=True)
class EpisodeAssemblyRequestClip:
    """Immutable clip reference copied from the approved assembly plan."""

    sequence_number: int
    asset_id: str
    dispatch_id: str
    provider_job_id: str
    batch_number: int
    output_index: int

    def __post_init__(self) -> None:
        if self.sequence_number <= 0:
            raise EpisodeAssemblyRequestPlanningError(
                "sequence_number must be greater than zero"
            )
        _require_non_blank("asset_id", self.asset_id)
        _require_non_blank("dispatch_id", self.dispatch_id)
        _require_non_blank("provider_job_id", self.provider_job_id)
        if self.batch_number <= 0:
            raise EpisodeAssemblyRequestPlanningError(
                "batch_number must be greater than zero"
            )
        if self.output_index <= 0:
            raise EpisodeAssemblyRequestPlanningError(
                "output_index must be greater than zero"
            )


@dataclass(frozen=True, slots=True)
class EpisodeAssemblyRequest:
    """Immutable provider-independent request for episode assembly execution."""

    request_id: str
    assembly_plan_id: str
    validation_manifest_id: str
    episode_id: str
    clips: tuple[EpisodeAssemblyRequestClip, ...]
    output_policy: EpisodeAssemblyOutputPolicy
    metadata: Mapping[str, str]

    def __post_init__(self) -> None:
        _require_non_blank("request_id", self.request_id)
        _require_non_blank("assembly_plan_id", self.assembly_plan_id)
        _require_non_blank("validation_manifest_id", self.validation_manifest_id)
        _require_non_blank("episode_id", self.episode_id)
        if not self.clips:
            raise EpisodeAssemblyRequestPlanningError(
                "assembly request must contain at least one clip"
            )
        expected_sequence = tuple(range(1, len(self.clips) + 1))
        actual_sequence = tuple(clip.sequence_number for clip in self.clips)
        if actual_sequence != expected_sequence:
            raise EpisodeAssemblyRequestPlanningError(
                "request clip sequence_numbers must be contiguous and start at one"
            )
        asset_ids = tuple(clip.asset_id for clip in self.clips)
        if len(asset_ids) != len(set(asset_ids)):
            raise EpisodeAssemblyRequestPlanningError(
                "assembly request asset_ids must be unique"
            )
        object.__setattr__(self, "metadata", _freeze_metadata(self.metadata))


class EpisodeAssemblyRequestPlanner:
    """Create deterministic assembly requests from approved assembly plans."""

    def plan(
        self,
        assembly_plan: EpisodeAssemblyPlan,
        output_policy: EpisodeAssemblyOutputPolicy,
    ) -> EpisodeAssemblyRequest:
        """Build a provider-independent assembly request without rendering media."""

        if not assembly_plan.clips:
            raise EpisodeAssemblyRequestPlanningError(
                "assembly plan must contain at least one clip"
            )

        clips = tuple(
            EpisodeAssemblyRequestClip(
                sequence_number=clip.sequence_number,
                asset_id=clip.asset_id,
                dispatch_id=clip.dispatch_id,
                provider_job_id=clip.provider_job_id,
                batch_number=clip.batch_number,
                output_index=clip.output_index,
            )
            for clip in assembly_plan.clips
        )

        canonical = _canonical_request_material(assembly_plan, clips, output_policy)
        digest = sha256(canonical.encode("utf-8")).hexdigest()
        return EpisodeAssemblyRequest(
            request_id=f"episode-assembly-request-{digest[:16]}",
            assembly_plan_id=assembly_plan.assembly_plan_id,
            validation_manifest_id=assembly_plan.validation_manifest_id,
            episode_id=assembly_plan.episode_id,
            clips=clips,
            output_policy=output_policy,
            metadata={"clip_count": str(len(clips))},
        )


def _canonical_request_material(
    assembly_plan: EpisodeAssemblyPlan,
    clips: tuple[EpisodeAssemblyRequestClip, ...],
    output_policy: EpisodeAssemblyOutputPolicy,
) -> str:
    lines = [
        f"assembly_plan_id={assembly_plan.assembly_plan_id}",
        f"validation_manifest_id={assembly_plan.validation_manifest_id}",
        f"episode_id={assembly_plan.episode_id}",
        f"container_format={output_policy.container_format}",
        f"video_codec={output_policy.video_codec}",
        f"audio_codec={output_policy.audio_codec}",
        f"width={output_policy.width}",
        f"height={output_policy.height}",
        f"frame_rate={output_policy.frame_rate}",
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
        raise EpisodeAssemblyRequestPlanningError(f"{name} must not be blank")
