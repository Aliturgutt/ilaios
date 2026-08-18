"""Deterministic reference-image intent for the canonical Video Factory.

OpenRouter distinguishes reference-to-video guidance (``input_references``) from
exact first/last-frame control (``frame_images``).  This module prevents silent
mode changes: references are either used as general guidance or assigned to exact
frame anchors, and ambiguous/unused assets fail closed.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from enum import Enum
from typing import cast


class VideoReferenceIntentError(ValueError):
    """Raised when reference-image intent cannot be represented without loss."""


class VideoReferenceMode(str, Enum):
    GUIDANCE = "input_references"
    FRAME_CONTROL = "frame_images"


@dataclass(frozen=True, slots=True)
class FrameReference:
    asset_index: int
    frame_type: str

    def __post_init__(self) -> None:
        if self.asset_index < 0:
            raise VideoReferenceIntentError("frame reference index must not be negative")
        if self.frame_type not in {"first_frame", "last_frame"}:
            raise VideoReferenceIntentError("unsupported frame reference type")


@dataclass(frozen=True, slots=True)
class VideoReferencePlan:
    schema: str
    mode: VideoReferenceMode
    reference_count: int
    frame_references: tuple[FrameReference, ...] = ()

    def to_dict(self) -> dict[str, object]:
        value = cast(dict[str, object], asdict(self))
        value["mode"] = self.mode.value
        return value


_FIRST_FRAME_PATTERNS = (
    r"\bfirst[ -]frame\b",
    r"\bstarting[ -]frame\b",
    r"\bstart[ -]frame\b",
    r"\bilk kare\b",
    r"\bilk frame\b",
)
_LAST_FRAME_PATTERNS = (
    r"\blast[ -]frame\b",
    r"\bending[ -]frame\b",
    r"\bend[ -]frame\b",
    r"\bson kare\b",
    r"\bson frame\b",
)


def derive_video_reference_plan(
    objective: str,
    *,
    reference_count: int,
) -> VideoReferencePlan:
    if not isinstance(objective, str) or not objective.strip():
        raise VideoReferenceIntentError("reference objective must not be blank")
    if objective != objective.strip():
        raise VideoReferenceIntentError("reference objective must be normalized")
    if reference_count < 1 or reference_count > 20:
        raise VideoReferenceIntentError("reference count is outside supported bounds")

    normalized = " ".join(objective.casefold().split())
    wants_first = _matches(normalized, _FIRST_FRAME_PATTERNS)
    wants_last = _matches(normalized, _LAST_FRAME_PATTERNS)
    if not wants_first and not wants_last:
        return VideoReferencePlan(
            schema="ilaios.video-reference-plan.v1",
            mode=VideoReferenceMode.GUIDANCE,
            reference_count=reference_count,
        )

    required = int(wants_first) + int(wants_last)
    if reference_count != required:
        raise VideoReferenceIntentError(
            "exact frame-control intent requires exactly one image per requested "
            "first/last frame; extra or missing references would be silently ignored"
        )
    frames: list[FrameReference] = []
    if wants_first:
        frames.append(FrameReference(0, "first_frame"))
    if wants_last:
        index = 1 if wants_first else 0
        frames.append(FrameReference(index, "last_frame"))
    return VideoReferencePlan(
        schema="ilaios.video-reference-plan.v1",
        mode=VideoReferenceMode.FRAME_CONTROL,
        reference_count=reference_count,
        frame_references=tuple(frames),
    )


def _matches(value: str, patterns: tuple[str, ...]) -> bool:
    return any(re.search(pattern, value, flags=re.IGNORECASE) is not None for pattern in patterns)


__all__ = [
    "FrameReference",
    "VideoReferenceIntentError",
    "VideoReferenceMode",
    "VideoReferencePlan",
    "derive_video_reference_plan",
]
