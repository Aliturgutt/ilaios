"""Fail-closed product intent admission for the canonical Desktop Video Factory.

This module does not generate media, choose providers, authorize spend, or create a
second Video runtime. It classifies only the minimum product-shape information
needed to prevent the current 16:9 create/reference runtime from silently claiming
unsupported revision, localization, series-continuation, or output-shape work.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from enum import Enum
from typing import cast


class VideoProductIntentError(ValueError):
    """Raised when a Video product request cannot be materialized truthfully."""


class VideoProductMode(str, Enum):
    CREATE = "create"
    REFERENCE_TO_VIDEO = "reference-to-video"
    SERIES_CONTINUATION = "series-continuation"
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
    series_state_required: bool

    def to_dict(self) -> dict[str, object]:
        value = cast(dict[str, object], asdict(self))
        value["mode"] = self.mode.value
        return value


_REVISION_PATTERNS = (
    r"\b(?:edit|revise|modify|rework|remix)\s+(?:this|the|my|existing|uploaded|source)\s+video\b",
    r"\b(?:this|the|my|existing|uploaded|source)\s+video\s+(?:edit|revision|remix)\b",
    r"\b(?:bu|mevcut|yüklediğim|yukledigim|kaynak)\s+videoyu\s+(?:düzenle|duzenle|değiştir|degistir|revize)\b",
)
_LOCALIZATION_PATTERNS = (
    r"\b(?:dub|localize|localise|translate)\s+(?:this|the|my|existing|uploaded|source)\s+video\b",
    r"\b(?:this|the|my|existing|uploaded|source)\s+video\s+(?:dub|dubbing|localization|localisation|translation)\b",
    r"\b(?:bu|mevcut|yüklediğim|yukledigim|kaynak)\s+videoyu\s+(?:dublaj|çevir|cevir|yerelleştir|yerellestir)\b",
)
_SERIES_PATTERNS = (
    r"\bepisode\s+\d+\b",
    r"\bpart\s+\d+\s+of\s+(?:the\s+)?series\b",
    r"\b(?:next|previous|existing)\s+episode\b",
    r"\b(?:bölüm|bolum)\s+\d+\b",
    r"\b(?:sonraki|önceki|onceki|mevcut)\s+(?:bölüm|bolum)\b",
)


def derive_video_product_spec(
    objective: str,
    *,
    reference_count: int = 0,
) -> VideoProductSpec:
    """Resolve one bounded product mode without inventing unavailable inputs."""

    if not isinstance(objective, str) or not objective.strip():
        raise VideoProductIntentError("video objective must not be blank")
    if objective != objective.strip():
        raise VideoProductIntentError("video objective must be normalized")
    if len(objective) > 20_000:
        raise VideoProductIntentError("video objective exceeds the input limit")
    if reference_count < 0 or reference_count > 20:
        raise VideoProductIntentError("video reference count is outside supported bounds")

    normalized = " ".join(objective.casefold().split())
    localization = _matches_any(normalized, _LOCALIZATION_PATTERNS)
    revision = _matches_any(normalized, _REVISION_PATTERNS)
    series = _matches_any(normalized, _SERIES_PATTERNS)

    if localization:
        mode = VideoProductMode.LOCALIZATION
    elif revision:
        mode = VideoProductMode.REVISION
    elif series:
        mode = VideoProductMode.SERIES_CONTINUATION
    elif reference_count:
        mode = VideoProductMode.REFERENCE_TO_VIDEO
    else:
        mode = VideoProductMode.CREATE

    return VideoProductSpec(
        schema="ilaios.video-product-spec.v1",
        mode=mode,
        objective=objective,
        aspect_ratio=_aspect_ratio(normalized),
        reference_count=reference_count,
        source_video_required=mode in {VideoProductMode.REVISION, VideoProductMode.LOCALIZATION},
        series_state_required=mode is VideoProductMode.SERIES_CONTINUATION,
    )


def admit_current_desktop_video_product(
    objective: str,
    *,
    reference_count: int = 0,
    source_video_present: bool = False,
    series_state_present: bool = False,
) -> VideoProductSpec:
    """Admit only work the current finished-product runtime can deliver exactly."""

    spec = derive_video_product_spec(objective, reference_count=reference_count)
    if source_video_present and not spec.source_video_required:
        raise VideoProductIntentError(
            "an authenticated source video is bound but the objective is not an explicit "
            "revision/localization request; refusing to silently ignore source media"
        )
    if spec.source_video_required and not source_video_present:
        raise VideoProductIntentError(
            f"video mode '{spec.mode.value}' requires an authenticated source video; "
            "image references cannot substitute for source media"
        )
    if spec.source_video_required:
        raise VideoProductIntentError(
            f"video mode '{spec.mode.value}' has authenticated source media but its "
            "bounded edit/localization execution path is not materialized yet"
        )
    if spec.series_state_required and not series_state_present:
        raise VideoProductIntentError(
            "series-continuation intent requires an authenticated canonical SeriesState "
            "binding; standalone text must not invent cross-episode continuity"
        )
    if spec.series_state_required:
        raise VideoProductIntentError(
            "authenticated SeriesState is present but series-continuation execution is "
            "not materialized by the current Desktop finished-product runtime"
        )
    if spec.aspect_ratio != "16:9":
        raise VideoProductIntentError(
            f"requested aspect ratio '{spec.aspect_ratio}' is not materialized by the "
            "current Desktop finished-product runtime; refusing a mismatched video"
        )
    return spec


def _matches_any(value: str, patterns: tuple[str, ...]) -> bool:
    return any(re.search(pattern, value, flags=re.IGNORECASE) is not None for pattern in patterns)


def _ratio(value: str, numerator: int, denominator: int) -> bool:
    return (
        re.search(
            rf"(?<!\d){numerator}\s*:\s*{denominator}(?!\d)",
            value,
        )
        is not None
    )


def _aspect_ratio(normalized: str) -> str:
    vertical = bool(
        _ratio(normalized, 9, 16)
        or re.search(r"\b(?:vertical|portrait)\s+(?:video|format|aspect(?:\s+ratio)?)\b", normalized)
        or re.search(r"\b(?:for|on)\s+tiktok\b", normalized)
        or re.search(r"\binstagram\s+reels?\b", normalized)
        or re.search(r"\b(?:for|on)\s+reels?\b", normalized)
        or re.search(r"\byoutube\s+shorts?\b", normalized)
    )
    square = bool(
        _ratio(normalized, 1, 1)
        or re.search(r"\bsquare\s+(?:video|format|aspect(?:\s+ratio)?)\b", normalized)
        or re.search(r"\bkare\s+(?:video|format)\b", normalized)
    )
    widescreen = _ratio(normalized, 16, 9)
    requested = [
        ratio
        for ratio, present in (("9:16", vertical), ("1:1", square), ("16:9", widescreen))
        if present
    ]
    if len(requested) > 1:
        raise VideoProductIntentError(
            "video objective requests conflicting aspect ratios; choose exactly one output shape"
        )
    return requested[0] if requested else "16:9"


__all__ = [
    "VideoProductIntentError",
    "VideoProductMode",
    "VideoProductSpec",
    "admit_current_desktop_video_product",
    "derive_video_product_spec",
]
