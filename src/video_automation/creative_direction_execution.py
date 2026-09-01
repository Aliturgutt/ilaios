"""Deterministic execution of approved CreativeDirection over canonical shots.

This module applies already-approved cinematography intent to M09 ``Shot``
objects before M10 asset planning. It does not select providers, call models,
render media, create a second orchestrator, or bypass governance.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace
from hashlib import sha256

from .models import Shot
from .video_skills import CreativeDirection, VideoSkillError


class CinematographyExecutionError(VideoSkillError):
    """Raised when approved creative direction cannot be executed safely."""


@dataclass(frozen=True, slots=True)
class CinematographyExecutionResult:
    """Content-addressed result of one deterministic cinematography pass."""

    direction_id: str
    shots: tuple[Shot, ...]
    execution_sha256: str

    def __post_init__(self) -> None:
        if not self.direction_id or self.direction_id != self.direction_id.strip():
            raise CinematographyExecutionError(
                "direction_id must be non-blank and trimmed"
            )
        if not self.shots:
            raise CinematographyExecutionError("cinematography result requires shots")
        if len(self.execution_sha256) != 64 or any(
            character not in "0123456789abcdef"
            for character in self.execution_sha256
        ):
            raise CinematographyExecutionError(
                "execution_sha256 must be lowercase SHA-256"
            )


class CinematographyExecutor:
    """Apply one approved creative direction to ordered canonical M09 shots."""

    _DIRECTION_MARKER = "creative_direction_id: "

    def execute(
        self,
        shots: Sequence[Shot],
        direction: CreativeDirection,
    ) -> CinematographyExecutionResult:
        planned = tuple(shots)
        if not planned:
            raise CinematographyExecutionError("at least one shot is required")
        shot_ids = tuple(shot.shot_id for shot in planned)
        if len(shot_ids) != len(set(shot_ids)):
            raise CinematographyExecutionError("shot_id values must be unique")

        _validate_direction_collections(direction)

        directed: list[Shot] = []
        for shot in planned:
            if shot.generation_prompt.startswith(self._DIRECTION_MARKER):
                raise CinematographyExecutionError(
                    f"shot already has creative direction: {shot.shot_id}"
                )
            directed.append(
                replace(
                    shot,
                    camera_description=_camera_description(shot, direction),
                    framing=direction.shot_scale,
                    movement=direction.camera_movement,
                    generation_prompt=_generation_prompt(shot, direction),
                )
            )

        directed_shots = tuple(directed)
        digest_material = "\n".join(
            (
                f"direction_id={direction.direction_id}",
                *(
                    f"{shot.shot_id}={sha256(shot.generation_prompt.encode('utf-8')).hexdigest()}"
                    for shot in directed_shots
                ),
            )
        )
        return CinematographyExecutionResult(
            direction_id=direction.direction_id,
            shots=directed_shots,
            execution_sha256=sha256(digest_material.encode("utf-8")).hexdigest(),
        )


def _camera_description(shot: Shot, direction: CreativeDirection) -> str:
    return "; ".join(
        (
            f"base={shot.camera_description}",
            f"visual_intent={direction.visual_intent}",
            f"shot_scale={direction.shot_scale}",
            f"camera_angle={direction.camera_angle}",
            f"camera_movement={direction.camera_movement}",
            f"lighting={direction.lighting}",
            f"pacing={direction.pacing}",
        )
    )


def _generation_prompt(shot: Shot, direction: CreativeDirection) -> str:
    return "\n".join(
        (
            f"creative_direction_id: {direction.direction_id}",
            f"narrative_prompt: {shot.generation_prompt}",
            f"visual_intent: {direction.visual_intent}",
            f"shot_scale: {direction.shot_scale}",
            f"camera_angle: {direction.camera_angle}",
            f"camera_movement: {direction.camera_movement}",
            f"lighting: {direction.lighting}",
            f"palette: {' | '.join(direction.palette)}",
            f"pacing: {direction.pacing}",
            f"continuity_keys: {' | '.join(direction.continuity_keys)}",
        )
    )


def _validate_direction_collections(direction: CreativeDirection) -> None:
    _require_unique_trimmed("palette", direction.palette)
    _require_unique_trimmed("continuity_keys", direction.continuity_keys)


def _require_unique_trimmed(name: str, values: tuple[str, ...]) -> None:
    if not values:
        raise CinematographyExecutionError(f"{name} must not be empty")
    for value in values:
        if not value or value != value.strip():
            raise CinematographyExecutionError(
                f"{name} values must be non-blank and trimmed"
            )
    if len(values) != len(set(values)):
        raise CinematographyExecutionError(f"{name} values must be unique")
