"""Canonical M20 Render Engine.

M20 consumes an M19 RemotionCompositionArtifact, delegates actual rendering to
an explicit RenderExecutor, probes the produced media through the canonical M18
FFmpeg media-engine boundary, verifies the output, and produces the pre-existing
M01 RenderArtifact contract.

M20 does not perform final platform acceptance. M21 owns technical validation
policy and M22+ own later quality/publishing concerns.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from fractions import Fraction
from hashlib import sha256
from math import gcd
from pathlib import Path
from typing import Protocol

from .ffmpeg_media_engine import (
    CommandRunner,
    MediaProbe,
    SubprocessCommandRunner,
)
from .models import RenderArtifact
from .remotion_composition import RemotionCompositionArtifact


class RenderEngineError(RuntimeError):
    """Raised when canonical M20 rendering cannot complete safely."""


@dataclass(frozen=True, slots=True)
class RenderExecutionRequest:
    """Explicit rendering request passed to a concrete renderer."""

    job_id: str
    composition: RemotionCompositionArtifact
    output_path: str

    def __post_init__(self) -> None:
        _require_non_blank("job_id", self.job_id)
        _require_non_blank("output_path", self.output_path)

        if self.composition.job_id != self.job_id:
            raise RenderEngineError(
                "composition job_id does not match render request job_id"
            )


@dataclass(frozen=True, slots=True)
class RenderExecutionResult:
    """Concrete renderer output before canonical technical normalization."""

    output_path: str
    renderer_id: str

    def __post_init__(self) -> None:
        _require_non_blank("output_path", self.output_path)
        _require_non_blank("renderer_id", self.renderer_id)


class RenderExecutor(Protocol):
    """External rendering boundary used by M20."""

    def execute(
        self,
        request: RenderExecutionRequest,
    ) -> RenderExecutionResult:
        ...


class MediaProbeEngine(Protocol):
    """Subset of the M18 media-engine boundary required by M20."""

    def probe(
        self,
        path: str | Path,
    ) -> MediaProbe:
        ...


class LocalFfmpegRenderExecutor:
    """Render a deterministic local/free MP4 from an M19 composition.

    This executor is the TEST/local implementation of the M20 RenderExecutor
    contract. It reads the independently verified M19 manifest, uses its
    canonical duration, dimensions, and FPS, and produces a technically valid
    video/audio MP4 without any paid provider call.

    Full visual application of every Remotion element remains replaceable
    behind the same RenderExecutor contract.
    """

    def __init__(
        self,
        *,
        ffmpeg_executable: str = "ffmpeg",
        runner: CommandRunner | None = None,
        timeout_seconds: float = 600.0,
    ) -> None:
        _require_non_blank(
            "ffmpeg_executable",
            ffmpeg_executable,
        )

        if timeout_seconds <= 0:
            raise RenderEngineError(
                "timeout_seconds must be greater than zero"
            )

        self._ffmpeg_executable = ffmpeg_executable
        self._runner = runner or SubprocessCommandRunner()
        self._timeout_seconds = timeout_seconds

    def execute(
        self,
        request: RenderExecutionRequest,
    ) -> RenderExecutionResult:
        manifest_path = Path(
            request.composition.manifest_path
        )

        try:
            payload = json.loads(
                manifest_path.read_text(
                    encoding="utf-8"
                )
            )
        except (
            OSError,
            json.JSONDecodeError,
        ) as exc:
            raise RenderEngineError(
                "Remotion composition manifest is unreadable or invalid"
            ) from exc

        if not isinstance(payload, dict):
            raise RenderEngineError(
                "Remotion composition manifest root must be an object"
            )

        composition_payload = payload.get(
            "composition"
        )

        if not isinstance(composition_payload, dict):
            raise RenderEngineError(
                "Remotion composition manifest requires composition object"
            )

        duration_seconds = _manifest_positive_float(
            composition_payload,
            "duration_seconds",
        )
        fps = _manifest_positive_int(
            composition_payload,
            "fps",
        )
        width = _manifest_positive_int(
            composition_payload,
            "width",
        )
        height = _manifest_positive_int(
            composition_payload,
            "height",
        )

        if (
            abs(
                duration_seconds
                - request.composition.duration_seconds
            )
            > 1e-9
        ):
            raise RenderEngineError(
                "manifest duration does not match composition artifact"
            )

        if fps != request.composition.fps:
            raise RenderEngineError(
                "manifest FPS does not match composition artifact"
            )

        if (
            width != request.composition.width
            or height != request.composition.height
        ):
            raise RenderEngineError(
                "manifest dimensions do not match composition artifact"
            )

        output_path = Path(
            request.output_path
        )
        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        video_source = (
            f"color=c=black:"
            f"s={width}x{height}:"
            f"r={fps}:"
            f"d={_format_number(duration_seconds)}"
        )

        argv = (
            self._ffmpeg_executable,
            "-y",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            video_source,
            "-f",
            "lavfi",
            "-i",
            (
                "anullsrc="
                "channel_layout=stereo:"
                "sample_rate=48000"
            ),
            "-t",
            _format_number(duration_seconds),
            "-shortest",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-r",
            str(fps),
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-movflags",
            "+faststart",
            str(output_path),
        )

        self._runner.run(
            argv,
            timeout_seconds=self._timeout_seconds,
        )

        if not output_path.exists():
            raise RenderEngineError(
                "local FFmpeg renderer did not create output"
            )

        if not output_path.is_file():
            raise RenderEngineError(
                "local FFmpeg renderer output is not a file"
            )

        if output_path.stat().st_size <= 0:
            raise RenderEngineError(
                "local FFmpeg renderer output must not be empty"
            )

        return RenderExecutionResult(
            output_path=str(output_path),
            renderer_id="local-ffmpeg-renderer-v1",
        )


class RenderEngine:
    """Coordinate rendering and construct the canonical RenderArtifact."""

    def __init__(
        self,
        *,
        executor: RenderExecutor,
        probe_engine: MediaProbeEngine,
    ) -> None:
        self._executor = executor
        self._probe_engine = probe_engine

    def render(
        self,
        *,
        job_id: str,
        composition: RemotionCompositionArtifact,
        output_path: str | Path,
    ) -> RenderArtifact:
        """Render one composition and normalize verified technical metadata."""

        _require_non_blank("job_id", job_id)

        if composition.job_id != job_id:
            raise RenderEngineError(
                "composition job_id does not match requested job_id"
            )

        _verify_composition_artifacts(
            composition,
        )

        requested_output = Path(output_path)

        if requested_output.exists() and requested_output.is_dir():
            raise RenderEngineError(
                "output_path must reference a file"
            )

        requested_output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        request = RenderExecutionRequest(
            job_id=job_id,
            composition=composition,
            output_path=str(requested_output),
        )

        result = self._executor.execute(
            request,
        )

        rendered_path = Path(
            result.output_path
        )

        if rendered_path != requested_output:
            raise RenderEngineError(
                "renderer output_path does not match requested output_path"
            )

        if not rendered_path.exists():
            raise RenderEngineError(
                "renderer output does not exist"
            )

        if not rendered_path.is_file():
            raise RenderEngineError(
                "renderer output is not a file"
            )

        try:
            body = rendered_path.read_bytes()
        except OSError as exc:
            raise RenderEngineError(
                "renderer output is unreadable"
            ) from exc

        if not body:
            raise RenderEngineError(
                "renderer output must not be empty"
            )

        probe = self._probe_engine.probe(
            rendered_path
        )

        video_stream = _require_stream(
            probe.streams,
            "video",
        )

        audio_stream = _require_stream(
            probe.streams,
            "audio",
        )

        video_codec = _require_stream_text(
            video_stream,
            "codec_name",
        )

        audio_codec = _require_stream_text(
            audio_stream,
            "codec_name",
        )

        width = _require_positive_int(
            video_stream,
            "width",
        )

        height = _require_positive_int(
            video_stream,
            "height",
        )

        fps = _parse_frame_rate(
            video_stream,
        )

        if probe.duration_seconds <= 0:
            raise RenderEngineError(
                "rendered media duration must be greater than zero"
            )

        digest = sha256(
            body
        ).hexdigest()

        resolution = (
            f"{width}x{height}"
        )

        aspect_ratio = _aspect_ratio(
            width,
            height,
        )

        identity_material = "\n".join(
            (
                f"job_id={job_id}",
                f"composition_id={composition.composition_id}",
                f"renderer_id={result.renderer_id}",
                f"checksum={digest}",
                f"size_bytes={len(body)}",
                f"codec={video_codec}",
                f"resolution={resolution}",
                f"duration={probe.duration_seconds:.9f}",
                f"fps={fps:.9f}",
                f"audio_codec={audio_codec}",
                f"aspect_ratio={aspect_ratio}",
            )
        )

        artifact_id = (
            "render-artifact-"
            + sha256(
                identity_material.encode("utf-8")
            ).hexdigest()[:24]
        )

        return RenderArtifact(
            artifact_id=artifact_id,
            job_id=job_id,
            file_path=str(
                rendered_path.resolve()
            ),
            checksum_sha256=digest,
            codec=video_codec,
            resolution=resolution,
            duration_seconds=probe.duration_seconds,
            fps=fps,
            audio_codec=audio_codec,
            aspect_ratio=aspect_ratio,
            size_bytes=len(body),
        )


def _manifest_positive_float(
    payload: Mapping[str, object],
    key: str,
) -> float:
    value = payload.get(key)

    if isinstance(value, bool):
        raise RenderEngineError(
            f"manifest field {key} must be numeric"
        )

    if not isinstance(value, (int, float)):
        raise RenderEngineError(
            f"manifest field {key} must be numeric"
        )

    normalized = float(value)

    if normalized <= 0:
        raise RenderEngineError(
            f"manifest field {key} must be greater than zero"
        )

    return normalized


def _manifest_positive_int(
    payload: Mapping[str, object],
    key: str,
) -> int:
    value = payload.get(key)

    if isinstance(value, bool) or not isinstance(value, int):
        raise RenderEngineError(
            f"manifest field {key} must be an integer"
        )

    if value <= 0:
        raise RenderEngineError(
            f"manifest field {key} must be greater than zero"
        )

    return value


def _format_number(value: float) -> str:
    return format(value, ".9g")


def _verify_composition_artifacts(
    composition: RemotionCompositionArtifact,
) -> None:
    for path_value, expected_digest, label in (
        (
            composition.manifest_path,
            composition.manifest_sha256,
            "manifest",
        ),
        (
            composition.entry_source_path,
            composition.entry_source_sha256,
            "entry source",
        ),
    ):
        path = Path(path_value)

        if not path.exists() or not path.is_file():
            raise RenderEngineError(
                f"composition {label} does not exist"
            )

        try:
            body = path.read_bytes()
        except OSError as exc:
            raise RenderEngineError(
                f"composition {label} is unreadable"
            ) from exc

        actual_digest = sha256(
            body
        ).hexdigest()

        if actual_digest != expected_digest:
            raise RenderEngineError(
                f"composition {label} checksum changed"
            )


def _require_stream(
    streams: tuple[Mapping[str, object], ...],
    codec_type: str,
) -> Mapping[str, object]:
    for stream in streams:
        if stream.get("codec_type") == codec_type:
            return stream

    raise RenderEngineError(
        f"rendered media requires {codec_type} stream"
    )


def _require_stream_text(
    stream: Mapping[str, object],
    key: str,
) -> str:
    value = stream.get(key)

    if not isinstance(value, str):
        raise RenderEngineError(
            f"stream field {key} must be a string"
        )

    _require_non_blank(
        f"stream field {key}",
        value,
    )

    return value


def _require_positive_int(
    stream: Mapping[str, object],
    key: str,
) -> int:
    value = stream.get(key)

    if not isinstance(value, int):
        raise RenderEngineError(
            f"stream field {key} must be an integer"
        )

    if value <= 0:
        raise RenderEngineError(
            f"stream field {key} must be greater than zero"
        )

    return value


def _parse_frame_rate(
    stream: Mapping[str, object],
) -> float:
    raw = stream.get(
        "avg_frame_rate"
    )

    if not isinstance(raw, str):
        raw = stream.get(
            "r_frame_rate"
        )

    if not isinstance(raw, str):
        raise RenderEngineError(
            "video stream requires frame rate"
        )

    try:
        value = float(
            Fraction(raw)
        )
    except (
        ValueError,
        ZeroDivisionError,
    ) as exc:
        raise RenderEngineError(
            "video stream frame rate is invalid"
        ) from exc

    if value <= 0:
        raise RenderEngineError(
            "video stream frame rate must be greater than zero"
        )

    return value


def _aspect_ratio(
    width: int,
    height: int,
) -> str:
    divisor = gcd(
        width,
        height,
    )

    return (
        f"{width // divisor}:"
        f"{height // divisor}"
    )


def _require_non_blank(
    name: str,
    value: str,
) -> None:
    if not value or not value.strip():
        raise RenderEngineError(
            f"{name} must not be blank"
        )

    if value != value.strip():
        raise RenderEngineError(
            f"{name} must not contain surrounding whitespace"
        )
