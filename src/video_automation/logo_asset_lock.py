"""Deterministic original-asset logo lock for reference-conditioned video.

This module is a bounded repair primitive, not a second video engine. It uses the
canonical M18 FFmpeg engine to composite the exact admitted logo bytes over an
already generated video when native-provider logo fidelity fails independent QA.

The compositor deliberately does not resize, crop, recolor, redraw, or otherwise
mutate the logo asset. If the original logo cannot fit the final frame at its
native pixel dimensions, the repair fails closed instead of degrading integrity.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
from pathlib import Path
from typing import Protocol

from .ffmpeg_media_engine import (
    FfmpegMediaEngine,
    FfmpegMediaEngineError,
    MediaCommandResult,
)


class LogoAssetLockError(RuntimeError):
    """Raised when deterministic logo preservation cannot be established."""


class LogoOverlayEngine(Protocol):
    def overlay(
        self,
        *,
        input_path: str | Path,
        overlay_path: str | Path,
        output_path: str | Path,
        x: int = 0,
        y: int = 0,
    ) -> MediaCommandResult: ...


class LogoPlacement(str, Enum):
    TOP_LEFT = "top-left"
    TOP_RIGHT = "top-right"
    BOTTOM_LEFT = "bottom-left"
    BOTTOM_RIGHT = "bottom-right"
    CENTER = "center"


@dataclass(frozen=True, slots=True)
class LogoAssetLockInput:
    content: bytes
    mime_type: str
    sha256_hex: str
    width: int
    height: int
    instruction: str | None = None

    def __post_init__(self) -> None:
        if not self.content:
            raise LogoAssetLockError("logo asset must not be empty")
        if self.mime_type not in {"image/png", "image/jpeg", "image/webp"}:
            raise LogoAssetLockError("logo asset MIME type is unsupported")
        if sha256(self.content).hexdigest() != self.sha256_hex:
            raise LogoAssetLockError("logo asset digest does not match admitted bytes")
        if self.width <= 0 or self.height <= 0:
            raise LogoAssetLockError("logo asset dimensions must be positive")
        if self.instruction is not None and len(self.instruction) > 500:
            raise LogoAssetLockError("logo asset instruction exceeds 500 characters")


@dataclass(frozen=True, slots=True)
class LogoAssetLockResult:
    output_path: str
    source_logo_sha256: str
    placement: LogoPlacement
    x: int
    y: int
    margin: int
    logo_width: int
    logo_height: int


class LogoAssetLockCompositor:
    """Composite one exact logo asset at deterministic coordinates."""

    def __init__(self, *, engine: LogoOverlayEngine | None = None) -> None:
        self._engine = engine or FfmpegMediaEngine(timeout_seconds=900)

    def apply(
        self,
        *,
        video_path: Path,
        output_path: Path,
        logo: LogoAssetLockInput,
        frame_width: int,
        frame_height: int,
    ) -> LogoAssetLockResult:
        if not video_path.is_file():
            raise LogoAssetLockError("asset-lock source video does not exist")
        if frame_width <= 0 or frame_height <= 0:
            raise LogoAssetLockError("asset-lock frame dimensions must be positive")
        if output_path.exists():
            raise LogoAssetLockError("asset-lock output already exists")

        margin = max(16, round(min(frame_width, frame_height) * 0.025))
        if logo.width > frame_width - (2 * margin) or logo.height > frame_height - (2 * margin):
            raise LogoAssetLockError(
                "logo asset is too large for exact no-rescale compositing"
            )

        placement = resolve_logo_placement(logo.instruction)
        x, y = _coordinates(
            placement,
            frame_width=frame_width,
            frame_height=frame_height,
            logo_width=logo.width,
            logo_height=logo.height,
            margin=margin,
        )
        logo_path = output_path.parent / f"asset-lock-logo-{logo.sha256_hex}{_extension(logo.mime_type)}"
        if logo_path.exists() and logo_path.read_bytes() != logo.content:
            raise LogoAssetLockError("asset-lock temporary logo digest collision")
        logo_path.parent.mkdir(parents=True, exist_ok=True)
        logo_path.write_bytes(logo.content)
        try:
            try:
                self._engine.overlay(
                    input_path=video_path,
                    overlay_path=logo_path,
                    output_path=output_path,
                    x=x,
                    y=y,
                )
            except FfmpegMediaEngineError as error:
                raise LogoAssetLockError("deterministic logo compositing failed") from error
        finally:
            logo_path.unlink(missing_ok=True)

        if not output_path.is_file() or output_path.stat().st_size <= 0:
            raise LogoAssetLockError("deterministic logo compositing produced no video")
        return LogoAssetLockResult(
            output_path=str(output_path),
            source_logo_sha256=logo.sha256_hex,
            placement=placement,
            x=x,
            y=y,
            margin=margin,
            logo_width=logo.width,
            logo_height=logo.height,
        )


def resolve_logo_placement(instruction: str | None) -> LogoPlacement:
    """Resolve a small deterministic EN/TR placement vocabulary.

    A missing placement uses bottom-right as the product-safe default. Multiple
    conflicting placement cues fail closed rather than guessing.
    """

    if instruction is None or not instruction.strip():
        return LogoPlacement.BOTTOM_RIGHT
    normalized = " ".join(instruction.casefold().replace("_", "-").split())
    aliases: dict[LogoPlacement, tuple[str, ...]] = {
        LogoPlacement.TOP_LEFT: (
            "asset-lock:top-left",
            "top-left",
            "top left",
            "upper left",
            "sol üst",
            "sol ust",
        ),
        LogoPlacement.TOP_RIGHT: (
            "asset-lock:top-right",
            "top-right",
            "top right",
            "upper right",
            "sağ üst",
            "sag ust",
        ),
        LogoPlacement.BOTTOM_LEFT: (
            "asset-lock:bottom-left",
            "bottom-left",
            "bottom left",
            "lower left",
            "sol alt",
        ),
        LogoPlacement.BOTTOM_RIGHT: (
            "asset-lock:bottom-right",
            "bottom-right",
            "bottom right",
            "lower right",
            "sağ alt",
            "sag alt",
        ),
        LogoPlacement.CENTER: (
            "asset-lock:center",
            "center",
            "centre",
            "merkez",
            "ortala",
        ),
    }
    matches = {
        placement
        for placement, values in aliases.items()
        if any(value in normalized for value in values)
    }
    if len(matches) > 1:
        raise LogoAssetLockError("logo placement instruction is ambiguous")
    if not matches:
        return LogoPlacement.BOTTOM_RIGHT
    return next(iter(matches))


def _coordinates(
    placement: LogoPlacement,
    *,
    frame_width: int,
    frame_height: int,
    logo_width: int,
    logo_height: int,
    margin: int,
) -> tuple[int, int]:
    if placement is LogoPlacement.TOP_LEFT:
        return margin, margin
    if placement is LogoPlacement.TOP_RIGHT:
        return frame_width - logo_width - margin, margin
    if placement is LogoPlacement.BOTTOM_LEFT:
        return margin, frame_height - logo_height - margin
    if placement is LogoPlacement.BOTTOM_RIGHT:
        return frame_width - logo_width - margin, frame_height - logo_height - margin
    return (frame_width - logo_width) // 2, (frame_height - logo_height) // 2


def _extension(mime_type: str) -> str:
    return {
        "image/png": ".png",
        "image/jpeg": ".jpg",
        "image/webp": ".webp",
    }[mime_type]
