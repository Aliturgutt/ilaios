"""Provider-neutral product intent for the canonical ILAIOS Video Factory.

This module does not generate media, route providers, authorize spend, or replace
any existing Video Factory planner. It resolves a bounded product mode before
provider execution so unsupported edit/localization, series-continuity or output-
shape requests fail closed instead of silently degrading into another product.
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
    r"\bepisodic\b",
    r"\bseri\b",
    r"\bnext episode\b",
    r"\bprevious episode\b",
    r"\bexisting episode\b",
    r"\bsonraki bölüm\b",
    r"\bsonraki bolum\b",
    r"\bönceki bölüm\b",
    r"\bonceki bolum\b",
    r"\bmevcut bölüm\b",
    r"\bmevcut bolum\b",
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
        audio_policy="current-provider-runtime-generates-audio-and-requires-signal-pass",
        caption_policy="safe-area-and-timing-validation-when-captions-are-requested",
    )


def validate_video_product_inputs(
    spec: VideoProductSpec,
    *,
    source_video_present: bool,
    series_state_present: bool = False,
    supported_aspect_ratios: tuple[str, ...] = ("16:9",),
) -> None:
    """Fail closed when requested inputs/output shape cannot be materialized exactly."""

    if spec.source_video_required and not source_video_present:
        raise VideoProductIntentError(
            f"video mode '{spec.mode.value}' requires an authenticated source video; "
            "image references cannot be treated as source-video edit input"
        )
    if spec.series_continuity_required and not series_state_present:
        raise VideoProductIntentError(
            "series Video intent requires an authenticated canonical series-state binding; "
            "a standalone objective cannot prove cross-episode continuity"
        )
    if spec.mode is VideoProductMode.REFERENCE_TO_VIDEO and spec.reference_count == 0:
        raise VideoProductIntentError("reference-to-video requires at least one reference")
    if spec.aspect_ratio not in supported_aspect_ratios:
        raise VideoProductIntentError(
            f"requested aspect ratio '{spec.aspect_ratio}' is not materialized by the "
            "current finished-product runtime; refusing to return a mismatched video"
        )


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
