"""Canonical M21 rendered-artifact technical validation.

M21 validates the final M20 RenderArtifact through deterministic file-integrity
checks plus independent M18/FFprobe technical inspection.

Validation includes:

- existence and readability
- checksum and file-size integrity
- valid/allowed container
- supported video codec
- expected resolution
- expected duration
- expected FPS
- required audio presence and codec
- video/audio stream integrity
- expected aspect ratio
- file-size boundaries

M21 performs no semantic/content-quality validation and does not publish media.
Those responsibilities belong to later canonical modules.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
from pathlib import Path
from typing import Mapping, Protocol

from .ffmpeg_media_engine import MediaProbe
from .models import RenderArtifact


class RenderTechnicalValidationError(ValueError):
    """Raised when M21 validation itself cannot be evaluated safely."""


class RenderTechnicalValidationStatus(str, Enum):
    """Deterministic technical validation disposition."""

    PASSED = "passed"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class RenderTechnicalValidationProfile:
    """Explicit M21 acceptance criteria."""

    allowed_containers: tuple[str, ...]
    allowed_video_codecs: tuple[str, ...]
    allowed_audio_codecs: tuple[str, ...]
    expected_width: int
    expected_height: int
    expected_duration_seconds: float
    duration_tolerance_seconds: float
    expected_fps: float
    fps_tolerance: float
    require_audio_stream: bool
    expected_aspect_ratio: str
    min_size_bytes: int
    max_size_bytes: int

    def __post_init__(self) -> None:
        if not self.allowed_containers:
            raise RenderTechnicalValidationError(
                "allowed_containers must not be empty"
            )

        if not self.allowed_video_codecs:
            raise RenderTechnicalValidationError(
                "allowed_video_codecs must not be empty"
            )

        if self.require_audio_stream and not self.allowed_audio_codecs:
            raise RenderTechnicalValidationError(
                "allowed_audio_codecs must not be empty when audio is required"
            )

        if self.expected_width <= 0 or self.expected_height <= 0:
            raise RenderTechnicalValidationError(
                "expected dimensions must be greater than zero"
            )

        if self.expected_duration_seconds <= 0:
            raise RenderTechnicalValidationError(
                "expected_duration_seconds must be greater than zero"
            )

        if self.duration_tolerance_seconds < 0:
            raise RenderTechnicalValidationError(
                "duration_tolerance_seconds must not be negative"
            )

        if self.expected_fps <= 0:
            raise RenderTechnicalValidationError(
                "expected_fps must be greater than zero"
            )

        if self.fps_tolerance < 0:
            raise RenderTechnicalValidationError(
                "fps_tolerance must not be negative"
            )

        _require_non_blank(
            "expected_aspect_ratio",
            self.expected_aspect_ratio,
        )

        if self.min_size_bytes <= 0:
            raise RenderTechnicalValidationError(
                "min_size_bytes must be greater than zero"
            )

        if self.max_size_bytes < self.min_size_bytes:
            raise RenderTechnicalValidationError(
                "max_size_bytes must be >= min_size_bytes"
            )

        object.__setattr__(
            self,
            "allowed_containers",
            tuple(
                sorted(
                    value.strip().lower()
                    for value in self.allowed_containers
                )
            ),
        )

        object.__setattr__(
            self,
            "allowed_video_codecs",
            tuple(
                sorted(
                    value.strip().lower()
                    for value in self.allowed_video_codecs
                )
            ),
        )

        object.__setattr__(
            self,
            "allowed_audio_codecs",
            tuple(
                sorted(
                    value.strip().lower()
                    for value in self.allowed_audio_codecs
                )
            ),
        )


@dataclass(frozen=True, slots=True)
class RenderTechnicalIssue:
    """One deterministic M21 validation violation."""

    code: str
    message: str

    def __post_init__(self) -> None:
        _require_non_blank("code", self.code)
        _require_non_blank("message", self.message)


@dataclass(frozen=True, slots=True)
class RenderTechnicalValidation:
    """Immutable M21 technical validation evidence."""

    validation_id: str
    artifact_id: str
    job_id: str
    status: RenderTechnicalValidationStatus
    issues: tuple[RenderTechnicalIssue, ...]
    observed_container: str
    observed_video_codec: str
    observed_audio_codec: str | None
    observed_width: int
    observed_height: int
    observed_duration_seconds: float
    observed_fps: float
    observed_aspect_ratio: str
    observed_size_bytes: int
    observed_sha256: str

    def __post_init__(self) -> None:
        for name in (
            "validation_id",
            "artifact_id",
            "job_id",
            "observed_container",
            "observed_video_codec",
            "observed_aspect_ratio",
            "observed_sha256",
        ):
            _require_non_blank(
                name,
                getattr(self, name),
            )

        if self.observed_audio_codec is not None:
            _require_non_blank(
                "observed_audio_codec",
                self.observed_audio_codec,
            )

        if self.status is RenderTechnicalValidationStatus.PASSED and self.issues:
            raise RenderTechnicalValidationError(
                "passed validation must not contain issues"
            )

        if self.status is RenderTechnicalValidationStatus.FAILED and not self.issues:
            raise RenderTechnicalValidationError(
                "failed validation must contain at least one issue"
            )


class RenderProbeEngine(Protocol):
    """M18 probe subset consumed by M21."""

    def probe(
        self,
        path: str | Path,
    ) -> MediaProbe:
        ...


class RenderTechnicalValidator:
    """Validate one canonical M20 RenderArtifact."""

    def __init__(
        self,
        *,
        probe_engine: RenderProbeEngine,
        profile: RenderTechnicalValidationProfile,
    ) -> None:
        self._probe_engine = probe_engine
        self._profile = profile

    def validate(
        self,
        artifact: RenderArtifact,
    ) -> RenderTechnicalValidation:
        path = Path(
            artifact.file_path
        )

        if not path.exists():
            raise RenderTechnicalValidationError(
                "render artifact does not exist"
            )

        if not path.is_file():
            raise RenderTechnicalValidationError(
                "render artifact path is not a file"
            )

        try:
            body = path.read_bytes()
        except OSError as exc:
            raise RenderTechnicalValidationError(
                "render artifact is unreadable"
            ) from exc

        if not body:
            raise RenderTechnicalValidationError(
                "render artifact must not be empty"
            )

        observed_sha256 = sha256(
            body
        ).hexdigest()

        observed_size = len(
            body
        )

        probe = self._probe_engine.probe(
            path
        )

        video_streams = tuple(
            stream
            for stream in probe.streams
            if stream.get("codec_type") == "video"
        )

        audio_streams = tuple(
            stream
            for stream in probe.streams
            if stream.get("codec_type") == "audio"
        )

        issues: list[
            RenderTechnicalIssue
        ] = []

        if len(video_streams) != 1:
            issues.append(
                RenderTechnicalIssue(
                    code="video_stream_integrity",
                    message=(
                        "rendered artifact must contain exactly one "
                        "video stream"
                    ),
                )
            )

        if self._profile.require_audio_stream and len(audio_streams) != 1:
            issues.append(
                RenderTechnicalIssue(
                    code="audio_stream_integrity",
                    message=(
                        "rendered artifact must contain exactly one "
                        "audio stream"
                    ),
                )
            )

        video_stream = (
            video_streams[0]
            if video_streams
            else {}
        )

        audio_stream = (
            audio_streams[0]
            if audio_streams
            else {}
        )

        observed_video_codec = _stream_text_or_unknown(
            video_stream,
            "codec_name",
        )

        observed_audio_codec = (
            _stream_text_or_none(
                audio_stream,
                "codec_name",
            )
        )

        observed_width = _stream_int_or_zero(
            video_stream,
            "width",
        )

        observed_height = _stream_int_or_zero(
            video_stream,
            "height",
        )

        observed_fps = _frame_rate_or_zero(
            video_stream,
        )

        observed_aspect_ratio = _aspect_ratio_or_unknown(
            observed_width,
            observed_height,
        )

        container = probe.format_name.lower()

        if container not in self._profile.allowed_containers:
            issues.append(
                RenderTechnicalIssue(
                    code="container_not_allowed",
                    message=f"container is not allowed: {probe.format_name}",
                )
            )

        if (
            observed_video_codec.lower()
            not in self._profile.allowed_video_codecs
        ):
            issues.append(
                RenderTechnicalIssue(
                    code="video_codec_not_allowed",
                    message=(
                        "video codec is not allowed: "
                        f"{observed_video_codec}"
                    ),
                )
            )

        if (
            self._profile.require_audio_stream
            and (
                observed_audio_codec is None
                or observed_audio_codec.lower()
                not in self._profile.allowed_audio_codecs
            )
        ):
            issues.append(
                RenderTechnicalIssue(
                    code="audio_codec_not_allowed",
                    message=(
                        "required audio codec is missing or unsupported"
                    ),
                )
            )

        if (
            observed_width
            != self._profile.expected_width
            or observed_height
            != self._profile.expected_height
        ):
            issues.append(
                RenderTechnicalIssue(
                    code="resolution_mismatch",
                    message=(
                        "expected resolution "
                        f"{self._profile.expected_width}x"
                        f"{self._profile.expected_height}, observed "
                        f"{observed_width}x{observed_height}"
                    ),
                )
            )

        duration_difference = abs(
            probe.duration_seconds
            - self._profile.expected_duration_seconds
        )

        if (
            duration_difference
            > self._profile.duration_tolerance_seconds
        ):
            issues.append(
                RenderTechnicalIssue(
                    code="duration_mismatch",
                    message=(
                        "render duration is outside configured tolerance"
                    ),
                )
            )

        fps_difference = abs(
            observed_fps
            - self._profile.expected_fps
        )

        if fps_difference > self._profile.fps_tolerance:
            issues.append(
                RenderTechnicalIssue(
                    code="fps_mismatch",
                    message=(
                        "render FPS is outside configured tolerance"
                    ),
                )
            )

        if (
            observed_aspect_ratio
            != self._profile.expected_aspect_ratio
        ):
            issues.append(
                RenderTechnicalIssue(
                    code="aspect_ratio_mismatch",
                    message=(
                        "expected aspect ratio "
                        f"{self._profile.expected_aspect_ratio}, "
                        f"observed {observed_aspect_ratio}"
                    ),
                )
            )

        if observed_size < self._profile.min_size_bytes:
            issues.append(
                RenderTechnicalIssue(
                    code="file_size_below_minimum",
                    message="render file size is below minimum",
                )
            )

        if observed_size > self._profile.max_size_bytes:
            issues.append(
                RenderTechnicalIssue(
                    code="file_size_above_maximum",
                    message="render file size is above maximum",
                )
            )

        if observed_sha256 != artifact.checksum_sha256:
            issues.append(
                RenderTechnicalIssue(
                    code="artifact_checksum_mismatch",
                    message=(
                        "RenderArtifact checksum does not match file bytes"
                    ),
                )
            )

        if observed_size != artifact.size_bytes:
            issues.append(
                RenderTechnicalIssue(
                    code="artifact_size_mismatch",
                    message=(
                        "RenderArtifact size_bytes does not match file bytes"
                    ),
                )
            )

        if artifact.codec.lower() != observed_video_codec.lower():
            issues.append(
                RenderTechnicalIssue(
                    code="artifact_video_codec_mismatch",
                    message=(
                        "RenderArtifact codec does not match probed codec"
                    ),
                )
            )

        if (
            observed_audio_codec is not None
            and artifact.audio_codec.lower()
            != observed_audio_codec.lower()
        ):
            issues.append(
                RenderTechnicalIssue(
                    code="artifact_audio_codec_mismatch",
                    message=(
                        "RenderArtifact audio codec does not match probe"
                    ),
                )
            )

        observed_resolution = (
            f"{observed_width}x{observed_height}"
        )

        if artifact.resolution != observed_resolution:
            issues.append(
                RenderTechnicalIssue(
                    code="artifact_resolution_mismatch",
                    message=(
                        "RenderArtifact resolution does not match probe"
                    ),
                )
            )

        if (
            abs(
                artifact.duration_seconds
                - probe.duration_seconds
            )
            > 1e-6
        ):
            issues.append(
                RenderTechnicalIssue(
                    code="artifact_duration_mismatch",
                    message=(
                        "RenderArtifact duration does not match probe"
                    ),
                )
            )

        if (
            abs(
                artifact.fps
                - observed_fps
            )
            > 1e-6
        ):
            issues.append(
                RenderTechnicalIssue(
                    code="artifact_fps_mismatch",
                    message=(
                        "RenderArtifact FPS does not match probe"
                    ),
                )
            )

        if artifact.aspect_ratio != observed_aspect_ratio:
            issues.append(
                RenderTechnicalIssue(
                    code="artifact_aspect_ratio_mismatch",
                    message=(
                        "RenderArtifact aspect ratio does not match probe"
                    ),
                )
            )

        normalized_issues = tuple(
            sorted(
                issues,
                key=lambda issue: issue.code,
            )
        )

        status = (
            RenderTechnicalValidationStatus.PASSED
            if not normalized_issues
            else RenderTechnicalValidationStatus.FAILED
        )

        evidence_material = "\n".join(
            (
                f"artifact_id={artifact.artifact_id}",
                f"job_id={artifact.job_id}",
                f"sha256={observed_sha256}",
                f"size={observed_size}",
                f"container={probe.format_name}",
                f"video_codec={observed_video_codec}",
                f"audio_codec={observed_audio_codec}",
                f"width={observed_width}",
                f"height={observed_height}",
                f"duration={probe.duration_seconds:.9f}",
                f"fps={observed_fps:.9f}",
                f"aspect_ratio={observed_aspect_ratio}",
                "issues="
                + ",".join(
                    issue.code
                    for issue in normalized_issues
                ),
            )
        )

        validation_id = (
            "render-technical-validation-"
            + sha256(
                evidence_material.encode("utf-8")
            ).hexdigest()[:24]
        )

        return RenderTechnicalValidation(
            validation_id=validation_id,
            artifact_id=artifact.artifact_id,
            job_id=artifact.job_id,
            status=status,
            issues=normalized_issues,
            observed_container=probe.format_name,
            observed_video_codec=observed_video_codec,
            observed_audio_codec=observed_audio_codec,
            observed_width=observed_width,
            observed_height=observed_height,
            observed_duration_seconds=probe.duration_seconds,
            observed_fps=observed_fps,
            observed_aspect_ratio=observed_aspect_ratio,
            observed_size_bytes=observed_size,
            observed_sha256=observed_sha256,
        )


def _stream_text_or_unknown(
    stream: Mapping[str, object],
    key: str,
) -> str:
    value = stream.get(key)

    if isinstance(value, str) and value.strip():
        return value

    return "unknown"


def _stream_text_or_none(
    stream: Mapping[str, object],
    key: str,
) -> str | None:
    value = stream.get(key)

    if isinstance(value, str) and value.strip():
        return value

    return None


def _stream_int_or_zero(
    stream: Mapping[str, object],
    key: str,
) -> int:
    value = stream.get(key)

    if isinstance(value, int) and value > 0:
        return value

    return 0


def _frame_rate_or_zero(
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
        return 0.0

    parts = raw.split(
        "/",
        maxsplit=1,
    )

    try:
        if len(parts) == 2:
            numerator = float(
                parts[0]
            )
            denominator = float(
                parts[1]
            )

            if denominator == 0:
                return 0.0

            return numerator / denominator

        return float(
            raw
        )
    except ValueError:
        return 0.0


def _aspect_ratio_or_unknown(
    width: int,
    height: int,
) -> str:
    if width <= 0 or height <= 0:
        return "unknown"

    from math import gcd

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
        raise RenderTechnicalValidationError(
            f"{name} must not be blank"
        )

    if value != value.strip():
        raise RenderTechnicalValidationError(
            f"{name} must not contain surrounding whitespace"
        )
