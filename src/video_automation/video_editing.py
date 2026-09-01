"""ILAIOS-native execution of governed ``video.edit.*`` skill operations.

The executor resolves inputs only through canonical M13 Asset Store methods and
delegates media mutation to the existing M18 FFmpeg engine. It is not a second
runtime, asset registry, policy authority, or orchestrator.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Protocol

from .ffmpeg_media_engine import FfmpegMediaEngine, MediaCommandResult
from .video_skills import EditKind, EditOperation, VideoSkillError


class RegisteredAssetResolver(Protocol):
    """Narrow read boundary implemented by canonical M13 Asset Store."""

    def require_registered_path(self, asset_id: str) -> Path: ...


class VideoEditEngine(Protocol):
    def trim(
        self,
        *,
        input_path: str | Path,
        output_path: str | Path,
        start_seconds: float,
        duration_seconds: float,
    ) -> MediaCommandResult: ...

    def concatenate(
        self,
        *,
        input_paths: tuple[str | Path, ...],
        output_path: str | Path,
    ) -> MediaCommandResult: ...

    def overlay(
        self,
        *,
        input_path: str | Path,
        overlay_path: str | Path,
        output_path: str | Path,
        x: int = 0,
        y: int = 0,
    ) -> MediaCommandResult: ...

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

    def mix_audio(
        self,
        *,
        input_paths: tuple[str | Path, ...],
        output_path: str | Path,
    ) -> MediaCommandResult: ...

    def crop(
        self,
        *,
        input_path: str | Path,
        output_path: str | Path,
        width: int,
        height: int,
        x: int = 0,
        y: int = 0,
    ) -> MediaCommandResult: ...


@dataclass(frozen=True, slots=True)
class EditExecutionResult:
    operation_id: str
    output_asset_id: str
    output_path: str
    sha256_hex: str
    byte_length: int
    command: tuple[str, ...]


class VideoEditExecutor:
    """Execute one validated operation under M13/M18 boundaries."""

    def __init__(
        self,
        resolver: RegisteredAssetResolver,
        output_root: Path,
        *,
        engine: VideoEditEngine | None = None,
    ) -> None:
        self._resolver = resolver
        self._output_root = output_root.resolve()
        self._engine = engine or FfmpegMediaEngine()

    def execute(self, operation: EditOperation) -> EditExecutionResult:
        inputs = tuple(
            self._resolver.require_registered_path(asset_id).resolve()
            for asset_id in operation.input_asset_ids
        )
        output = self._output_path(operation.output_asset_id)
        if output.is_symlink():
            raise VideoSkillError("edit output symbolic links are prohibited")
        if output.exists():
            raise VideoSkillError("edit output already exists")
        result = self._dispatch(operation, inputs, output)
        if not output.is_file() or output.is_symlink():
            raise VideoSkillError("edit engine did not produce a regular output file")
        body = output.read_bytes()
        if not body:
            raise VideoSkillError("edit output must not be empty")
        return EditExecutionResult(
            operation.operation_id,
            operation.output_asset_id,
            str(output),
            sha256(body).hexdigest(),
            len(body),
            result.argv,
        )

    def _output_path(self, asset_id: str) -> Path:
        if any(
            character
            not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_."
            for character in asset_id
        ):
            raise VideoSkillError("output_asset_id contains unsafe path characters")
        output = (self._output_root / f"{asset_id}.mp4").resolve()
        if self._output_root not in output.parents:
            raise VideoSkillError("edit output escapes the configured sandbox")
        output.parent.mkdir(parents=True, exist_ok=True)
        return output

    def _dispatch(
        self, operation: EditOperation, inputs: tuple[Path, ...], output: Path
    ) -> MediaCommandResult:
        parameters = operation.parameters
        if operation.kind is EditKind.TRIM:
            _input_count(inputs, 1)
            _only(parameters, {"start_seconds", "duration_seconds"})
            return self._engine.trim(
                input_path=inputs[0],
                output_path=output,
                start_seconds=_float(parameters, "start_seconds", minimum=0),
                duration_seconds=_float(
                    parameters, "duration_seconds", minimum=0, exclusive=True
                ),
            )
        if operation.kind is EditKind.CONCATENATE:
            if len(inputs) < 2:
                raise VideoSkillError("concatenate requires at least two inputs")
            _only(parameters, set())
            return self._engine.concatenate(input_paths=inputs, output_path=output)
        if operation.kind is EditKind.OVERLAY:
            _input_count(inputs, 2)
            _only(parameters, {"x", "y"})
            return self._engine.overlay(
                input_path=inputs[0],
                overlay_path=inputs[1],
                output_path=output,
                x=_integer(parameters, "x", default=0),
                y=_integer(parameters, "y", default=0),
            )
        if operation.kind is EditKind.SCALE:
            _input_count(inputs, 1)
            _only(parameters, {"width", "height", "fps", "video_codec", "audio_codec"})
            return self._engine.normalize_video(
                input_path=inputs[0],
                output_path=output,
                width=_integer(parameters, "width", minimum=1),
                height=_integer(parameters, "height", minimum=1),
                fps=_integer(parameters, "fps", minimum=1),
                video_codec=_string(parameters, "video_codec"),
                audio_codec=_string(parameters, "audio_codec"),
            )
        if operation.kind is EditKind.CROP:
            _input_count(inputs, 1)
            _only(parameters, {"width", "height", "x", "y"})
            return self._engine.crop(
                input_path=inputs[0],
                output_path=output,
                width=_integer(parameters, "width", minimum=1),
                height=_integer(parameters, "height", minimum=1),
                x=_integer(parameters, "x", default=0),
                y=_integer(parameters, "y", default=0),
            )
        if operation.kind is EditKind.AUDIO_MIX:
            if len(inputs) < 2:
                raise VideoSkillError("audio mix requires at least two inputs")
            _only(parameters, set())
            return self._engine.mix_audio(input_paths=inputs, output_path=output)
        raise VideoSkillError(f"unsupported edit kind: {operation.kind.value}")


def _only(parameters: Mapping[str, object], allowed: set[str]) -> None:
    unknown = set(parameters) - allowed
    if unknown:
        raise VideoSkillError(f"unsupported edit parameters: {sorted(unknown)}")


def _input_count(inputs: tuple[Path, ...], expected: int) -> None:
    if len(inputs) != expected:
        raise VideoSkillError(f"edit operation requires exactly {expected} inputs")


def _float(
    parameters: Mapping[str, object],
    key: str,
    *,
    minimum: float,
    exclusive: bool = False,
) -> float:
    value = parameters.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise VideoSkillError(f"{key} must be numeric")
    result = float(value)
    if result < minimum or (exclusive and result == minimum):
        raise VideoSkillError(f"{key} is outside the allowed range")
    return result


def _integer(
    parameters: Mapping[str, object],
    key: str,
    *,
    default: int | None = None,
    minimum: int | None = None,
) -> int:
    value = parameters.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int):
        raise VideoSkillError(f"{key} must be an integer")
    if minimum is not None and value < minimum:
        raise VideoSkillError(f"{key} is outside the allowed range")
    return value


def _string(parameters: Mapping[str, object], key: str) -> str:
    value = parameters.get(key)
    if not isinstance(value, str) or not value or value != value.strip():
        raise VideoSkillError(f"{key} must be a non-blank trimmed string")
    return value
