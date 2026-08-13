"""Canonical M18 general FFmpeg media engine.

This module provides deterministic low-level FFmpeg/FFprobe command execution
for ILAIOS Video Automation.

Supported responsibilities:

- probe / technical inspection
- trim
- concatenate
- transcode / codec conversion
- scale / crop
- frame-rate normalization
- audio normalization
- audio mixing
- muxing

Timeline planning, Remotion composition, publishing, provider selection, and
business orchestration do not belong in M18.
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


class FfmpegMediaEngineError(RuntimeError):
    """Raised when an M18 media operation cannot complete safely."""


@dataclass(frozen=True, slots=True)
class MediaCommandResult:
    """Immutable result from one low-level media command."""

    argv: tuple[str, ...]
    return_code: int
    stdout: str
    stderr: str

    def __post_init__(self) -> None:
        if not self.argv:
            raise FfmpegMediaEngineError("argv must not be empty")

        if self.return_code != 0:
            raise FfmpegMediaEngineError(
                "successful MediaCommandResult requires return_code 0"
            )


@dataclass(frozen=True, slots=True)
class MediaProbe:
    """Normalized FFprobe evidence."""

    path: str
    format_name: str
    duration_seconds: float
    streams: tuple[Mapping[str, object], ...]

    def __post_init__(self) -> None:
        _require_non_blank("path", self.path)
        _require_non_blank("format_name", self.format_name)

        if self.duration_seconds < 0:
            raise FfmpegMediaEngineError("duration_seconds must be >= 0")


class CommandRunner(Protocol):
    """Injectable subprocess boundary for deterministic testing."""

    def run(
        self,
        argv: tuple[str, ...],
        *,
        timeout_seconds: float,
    ) -> MediaCommandResult: ...


class SubprocessCommandRunner:
    """Production subprocess implementation."""

    def run(
        self,
        argv: tuple[str, ...],
        *,
        timeout_seconds: float,
    ) -> MediaCommandResult:
        if timeout_seconds <= 0:
            raise FfmpegMediaEngineError("timeout_seconds must be greater than zero")

        try:
            completed = subprocess.run(
                argv,
                check=False,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
            )
        except FileNotFoundError as exc:
            raise FfmpegMediaEngineError(
                f"media executable was not found: {argv[0]}"
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise FfmpegMediaEngineError(f"media command timed out: {argv[0]}") from exc

        if completed.returncode != 0:
            raise FfmpegMediaEngineError(
                completed.stderr.strip()
                or f"media command failed with code {completed.returncode}"
            )

        return MediaCommandResult(
            argv=argv,
            return_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )


class FfmpegMediaEngine:
    """General deterministic FFmpeg/FFprobe integration."""

    def __init__(
        self,
        *,
        ffmpeg_executable: str = "ffmpeg",
        ffprobe_executable: str = "ffprobe",
        runner: CommandRunner | None = None,
        timeout_seconds: float = 600.0,
    ) -> None:
        _require_non_blank(
            "ffmpeg_executable",
            ffmpeg_executable,
        )
        _require_non_blank(
            "ffprobe_executable",
            ffprobe_executable,
        )

        if timeout_seconds <= 0:
            raise FfmpegMediaEngineError("timeout_seconds must be greater than zero")

        self._ffmpeg = ffmpeg_executable
        self._ffprobe = ffprobe_executable
        self._runner = runner or SubprocessCommandRunner()
        self._timeout_seconds = timeout_seconds

    def probe(self, path: str | Path) -> MediaProbe:
        """Probe media using deterministic JSON FFprobe output."""

        source = _require_existing_file(path)

        argv = (
            self._ffprobe,
            "-v",
            "error",
            "-show_format",
            "-show_streams",
            "-of",
            "json",
            str(source),
        )

        result = self._execute(argv)

        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise FfmpegMediaEngineError("ffprobe did not return valid JSON") from exc

        if not isinstance(payload, dict):
            raise FfmpegMediaEngineError("ffprobe JSON root must be an object")

        format_payload = payload.get("format")
        streams_payload = payload.get("streams")

        if not isinstance(format_payload, dict):
            raise FfmpegMediaEngineError("ffprobe JSON requires format object")

        if not isinstance(streams_payload, list):
            raise FfmpegMediaEngineError("ffprobe JSON requires streams array")

        format_name = format_payload.get("format_name")
        duration = format_payload.get("duration")

        if not isinstance(format_name, str):
            raise FfmpegMediaEngineError("ffprobe format_name must be a string")

        if not isinstance(duration, str):
            raise FfmpegMediaEngineError("ffprobe duration must be a string")

        normalized_streams: list[Mapping[str, object]] = []

        for stream in streams_payload:
            if not isinstance(stream, dict):
                raise FfmpegMediaEngineError("ffprobe stream must be an object")

            normalized_streams.append(dict(stream))

        try:
            duration_seconds = float(duration)
        except ValueError as exc:
            raise FfmpegMediaEngineError("ffprobe duration is invalid") from exc

        return MediaProbe(
            path=str(source.resolve()),
            format_name=format_name,
            duration_seconds=duration_seconds,
            streams=tuple(normalized_streams),
        )

    def trim(
        self,
        *,
        input_path: str | Path,
        output_path: str | Path,
        start_seconds: float,
        duration_seconds: float,
    ) -> MediaCommandResult:
        if start_seconds < 0:
            raise FfmpegMediaEngineError("start_seconds must be >= 0")

        if duration_seconds <= 0:
            raise FfmpegMediaEngineError("duration_seconds must be greater than zero")

        source = _require_existing_file(input_path)
        output = _prepare_output(output_path)

        argv = (
            self._ffmpeg,
            "-y",
            "-v",
            "error",
            "-ss",
            _number(start_seconds),
            "-i",
            str(source),
            "-t",
            _number(duration_seconds),
            "-c",
            "copy",
            str(output),
        )

        return self._execute(argv)

    def concatenate(
        self,
        *,
        input_paths: tuple[str | Path, ...],
        output_path: str | Path,
    ) -> MediaCommandResult:
        if not input_paths:
            raise FfmpegMediaEngineError("input_paths must not be empty")

        sources = tuple(_require_existing_file(path) for path in input_paths)
        output = _prepare_output(output_path)

        manifest = output.with_suffix(output.suffix + ".m18-concat.txt")

        try:
            manifest.write_text(
                "".join(
                    f"file '{_escape_concat_path(source)}'\n" for source in sources
                ),
                encoding="utf-8",
                newline="\n",
            )

            argv = (
                self._ffmpeg,
                "-y",
                "-v",
                "error",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(manifest),
                "-c",
                "copy",
                str(output),
            )

            return self._execute(argv)
        finally:
            if manifest.exists():
                manifest.unlink()

    def transcode(
        self,
        *,
        input_path: str | Path,
        output_path: str | Path,
        video_codec: str,
        audio_codec: str,
    ) -> MediaCommandResult:
        _require_non_blank("video_codec", video_codec)
        _require_non_blank("audio_codec", audio_codec)

        source = _require_existing_file(input_path)
        output = _prepare_output(output_path)

        argv = (
            self._ffmpeg,
            "-y",
            "-v",
            "error",
            "-i",
            str(source),
            "-c:v",
            video_codec,
            "-c:a",
            audio_codec,
            str(output),
        )

        return self._execute(argv)

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
    ) -> MediaCommandResult:
        if width <= 0 or height <= 0:
            raise FfmpegMediaEngineError("width and height must be greater than zero")

        if fps <= 0:
            raise FfmpegMediaEngineError("fps must be greater than zero")

        _require_non_blank("video_codec", video_codec)
        _require_non_blank("audio_codec", audio_codec)

        source = _require_existing_file(input_path)
        output = _prepare_output(output_path)

        filter_graph = (
            f"scale={width}:{height}:force_original_aspect_ratio=increase,"
            f"crop={width}:{height},fps={fps}"
        )

        argv = (
            self._ffmpeg,
            "-y",
            "-v",
            "error",
            "-i",
            str(source),
            "-vf",
            filter_graph,
            "-c:v",
            video_codec,
            "-c:a",
            audio_codec,
            str(output),
        )

        return self._execute(argv)

    def normalize_audio(
        self,
        *,
        input_path: str | Path,
        output_path: str | Path,
        target_lufs: float = -16.0,
    ) -> MediaCommandResult:
        source = _require_existing_file(input_path)
        output = _prepare_output(output_path)

        argv = (
            self._ffmpeg,
            "-y",
            "-v",
            "error",
            "-i",
            str(source),
            "-af",
            f"loudnorm=I={_number(target_lufs)}:TP=-1.5:LRA=11",
            str(output),
        )

        return self._execute(argv)

    def crop(
        self,
        *,
        input_path: str | Path,
        output_path: str | Path,
        width: int,
        height: int,
        x: int = 0,
        y: int = 0,
    ) -> MediaCommandResult:
        if width <= 0 or height <= 0:
            raise FfmpegMediaEngineError("crop width and height must be positive")
        source = _require_existing_file(input_path)
        output = _prepare_output(output_path)
        return self._execute(
            (
                self._ffmpeg,
                "-y",
                "-v",
                "error",
                "-i",
                str(source),
                "-vf",
                f"crop={width}:{height}:{x}:{y}",
                str(output),
            )
        )

    def mix_audio(
        self,
        *,
        input_paths: tuple[str | Path, ...],
        output_path: str | Path,
    ) -> MediaCommandResult:
        if len(input_paths) < 2:
            raise FfmpegMediaEngineError("audio mixing requires at least two inputs")

        sources = tuple(_require_existing_file(path) for path in input_paths)
        output = _prepare_output(output_path)

        input_args: list[str] = []

        for source in sources:
            input_args.extend(("-i", str(source)))

        filter_value = f"amix=inputs={len(sources)}:duration=longest:normalize=0"

        argv = (
            self._ffmpeg,
            "-y",
            "-v",
            "error",
            *input_args,
            "-filter_complex",
            filter_value,
            str(output),
        )

        return self._execute(tuple(argv))

    def overlay(
        self,
        *,
        input_path: str | Path,
        overlay_path: str | Path,
        output_path: str | Path,
        x: int = 0,
        y: int = 0,
    ) -> MediaCommandResult:
        """Overlay one registered visual asset without shell interpolation."""

        source = _require_existing_file(input_path)
        overlay = _require_existing_file(overlay_path)
        output = _prepare_output(output_path)
        filter_value = f"[0:v][1:v]overlay=x={x}:y={y}:format=auto"
        argv = (
            self._ffmpeg,
            "-y",
            "-v",
            "error",
            "-i",
            str(source),
            "-i",
            str(overlay),
            "-filter_complex",
            filter_value,
            "-map",
            "0:a?",
            "-c:a",
            "copy",
            str(output),
        )
        return self._execute(argv)

    def mux(
        self,
        *,
        video_path: str | Path,
        audio_path: str | Path,
        output_path: str | Path,
    ) -> MediaCommandResult:
        video = _require_existing_file(video_path)
        audio = _require_existing_file(audio_path)
        output = _prepare_output(output_path)

        argv = (
            self._ffmpeg,
            "-y",
            "-v",
            "error",
            "-i",
            str(video),
            "-i",
            str(audio),
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-shortest",
            str(output),
        )

        return self._execute(argv)

    def _execute(
        self,
        argv: tuple[str, ...],
    ) -> MediaCommandResult:
        return self._runner.run(
            argv,
            timeout_seconds=self._timeout_seconds,
        )


def _require_existing_file(
    path: str | Path,
) -> Path:
    value = Path(path)

    if not value.exists():
        raise FfmpegMediaEngineError(f"input media does not exist: {value}")

    if not value.is_file():
        raise FfmpegMediaEngineError(f"input media is not a file: {value}")

    return value


def _prepare_output(
    path: str | Path,
) -> Path:
    value = Path(path)

    if value.exists() and value.is_dir():
        raise FfmpegMediaEngineError(f"output_path must reference a file: {value}")

    value.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    return value


def _escape_concat_path(path: Path) -> str:
    return str(path.resolve()).replace("\\", "/").replace("'", "'\\''")


def _number(value: float) -> str:
    return format(value, ".9g")


def _require_non_blank(
    name: str,
    value: str,
) -> None:
    if not value or not value.strip():
        raise FfmpegMediaEngineError(f"{name} must not be blank")

    if value != value.strip():
        raise FfmpegMediaEngineError(f"{name} must not contain surrounding whitespace")
