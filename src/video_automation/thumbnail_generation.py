"""Deterministic artifact-bound thumbnail generation for Video Factory.

The coordinator verifies the exact source artifact before rendering, delegates
FFmpeg process execution through the existing M18 command-runner boundary, and
re-verifies the emitted thumbnail before producing immutable evidence.  It does
not perform perceptual thumbnail QA or publish media.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Protocol

from .ffmpeg_media_engine import CommandRunner, SubprocessCommandRunner
from .video_skills import ThumbnailRequest


class ThumbnailGenerationError(ValueError):
    """Raised when a thumbnail cannot be generated or evidenced safely."""


@dataclass(frozen=True, slots=True)
class ThumbnailArtifact:
    """Immutable evidence for one generated thumbnail artifact."""

    thumbnail_id: str
    request_id: str
    source_artifact_sha256: str
    output_path: str
    sha256_hex: str
    byte_length: int
    width: int
    height: int
    timestamp_ms: int
    renderer_id: str
    safe_text_rendered: bool
    provenance_reference: str

    def __post_init__(self) -> None:
        for name in (
            "thumbnail_id",
            "request_id",
            "output_path",
            "renderer_id",
            "provenance_reference",
        ):
            _require_text(name, getattr(self, name))
        _require_sha256(self.source_artifact_sha256)
        _require_sha256(self.sha256_hex)
        if self.byte_length <= 0:
            raise ThumbnailGenerationError("thumbnail byte_length must be positive")
        if self.width <= 0 or self.height <= 0:
            raise ThumbnailGenerationError("thumbnail dimensions must be positive")
        if self.timestamp_ms < 0:
            raise ThumbnailGenerationError("thumbnail timestamp must not be negative")


class ThumbnailRenderer(Protocol):
    """Bounded renderer contract used by the thumbnail coordinator."""

    @property
    def renderer_id(self) -> str:
        """Return a stable implementation identifier."""

    @property
    def renders_text(self) -> bool:
        """Return whether safe_text is materially rendered into the output."""

    def render(
        self,
        *,
        source_path: Path,
        output_path: Path,
        timestamp_ms: int,
        width: int,
        height: int,
        safe_text: str,
    ) -> None:
        """Render exactly one thumbnail file."""


class FfmpegThumbnailRenderer:
    """FFmpeg frame renderer using the existing M18 command-runner boundary."""

    def __init__(
        self,
        *,
        ffmpeg_executable: str = "ffmpeg",
        runner: CommandRunner | None = None,
        timeout_seconds: float = 60.0,
        font_path: str | Path | None = None,
    ) -> None:
        _require_text("ffmpeg_executable", ffmpeg_executable)
        if timeout_seconds <= 0:
            raise ThumbnailGenerationError("timeout_seconds must be positive")
        self._ffmpeg = ffmpeg_executable
        self._runner = runner or SubprocessCommandRunner()
        self._timeout_seconds = timeout_seconds
        self._font_path = _validated_font_path(font_path)

    @property
    def renderer_id(self) -> str:
        text_mode = "textfile-drawtext" if self._font_path is not None else "frame-only"
        return f"ffmpeg-thumbnail-v1:{text_mode}"

    @property
    def renders_text(self) -> bool:
        return self._font_path is not None

    def render(
        self,
        *,
        source_path: Path,
        output_path: Path,
        timestamp_ms: int,
        width: int,
        height: int,
        safe_text: str,
    ) -> None:
        if timestamp_ms < 0:
            raise ThumbnailGenerationError("timestamp_ms must not be negative")
        if width <= 0 or height <= 0:
            raise ThumbnailGenerationError("thumbnail dimensions must be positive")
        if not source_path.is_file():
            raise ThumbnailGenerationError("thumbnail source must be a regular file")
        if output_path.exists() and output_path.is_dir():
            raise ThumbnailGenerationError("thumbnail output must reference a file")
        if safe_text and self._font_path is None:
            raise ThumbnailGenerationError(
                "safe_text requires an explicitly configured thumbnail font"
            )
        if "\x00" in safe_text:
            raise ThumbnailGenerationError("safe_text must not contain NUL bytes")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        text_file: Path | None = None
        filter_graph = (
            f"scale={width}:{height}:force_original_aspect_ratio=increase,"
            f"crop={width}:{height}"
        )
        try:
            if safe_text:
                text_file = output_path.with_suffix(output_path.suffix + ".text.txt")
                text_file.write_text(safe_text, encoding="utf-8", newline="\n")
                assert self._font_path is not None
                filter_graph += (
                    ",drawtext="
                    f"fontfile='{_escape_filter_path(self._font_path)}':"
                    f"textfile='{_escape_filter_path(text_file)}':"
                    "fontcolor=white:fontsize=h/14:"
                    "x=(w-text_w)/2:y=h-(text_h*2):"
                    "box=1:boxcolor=black@0.55:boxborderw=18"
                )

            command = (
                self._ffmpeg,
                "-y",
                "-v",
                "error",
                "-ss",
                _number(timestamp_ms / 1000.0),
                "-i",
                str(source_path),
                "-frames:v",
                "1",
                "-vf",
                filter_graph,
                "-q:v",
                "2",
                str(output_path),
            )
            self._runner.run(command, timeout_seconds=self._timeout_seconds)
        finally:
            if text_file is not None and text_file.exists():
                text_file.unlink()


class ThumbnailGenerationCoordinator:
    """Verify source identity, render once, and emit content-addressed evidence."""

    def __init__(self, renderer: ThumbnailRenderer) -> None:
        self._renderer = renderer

    def generate(
        self,
        request: ThumbnailRequest,
        *,
        source_path: str | Path,
        source_byte_length: int,
        output_directory: str | Path,
        provenance_reference: str,
    ) -> ThumbnailArtifact:
        _require_text("provenance_reference", provenance_reference)
        if source_byte_length <= 0:
            raise ThumbnailGenerationError("source_byte_length must be positive")
        source = Path(source_path)
        if source.is_symlink():
            raise ThumbnailGenerationError("symbolic-link thumbnail sources are prohibited")
        if not source.exists() or not source.is_file():
            raise ThumbnailGenerationError("thumbnail source must be an existing regular file")
        body = source.read_bytes()
        if not body:
            raise ThumbnailGenerationError("thumbnail source must not be empty")
        if len(body) != source_byte_length:
            raise ThumbnailGenerationError("thumbnail source byte length mismatch")
        observed_sha = sha256(body).hexdigest()
        if observed_sha != request.artifact_sha256:
            raise ThumbnailGenerationError("thumbnail source SHA-256 mismatch")
        if request.safe_text and not self._renderer.renders_text:
            raise ThumbnailGenerationError(
                "thumbnail renderer cannot materialize requested safe_text"
            )

        output_root = Path(output_directory)
        if output_root.exists() and not output_root.is_dir():
            raise ThumbnailGenerationError("output_directory must reference a directory")
        output_root.mkdir(parents=True, exist_ok=True)
        material = "|".join(
            (
                request.request_id,
                request.artifact_sha256,
                str(request.timestamp_ms),
                str(request.width),
                str(request.height),
                request.safe_text,
                self._renderer.renderer_id,
                provenance_reference,
            )
        )
        request_digest = sha256(material.encode("utf-8")).hexdigest()
        output = output_root / f"thumbnail-{request_digest[:20]}.jpg"
        if output.resolve() == source.resolve():
            raise ThumbnailGenerationError("thumbnail output cannot overwrite its source")

        self._renderer.render(
            source_path=source,
            output_path=output,
            timestamp_ms=request.timestamp_ms,
            width=request.width,
            height=request.height,
            safe_text=request.safe_text,
        )
        if output.is_symlink():
            raise ThumbnailGenerationError("symbolic-link thumbnail outputs are prohibited")
        if not output.exists() or not output.is_file():
            raise ThumbnailGenerationError("thumbnail renderer did not emit a regular file")
        output_body = output.read_bytes()
        if not output_body:
            raise ThumbnailGenerationError("thumbnail renderer emitted an empty file")
        output_sha = sha256(output_body).hexdigest()
        thumbnail_id = (
            "thumbnail-"
            + sha256(
                f"{request.request_id}|{observed_sha}|{output_sha}".encode("utf-8")
            ).hexdigest()[:24]
        )
        return ThumbnailArtifact(
            thumbnail_id=thumbnail_id,
            request_id=request.request_id,
            source_artifact_sha256=observed_sha,
            output_path=str(output.resolve()),
            sha256_hex=output_sha,
            byte_length=len(output_body),
            width=request.width,
            height=request.height,
            timestamp_ms=request.timestamp_ms,
            renderer_id=self._renderer.renderer_id,
            safe_text_rendered=bool(request.safe_text),
            provenance_reference=provenance_reference,
        )


def _validated_font_path(value: str | Path | None) -> Path | None:
    if value is None:
        return None
    path = Path(value)
    if path.is_symlink():
        raise ThumbnailGenerationError("symbolic-link thumbnail fonts are prohibited")
    if not path.exists() or not path.is_file():
        raise ThumbnailGenerationError("thumbnail font must be an existing regular file")
    return path.resolve()


def _escape_filter_path(path: Path) -> str:
    return (
        str(path.resolve())
        .replace("\\", "/")
        .replace(":", "\\:")
        .replace("'", "\\'")
    )


def _number(value: float) -> str:
    return format(value, ".9g")


def _require_sha256(value: str) -> None:
    if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        raise ThumbnailGenerationError("SHA-256 values must be lowercase hexadecimal")


def _require_text(name: str, value: str) -> None:
    if not value or value != value.strip():
        raise ThumbnailGenerationError(f"{name} must be non-blank and trimmed")
