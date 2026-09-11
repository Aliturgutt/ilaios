"""Deterministic zero-provider-cost final 1080p mastering for Video Factory.

This module is a bounded post-production step. It reuses the canonical M18
FFmpeg media engine, never calls an external provider, and never creates a
second publishing or policy authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Protocol

from .ffmpeg_media_engine import MediaCommandResult, MediaProbe


class FinalMasteringError(RuntimeError):
    """Raised when a final master cannot be produced or verified safely."""


@dataclass(frozen=True, slots=True)
class FinalMasteringReceipt:
    source_path: str
    output_path: str
    source_width: int
    source_height: int
    output_width: int
    output_height: int
    sha256_hex: str
    byte_length: int
    upgraded: bool
    provider_cost_usd: float = 0.0


class FinalMasteringMediaEngine(Protocol):
    def probe(self, path: str | Path) -> MediaProbe: ...

    def normalize_video(
        self,
        *,
        input_path: str | Path,
        output_path: str | Path,
        width: int,
        height: int,
        fps: int,
        video_codec: str,
        audio_codec: str,
    ) -> MediaCommandResult: ...


class Final1080pMasterer:
    """Create a canonical 1080p master when the accepted shape is below 1080p."""

    def __init__(self, engine: FinalMasteringMediaEngine) -> None:
        self._engine = engine

    def master(
        self,
        *,
        input_path: str | Path,
        output_path: str | Path,
        fps: int = 30,
        video_codec: str = "libx264",
        audio_codec: str = "aac",
    ) -> FinalMasteringReceipt:
        if fps <= 0:
            raise FinalMasteringError("fps must be greater than zero")
        source = Path(input_path)
        if not source.is_file():
            raise FinalMasteringError("input video does not exist")

        source_probe = self._engine.probe(source)
        source_width, source_height = _video_dimensions(source_probe)
        target_width, target_height = _target_dimensions(source_width, source_height)

        already_mastered = (
            source_width >= target_width and source_height >= target_height
        )
        if already_mastered:
            return _receipt(
                source_path=source,
                output_path=source,
                source_width=source_width,
                source_height=source_height,
                output_width=source_width,
                output_height=source_height,
                upgraded=False,
            )

        output = Path(output_path)
        if output.resolve() == source.resolve():
            raise FinalMasteringError("upscale output must not overwrite source artifact")

        self._engine.normalize_video(
            input_path=source,
            output_path=output,
            width=target_width,
            height=target_height,
            fps=fps,
            video_codec=video_codec,
            audio_codec=audio_codec,
        )
        if not output.is_file():
            raise FinalMasteringError("FFmpeg did not materialize final master")

        output_probe = self._engine.probe(output)
        output_width, output_height = _video_dimensions(output_probe)
        if (output_width, output_height) != (target_width, target_height):
            raise FinalMasteringError("final master resolution verification failed")

        return _receipt(
            source_path=source,
            output_path=output,
            source_width=source_width,
            source_height=source_height,
            output_width=output_width,
            output_height=output_height,
            upgraded=True,
        )


def _video_dimensions(probe: MediaProbe) -> tuple[int, int]:
    for stream in probe.streams:
        if stream.get("codec_type") != "video":
            continue
        width = stream.get("width")
        height = stream.get("height")
        if (
            isinstance(width, int)
            and isinstance(height, int)
            and width > 0
            and height > 0
        ):
            return width, height
    raise FinalMasteringError("video stream dimensions are missing")


def _target_dimensions(width: int, height: int) -> tuple[int, int]:
    # Final mastering intentionally accepts only the canonical social shapes.
    if width == height:
        return 1080, 1080
    if width * 9 == height * 16:
        return 1920, 1080
    if width * 16 == height * 9:
        return 1080, 1920
    raise FinalMasteringError("unsupported final-master aspect ratio")


def _receipt(
    *,
    source_path: Path,
    output_path: Path,
    source_width: int,
    source_height: int,
    output_width: int,
    output_height: int,
    upgraded: bool,
) -> FinalMasteringReceipt:
    payload = output_path.read_bytes()
    if not payload:
        raise FinalMasteringError("final master artifact is empty")
    return FinalMasteringReceipt(
        source_path=str(source_path.resolve()),
        output_path=str(output_path.resolve()),
        source_width=source_width,
        source_height=source_height,
        output_width=output_width,
        output_height=output_height,
        sha256_hex=sha256(payload).hexdigest(),
        byte_length=len(payload),
        upgraded=upgraded,
        provider_cost_usd=0.0,
    )
