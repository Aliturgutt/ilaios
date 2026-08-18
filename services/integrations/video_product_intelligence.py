"""Provider-neutral product intent for the canonical ILAIOS Video Factory.

This module does not generate media, route providers, authorize spend, or replace
any existing Video Factory planner.  It resolves a bounded product mode before
provider execution so unsupported edit/localization requests fail closed instead
of silently degrading into text-to-video generation.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from enum import Enum
from typing import cast


class VideoProductIntentError(ValueError):
    """Raised when a requested Video product mode cannot be safely materialized."""


class VideoProductMode(str, Enum):
    CREATE = "create"
    REFERENCE_TO_VIDEO = "reference-to-video"
    SERIES = "series"
    REVISION = "revision"
    LOCALIZATION = "localization"


@dataclass(frozen=True, slots=True)
class VideoProductSpec:
    schema: str
    mode: VideoProductMode
    objective: str
    aspect_ratio: str
    reference_count: int
    source_video_required: bool
    series_continuity_required: bool
    required_capabilities: tuple[str, ...]
    continuity_policy: str
    audio_policy: str
    caption_policy: str

    def to_dict(self) -> dict[str, object]:
        value = cast(dict[str, object], asdict(self))
        value["mode"] = self.mode.value
        return value


_REVISION_TERMS = (
    r"\brevise\b",
    r"\bedit\b",
    r"\bremix\b",
    r"\brework\b",
    r"\bmodify\b",
    r"\brevize\b",
    r"\bdüzenle\b",
    r"\bduzenle\b",
    r"\bdeğiştir\b",
    r"\bdegistir\b",
)
_LOCALIZATION_TERMS = (
    r"\blocali[sz]e\b",
    r"\bdub\b",
    r"\bdubbing\b",
    r"\btranslate the video\b",
    r"\bdublaj\b",
    r"\byerelleştir\b",
    r"\byerellestir\b",
)
_SERIES_TERMS = (
    r"\bseries\b",
    r"\bepisode\b",
    r"\bepisodic\b",
    r"\bseri\b",
    r"\bbölüm\b",
    r"\bbolum\b",
)


def derive_video_product_spec(
    objective: str,
    *,
    reference_count: int = 0,
) -> VideoProductSpec:
    """Resolve one bounded Video product mode from the authenticated objective."""

    if not isinstance(objective, str) or not objective.strip():
        raise VideoProductIntentError("video objective must not be blank")
    if objective != objective.strip():
        raise VideoProductIntentError("video objective must be normalized")
    if len(objective) > 20_000:
        raise VideoProductIntentError("video objective exceeds the input limit")
    if reference_count < 0 or reference_count > 20:
        raise VideoProductIntentError("video reference count is outside supported bounds")

    normalized = " ".join(objective.casefold().split())
    localization = _matches_any(normalized, _LOCALIZATION_TERMS)
    revision = _matches_any(normalized, _REVISION_TERMS)
    series = _matches_any(normalized, _SERIES_TERMS)

    if localization:
        mode = VideoProductMode.LOCALIZATION
    elif revision:
        mode = VideoProductMode.REVISION
    elif series:
        mode = VideoProductMode.SERIES
    elif reference_count:
        mode = VideoProductMode.REFERENCE_TO_VIDEO
    else:
        mode = VideoProductMode.CREATE

    source_required = mode in {
        VideoProductMode.REVISION,
        VideoProductMode.LOCALIZATION,
    }
    capabilities: list[str] = ["video.generate"]
    if reference_count:
        capabilities.append("video.reference")
    if series:
        capabilities.append("video.series-continuity")
    if mode is VideoProductMode.REVISION:
        capabilities.append("video.edit")
    elif mode is VideoProductMode.LOCALIZATION:
        capabilities.extend(("video.edit", "video.localize"))

    return VideoProductSpec(
        schema="ilaios.video-product-spec.v1",
        mode=mode,
        objective=objective,
        aspect_ratio=_aspect_ratio(normalized),
        reference_count=reference_count,
        source_video_required=source_required,
        series_continuity_required=series,
        required_capabilities=tuple(capabilities),
        continuity_policy=(
            "canonical-series-state-required"
            if series
            else "canonical-shot-continuity-required"
        ),
        audio_policy="preserve-or-generate-only-when-objective-requires-audio",
        caption_policy="safe-area-and-timing-validation-when-captions-are-requested",
    )


def validate_video_product_inputs(
    spec: VideoProductSpec,
    *,
    source_video_present: bool,
) -> None:
    """Fail closed when a mode requires source media the current request lacks."""

    if spec.source_video_required and not source_video_present:
        raise VideoProductIntentError(
            f"video mode '{spec.mode.value}' requires an authenticated source video; "
            "image references cannot be treated as source-video edit input"
        )
    if spec.mode is VideoProductMode.REFERENCE_TO_VIDEO and spec.reference_count == 0:
        raise VideoProductIntentError("reference-to-video requires at least one reference")


def _matches_any(value: str, patterns: tuple[str, ...]) -> bool:
    return any(re.search(pattern, value, flags=re.IGNORECASE) is not None for pattern in patterns)


def _aspect_ratio(normalized: str) -> str:
    if any(
        marker in normalized
        for marker in ("9:16", "vertical", "portrait", "tiktok", "reels", "shorts")
    ):
        return "9:16"
    if any(marker in normalized for marker in ("1:1", "square", "kare")):
        return "1:1"
    return "16:9"


__all__ = [
    "VideoProductIntentError",
    "VideoProductMode",
    "VideoProductSpec",
    "derive_video_product_spec",
    "validate_video_product_inputs",
]
