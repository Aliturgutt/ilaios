"""Provider-independent episode assembly execution."""

from __future__ import annotations

import subprocess
from collections.abc import Mapping
from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path
from types import MappingProxyType
from typing import Protocol

from .episode_assembly_request_planning import EpisodeAssemblyRequest
from .media_technical_validation import (
    EpisodeMediaTechnicalValidationManifest,
    MediaTechnicalValidationStatus,
    ValidatedMediaAsset,
)


class EpisodeAssemblyExecutionError(ValueError):
    """Raised when episode assembly cannot be executed safely."""


@dataclass(frozen=True, slots=True)
class EpisodeAssemblyInputClip:
    sequence_number: int
    asset_id: str
    local_path: str
    sha256_hex: str
    byte_length: int

    def __post_init__(self) -> None:
        if self.sequence_number <= 0:
            raise EpisodeAssemblyExecutionError(
                "sequence_number must be greater than zero"
            )
        _require_non_blank("asset_id", self.asset_id)
        _require_non_blank("local_path", self.local_path)
        _validate_sha256(self.sha256_hex)
        if self.byte_length <= 0:
            raise EpisodeAssemblyExecutionError("byte_length must be greater than zero")


@dataclass(frozen=True, slots=True)
class EpisodeAssemblyExecutorRequest:
    request_id: str
    episode_id: str
    clips: tuple[EpisodeAssemblyInputClip, ...]
    output_path: str
    container_format: str
    video_codec: str
    audio_codec: str
    width: int
    height: int
    frame_rate: int
    metadata: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in (
            "request_id",
            "episode_id",
            "output_path",
            "container_format",
            "video_codec",
            "audio_codec",
        ):
            _require_non_blank(name, getattr(self, name))
        if not self.clips:
            raise EpisodeAssemblyExecutionError(
                "executor request must contain at least one clip"
            )
        if tuple(c.sequence_number for c in self.clips) != tuple(
            range(1, len(self.clips) + 1)
        ):
            raise EpisodeAssemblyExecutionError(
                "executor clip sequence_numbers must be contiguous and start at one"
            )
        if self.width <= 0 or self.height <= 0 or self.frame_rate <= 0:
            raise EpisodeAssemblyExecutionError(
                "output dimensions and frame_rate must be greater than zero"
            )
        object.__setattr__(self, "metadata", _freeze_metadata(self.metadata))


@dataclass(frozen=True, slots=True)
class EpisodeAssemblyExecutorResult:
    output_path: str
    metadata: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_non_blank("output_path", self.output_path)
        object.__setattr__(self, "metadata", _freeze_metadata(self.metadata))


class EpisodeAssemblyExecutor(Protocol):
    @property
    def executor_id(self) -> str: ...
    def execute(
        self, request: EpisodeAssemblyExecutorRequest
    ) -> EpisodeAssemblyExecutorResult: ...


class FfmpegEpisodeAssemblyExecutor:
    def __init__(
        self, executable: str = "ffmpeg", *, timeout_seconds: float = 600.0
    ) -> None:
        _require_non_blank("executable", executable)
        if timeout_seconds <= 0:
            raise EpisodeAssemblyExecutionError(
                "timeout_seconds must be greater than zero"
            )
        self._executable = executable
        self._timeout_seconds = timeout_seconds

    @property
    def executor_id(self) -> str:
        return "ffmpeg-concat-v1"

    def execute(
        self, request: EpisodeAssemblyExecutorRequest
    ) -> EpisodeAssemblyExecutorResult:
        output = Path(request.output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        manifest = output.with_suffix(output.suffix + ".concat.txt")
        manifest.write_text(
            "".join(
                f"file '{_escape_path(Path(c.local_path))}'\n" for c in request.clips
            ),
            encoding="utf-8",
            newline="\n",
        )
        command = (
            self._executable,
            "-y",
            "-v",
            "error",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(manifest),
            "-vf",
            f"scale={request.width}:{request.height},fps={request.frame_rate}",
            "-c:v",
            request.video_codec,
            "-c:a",
            request.audio_codec,
            "-f",
            request.container_format,
            str(output),
        )
        try:
            completed = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                timeout=self._timeout_seconds,
            )
        except FileNotFoundError as exc:
            raise EpisodeAssemblyExecutionError(
                "ffmpeg executable was not found"
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise EpisodeAssemblyExecutionError("ffmpeg timed out") from exc
        finally:
            if manifest.exists():
                manifest.unlink()
        if completed.returncode != 0:
            raise EpisodeAssemblyExecutionError(
                f"ffmpeg failed: {completed.stderr.strip() or 'unknown ffmpeg error'}"
            )
        return EpisodeAssemblyExecutorResult(
            str(output), {"return_code": str(completed.returncode)}
        )


@dataclass(frozen=True, slots=True)
class EpisodeAssemblyArtifact:
    artifact_id: str
    request_id: str
    episode_id: str
    executor_id: str
    output_path: str
    sha256_hex: str
    byte_length: int
    container_format: str
    video_codec: str
    audio_codec: str
    width: int
    height: int
    frame_rate: int
    source_asset_ids: tuple[str, ...]
    metadata: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in (
            "artifact_id",
            "request_id",
            "episode_id",
            "executor_id",
            "output_path",
            "container_format",
            "video_codec",
            "audio_codec",
        ):
            _require_non_blank(name, getattr(self, name))
        _validate_sha256(self.sha256_hex)
        if self.byte_length <= 0:
            raise EpisodeAssemblyExecutionError("byte_length must be greater than zero")
        if not self.source_asset_ids or len(self.source_asset_ids) != len(
            set(self.source_asset_ids)
        ):
            raise EpisodeAssemblyExecutionError(
                "source_asset_ids must be non-empty and unique"
            )
        object.__setattr__(self, "metadata", _freeze_metadata(self.metadata))


class EpisodeAssemblyExecutionCoordinator:
    def __init__(self, executor: EpisodeAssemblyExecutor) -> None:
        self._executor = executor

    def execute(
        self,
        request: EpisodeAssemblyRequest,
        manifest: EpisodeMediaTechnicalValidationManifest,
        output_root: Path,
    ) -> EpisodeAssemblyArtifact:
        _validate_identity(request, manifest)
        by_id = {asset.asset_id: asset for asset in manifest.assets}
        clips = tuple(
            self._resolve_clip(c.sequence_number, c.asset_id, by_id)
            for c in request.clips
        )
        output_root.mkdir(parents=True, exist_ok=True)
        output = (
            output_root
            / f"{request.request_id}{_container_extension(request.output_policy.container_format)}"
        )
        executor_request = EpisodeAssemblyExecutorRequest(
            request_id=request.request_id,
            episode_id=request.episode_id,
            clips=clips,
            output_path=str(output),
            container_format=request.output_policy.container_format,
            video_codec=request.output_policy.video_codec,
            audio_codec=request.output_policy.audio_codec,
            width=request.output_policy.width,
            height=request.output_policy.height,
            frame_rate=request.output_policy.frame_rate,
            metadata={
                "assembly_plan_id": request.assembly_plan_id,
                "technical_validation_manifest_id": manifest.technical_validation_manifest_id,
            },
        )
        result = self._executor.execute(executor_request)
        if Path(result.output_path) != output:
            raise EpisodeAssemblyExecutionError(
                "executor output_path does not match requested output_path"
            )
        body = _read_output(output)
        digest = sha256(body).hexdigest()
        material = "|".join(
            (
                request.request_id,
                manifest.technical_validation_manifest_id,
                self._executor.executor_id,
                digest,
                str(len(body)),
                ",".join(c.asset_id for c in clips),
            )
        )
        metadata = dict(result.metadata)
        metadata["technical_validation_manifest_id"] = (
            manifest.technical_validation_manifest_id
        )
        return EpisodeAssemblyArtifact(
            artifact_id=f"episode-assembly-artifact-{sha256(material.encode()).hexdigest()[:16]}",
            request_id=request.request_id,
            episode_id=request.episode_id,
            executor_id=self._executor.executor_id,
            output_path=str(output),
            sha256_hex=digest,
            byte_length=len(body),
            container_format=request.output_policy.container_format,
            video_codec=request.output_policy.video_codec,
            audio_codec=request.output_policy.audio_codec,
            width=request.output_policy.width,
            height=request.output_policy.height,
            frame_rate=request.output_policy.frame_rate,
            source_asset_ids=tuple(c.asset_id for c in clips),
            metadata=metadata,
        )

    def _resolve_clip(
        self,
        sequence_number: int,
        asset_id: str,
        by_id: Mapping[str, ValidatedMediaAsset],
    ) -> EpisodeAssemblyInputClip:
        try:
            asset = by_id[asset_id]
        except KeyError as exc:
            raise EpisodeAssemblyExecutionError(
                f"assembly asset is missing from technical validation: {asset_id}"
            ) from exc
        if asset.status is not MediaTechnicalValidationStatus.PASSED:
            raise EpisodeAssemblyExecutionError(
                f"assembly asset did not pass technical validation: {asset_id}"
            )
        _verify_asset(Path(asset.local_path), asset)
        return EpisodeAssemblyInputClip(
            sequence_number,
            asset_id,
            asset.local_path,
            asset.sha256_hex,
            asset.byte_length,
        )


def _validate_identity(
    request: EpisodeAssemblyRequest, manifest: EpisodeMediaTechnicalValidationManifest
) -> None:
    if request.episode_id != manifest.episode_id:
        raise EpisodeAssemblyExecutionError(
            "assembly request episode_id does not match technical validation manifest"
        )
    if manifest.status is not MediaTechnicalValidationStatus.PASSED:
        raise EpisodeAssemblyExecutionError(
            "technical validation manifest must pass before assembly execution"
        )
    if {c.asset_id for c in request.clips} != {
        a.asset_id for a in manifest.assets
    }:
        raise EpisodeAssemblyExecutionError(
            "assembly request assets must exactly match technical validation assets"
        )


def _verify_asset(path: Path, asset: ValidatedMediaAsset) -> None:
    if not path.exists():
        raise EpisodeAssemblyExecutionError(f"validated asset does not exist: {path}")
    if not path.is_file():
        raise EpisodeAssemblyExecutionError(f"validated asset is not a file: {path}")
    body = path.read_bytes()
    if len(body) != asset.byte_length:
        raise EpisodeAssemblyExecutionError(
            f"validated asset byte length mismatch: {path}"
        )
    if sha256(body).hexdigest() != asset.sha256_hex:
        raise EpisodeAssemblyExecutionError(f"validated asset SHA-256 mismatch: {path}")


def _read_output(path: Path) -> bytes:
    if not path.exists() or not path.is_file():
        raise EpisodeAssemblyExecutionError(f"assembly output does not exist: {path}")
    body = path.read_bytes()
    if not body:
        raise EpisodeAssemblyExecutionError("assembly output must not be empty")
    return body


def _container_extension(value: str) -> str:
    try:
        return {"mp4": ".mp4", "mov": ".mov", "webm": ".webm", "matroska": ".mkv"}[
            value.strip().lower()
        ]
    except KeyError as exc:
        raise EpisodeAssemblyExecutionError(
            f"unsupported assembly container_format: {value.strip().lower()}"
        ) from exc


def _escape_path(path: Path) -> str:
    return str(path.resolve()).replace("\\", "/").replace("'", "'\\''")


def _freeze_metadata(metadata: Mapping[str, str]) -> Mapping[str, str]:
    normalized = dict(metadata)
    for key, value in normalized.items():
        _require_non_blank("metadata key", key)
        _require_non_blank(f"metadata value for {key}", value)
    return MappingProxyType(dict(sorted(normalized.items())))


def _validate_sha256(value: str) -> None:
    if len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise EpisodeAssemblyExecutionError(
            "sha256_hex must be a lowercase SHA-256 digest"
        )


def _require_non_blank(name: str, value: str) -> None:
    if not value or not value.strip():
        raise EpisodeAssemblyExecutionError(f"{name} must not be blank")
