"""Deterministic provider-neutral planning for cinematic shot generation.

This module converts an approved :class:`ShotPromptPackage` into an auditable
request contract. It does not select a provider, call an external service,
render media, retry work, or invent creative facts.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256
from types import MappingProxyType

from .prompt_compilation import ShotPromptPackage


class ShotRequestPlanningError(ValueError):
    """Raised when an approved prompt cannot form a valid request plan."""


@dataclass(frozen=True, slots=True)
class ShotGenerationPolicy:
    """Explicit constraints used to plan one video-generation request."""

    aspect_ratio: str = "9:16"
    frames_per_second: int = 24
    output_count: int = 1
    seed: int | None = None

    def __post_init__(self) -> None:
        _require_non_blank("aspect_ratio", self.aspect_ratio)
        if self.frames_per_second <= 0:
            raise ShotRequestPlanningError(
                "frames_per_second must be greater than zero"
            )
        if self.output_count <= 0:
            raise ShotRequestPlanningError("output_count must be greater than zero")
        if self.seed is not None and self.seed < 0:
            raise ShotRequestPlanningError("seed must be zero or greater")


@dataclass(frozen=True, slots=True)
class ShotGenerationRequest:
    """Provider-neutral, immutable request contract for one cinematic shot."""

    request_id: str
    idempotency_key: str
    shot_id: str
    source_beat_id: str
    prompt_text: str
    duration_seconds: float
    aspect_ratio: str
    frames_per_second: int
    output_count: int
    seed: int | None
    metadata: Mapping[str, str]

    def __post_init__(self) -> None:
        _require_non_blank("request_id", self.request_id)
        _require_non_blank("idempotency_key", self.idempotency_key)
        _require_non_blank("shot_id", self.shot_id)
        _require_non_blank("source_beat_id", self.source_beat_id)
        _require_non_blank("prompt_text", self.prompt_text)
        _require_non_blank("aspect_ratio", self.aspect_ratio)
        if self.duration_seconds <= 0:
            raise ShotRequestPlanningError(
                "duration_seconds must be greater than zero"
            )
        if self.frames_per_second <= 0:
            raise ShotRequestPlanningError(
                "frames_per_second must be greater than zero"
            )
        if self.output_count <= 0:
            raise ShotRequestPlanningError("output_count must be greater than zero")
        if self.seed is not None and self.seed < 0:
            raise ShotRequestPlanningError("seed must be zero or greater")
        normalized = dict(self.metadata)
        for key, value in normalized.items():
            _require_non_blank("metadata key", key)
            _require_non_blank(f"metadata value for {key}", value)
        object.__setattr__(self, "metadata", MappingProxyType(normalized))


class ShotGenerationRequestPlanner:
    """Create stable request contracts from already-approved prompt packages."""

    def __init__(self, policy: ShotGenerationPolicy | None = None) -> None:
        self._policy = policy or ShotGenerationPolicy()

    def plan(self, package: ShotPromptPackage) -> ShotGenerationRequest:
        """Build one deterministic request without provider selection or I/O."""

        canonical = _canonical_request_material(package, self._policy)
        digest = sha256(canonical.encode("utf-8")).hexdigest()
        request_id = f"shot-request-{digest[:16]}"
        metadata = {
            "shot_id": package.shot_id,
            "source_beat_id": package.source_beat_id,
            "prompt_sha256": sha256(
                package.prompt_text.encode("utf-8")
            ).hexdigest(),
        }
        return ShotGenerationRequest(
            request_id=request_id,
            idempotency_key=digest,
            shot_id=package.shot_id,
            source_beat_id=package.source_beat_id,
            prompt_text=package.prompt_text,
            duration_seconds=package.duration_seconds,
            aspect_ratio=self._policy.aspect_ratio,
            frames_per_second=self._policy.frames_per_second,
            output_count=self._policy.output_count,
            seed=self._policy.seed,
            metadata=metadata,
        )


def _canonical_request_material(
    package: ShotPromptPackage,
    policy: ShotGenerationPolicy,
) -> str:
    seed = "none" if policy.seed is None else str(policy.seed)
    return "\n".join(
        (
            f"shot_id={package.shot_id}",
            f"source_beat_id={package.source_beat_id}",
            f"duration_seconds={_format_duration(package.duration_seconds)}",
            f"aspect_ratio={policy.aspect_ratio}",
            f"frames_per_second={policy.frames_per_second}",
            f"output_count={policy.output_count}",
            f"seed={seed}",
            f"prompt_sha256={sha256(package.prompt_text.encode('utf-8')).hexdigest()}",
        )
    )


def _format_duration(value: float) -> str:
    return f"{value:.3f}".rstrip("0").rstrip(".")


def _require_non_blank(name: str, value: str) -> None:
    if not value.strip():
        raise ShotRequestPlanningError(f"{name} must not be blank")
