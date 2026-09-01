"""Provider-independent technical validation of retrieved media assets.

This module re-verifies retrieval evidence, probes local media through an explicit
adapter contract, evaluates deterministic technical profiles, and produces
immutable validation evidence for downstream assembly. It does not select
providers, download media, mutate source assets, repair media, or execute
assembly.
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import Enum
from fractions import Fraction
from hashlib import sha256
from pathlib import Path
from types import MappingProxyType
from typing import Protocol

from .generated_asset_retrieval import (
    EpisodeGeneratedAssetRetrievalManifest,
    RetrievedGenerationAsset,
)


class MediaTechnicalValidationError(ValueError):
    """Raised when technical media validation cannot be completed safely."""


class MediaTechnicalValidationStatus(str, Enum):
    """Provider-neutral technical validation outcome."""

    PASSED = "passed"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class MediaTechnicalProfile:
    """Deterministic acceptance profile for generated video assets."""

    allowed_containers: tuple[str, ...] = ("mov,mp4,m4a,3gp,3g2,mj2", "mp4")
    allowed_video_codecs: tuple[str, ...] = ("h264", "hevc", "vp9", "av1")
    min_width: int = 720
    min_height: int = 1280
    max_width: int = 4320
    max_height: int = 7680
    min_frames_per_second: float = 23.0
    max_frames_per_second: float = 61.0
    min_duration_seconds: float = 0.1
    max_duration_seconds: float = 120.0
    require_video_stream: bool = True
    allow_audio_stream: bool = True
    duration_tolerance_seconds: float = 0.25

    def __post_init__(self) -> None:
        if not self.allowed_containers:
            raise MediaTechnicalValidationError("allowed_containers must not be empty")
        if not self.allowed_video_codecs:
            raise MediaTechnicalValidationError(
                "allowed_video_codecs must not be empty"
            )
        _validate_positive_int("min_width", self.min_width)
        _validate_positive_int("min_height", self.min_height)
        _validate_positive_int("max_width", self.max_width)
        _validate_positive_int("max_height", self.max_height)
        if self.min_width > self.max_width:
            raise MediaTechnicalValidationError("min_width must not exceed max_width")
        if self.min_height > self.max_height:
            raise MediaTechnicalValidationError(
                "min_height must not exceed max_height"
            )
        _validate_positive_float(
            "min_frames_per_second", self.min_frames_per_second
        )
        _validate_positive_float(
            "max_frames_per_second", self.max_frames_per_second
        )
        if self.min_frames_per_second > self.max_frames_per_second:
            raise MediaTechnicalValidationError(
                "min_frames_per_second must not exceed max_frames_per_second"
            )
        _validate_positive_float(
            "min_duration_seconds", self.min_duration_seconds
        )
        _validate_positive_float(
            "max_duration_seconds", self.max_duration_seconds
        )
        if self.min_duration_seconds > self.max_duration_seconds:
            raise MediaTechnicalValidationError(
                "min_duration_seconds must not exceed max_duration_seconds"
            )
        if self.duration_tolerance_seconds < 0:
            raise MediaTechnicalValidationError(
                "duration_tolerance_seconds must not be negative"
            )
        object.__setattr__(
            self,
            "allowed_containers",
            tuple(sorted(_normalize_non_blank_values(self.allowed_containers))),
        )
        object.__setattr__(
            self,
            "allowed_video_codecs",
            tuple(sorted(_normalize_non_blank_values(self.allowed_video_codecs))),
        )


@dataclass(frozen=True, slots=True)
class MediaProbeObservation:
    """Provider-neutral technical facts obtained from one local media file."""

    container: str
    duration_seconds: float
    width: int
    height: int
    frames_per_second: float
    video_codec: str
    audio_codec: str | None
    video_stream_count: int
    audio_stream_count: int
    metadata: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_non_blank("container", self.container)
        _validate_positive_float("duration_seconds", self.duration_seconds)
        _validate_non_negative_int("width", self.width)
        _validate_non_negative_int("height", self.height)
        _validate_non_negative_float(
            "frames_per_second", self.frames_per_second
        )
        _require_non_blank("video_codec", self.video_codec)
        if self.audio_codec is not None:
            _require_non_blank("audio_codec", self.audio_codec)
        _validate_non_negative_int(
            "video_stream_count", self.video_stream_count
        )
        _validate_non_negative_int(
            "audio_stream_count", self.audio_stream_count
        )
        object.__setattr__(self, "metadata", _freeze_metadata(self.metadata))


class MediaTechnicalProbe(Protocol):
    """Adapter contract for probing one local media file."""

    @property
    def probe_id(self) -> str:
        """Return the deterministic probe implementation identifier."""

    def probe(self, path: Path) -> MediaProbeObservation:
        """Return normalized technical facts for one local file."""


class FfprobeMediaTechnicalProbe:
    """Concrete JSON ffprobe adapter with no shell invocation."""

    def __init__(
        self,
        executable: str = "ffprobe",
        *,
        timeout_seconds: float = 30.0,
    ) -> None:
        _require_non_blank("executable", executable)
        _validate_positive_float("timeout_seconds", timeout_seconds)
        self._executable = executable
        self._timeout_seconds = timeout_seconds

    @property
    def probe_id(self) -> str:
        return "ffprobe-json-v1"

    def probe(self, path: Path) -> MediaProbeObservation:
        command = (
            self._executable,
            "-v",
            "error",
            "-show_entries",
            (
                "format=format_name,duration:"
                "stream=index,codec_type,codec_name,width,height,"
                "avg_frame_rate,r_frame_rate"
            ),
            "-of",
            "json",
            str(path),
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
            raise MediaTechnicalValidationError(
                "ffprobe executable was not found"
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise MediaTechnicalValidationError("ffprobe timed out") from exc
        if completed.returncode != 0:
            detail = completed.stderr.strip() or "unknown ffprobe error"
            raise MediaTechnicalValidationError(
                f"ffprobe failed: {detail}"
            )
        try:
            payload = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise MediaTechnicalValidationError(
                "ffprobe returned invalid JSON"
            ) from exc
        if not isinstance(payload, dict):
            raise MediaTechnicalValidationError(
                "ffprobe JSON root must be an object"
            )
        return _observation_from_ffprobe_payload(payload)


@dataclass(frozen=True, slots=True)
class MediaTechnicalIssue:
    """One deterministic technical profile violation."""

    code: str
    message: str

    def __post_init__(self) -> None:
        _require_non_blank("code", self.code)
        _require_non_blank("message", self.message)


@dataclass(frozen=True, slots=True)
class ValidatedMediaAsset:
    """Immutable technical validation evidence for one retrieved asset."""

    asset_id: str
    provider_id: str
    local_path: str
    sha256_hex: str
    byte_length: int
    content_type: str
    status: MediaTechnicalValidationStatus
    observation: MediaProbeObservation
    issues: tuple[MediaTechnicalIssue, ...]
    evidence_id: str
    metadata: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in (
            "asset_id",
            "provider_id",
            "local_path",
            "sha256_hex",
            "content_type",
            "evidence_id",
        ):
            _require_non_blank(name, getattr(self, name))
        _validate_sha256(self.sha256_hex)
        _validate_positive_int("byte_length", self.byte_length)
        if self.status is MediaTechnicalValidationStatus.PASSED and self.issues:
            raise MediaTechnicalValidationError(
                "passed asset must not contain technical issues"
            )
        if self.status is MediaTechnicalValidationStatus.FAILED and not self.issues:
            raise MediaTechnicalValidationError(
                "failed asset must contain at least one technical issue"
            )
        object.__setattr__(self, "metadata", _freeze_metadata(self.metadata))


@dataclass(frozen=True, slots=True)
class EpisodeMediaTechnicalValidationManifest:
    """Immutable technical media validation evidence for one episode."""

    technical_validation_manifest_id: str
    retrieval_manifest_id: str
    result_manifest_id: str
    dispatch_plan_id: str
    episode_id: str
    assets: tuple[ValidatedMediaAsset, ...]
    asset_count: int
    passed_count: int
    failed_count: int
    status: MediaTechnicalValidationStatus
    profile_id: str
    probe_id: str
    metadata: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in (
            "technical_validation_manifest_id",
            "retrieval_manifest_id",
            "result_manifest_id",
            "dispatch_plan_id",
            "episode_id",
            "profile_id",
            "probe_id",
        ):
            _require_non_blank(name, getattr(self, name))
        if self.asset_count != len(self.assets):
            raise MediaTechnicalValidationError(
                "asset_count must equal assets length"
            )
        if self.passed_count + self.failed_count != self.asset_count:
            raise MediaTechnicalValidationError(
                "passed_count plus failed_count must equal asset_count"
            )
        expected_status = (
            MediaTechnicalValidationStatus.PASSED
            if self.failed_count == 0
            else MediaTechnicalValidationStatus.FAILED
        )
        if self.status is not expected_status:
            raise MediaTechnicalValidationError(
                "manifest status does not match failed_count"
            )
        object.__setattr__(self, "metadata", _freeze_metadata(self.metadata))


class MediaTechnicalValidationCoordinator:
    """Verify retrieval evidence, probe assets, and evaluate a technical profile."""

    def __init__(
        self,
        probe: MediaTechnicalProbe,
        profile: MediaTechnicalProfile | None = None,
    ) -> None:
        self._probe = probe
        self._profile = profile or MediaTechnicalProfile()

    def validate(
        self,
        retrieval_manifest: EpisodeGeneratedAssetRetrievalManifest,
    ) -> EpisodeMediaTechnicalValidationManifest:
        profile_id = _profile_id(self._profile)
        validated = tuple(
            self._validate_asset(asset, profile_id)
            for asset in retrieval_manifest.assets
        )
        passed_count = sum(
            item.status is MediaTechnicalValidationStatus.PASSED
            for item in validated
        )
        failed_count = len(validated) - passed_count
        status = (
            MediaTechnicalValidationStatus.PASSED
            if failed_count == 0
            else MediaTechnicalValidationStatus.FAILED
        )
        canonical = _canonical_manifest_material(
            retrieval_manifest,
            validated,
            profile_id,
            self._probe.probe_id,
        )
        digest = sha256(canonical.encode("utf-8")).hexdigest()
        return EpisodeMediaTechnicalValidationManifest(
            technical_validation_manifest_id=f"media-validation-{digest[:16]}",
            retrieval_manifest_id=retrieval_manifest.retrieval_manifest_id,
            result_manifest_id=retrieval_manifest.result_manifest_id,
            dispatch_plan_id=retrieval_manifest.dispatch_plan_id,
            episode_id=retrieval_manifest.episode_id,
            assets=validated,
            asset_count=len(validated),
            passed_count=passed_count,
            failed_count=failed_count,
            status=status,
            profile_id=profile_id,
            probe_id=self._probe.probe_id,
            metadata={"source_asset_count": str(retrieval_manifest.asset_count)},
        )

    def _validate_asset(
        self,
        asset: RetrievedGenerationAsset,
        profile_id: str,
    ) -> ValidatedMediaAsset:
        path = Path(asset.local_path)
        _verify_retrieval_evidence(path, asset)
        observation = self._probe.probe(path)
        issues = _evaluate_profile(observation, self._profile)
        status = (
            MediaTechnicalValidationStatus.PASSED
            if not issues
            else MediaTechnicalValidationStatus.FAILED
        )
        canonical = "|".join(
            (
                asset.asset_id,
                asset.sha256_hex,
                profile_id,
                self._probe.probe_id,
                observation.container,
                observation.video_codec,
                str(observation.width),
                str(observation.height),
                _canonical_float(observation.frames_per_second),
                _canonical_float(observation.duration_seconds),
                ",".join(issue.code for issue in issues),
            )
        )
        evidence_id = f"media-evidence-{sha256(canonical.encode('utf-8')).hexdigest()[:16]}"
        return ValidatedMediaAsset(
            asset_id=asset.asset_id,
            provider_id=asset.provider_id,
            local_path=asset.local_path,
            sha256_hex=asset.sha256_hex,
            byte_length=asset.byte_length,
            content_type=asset.content_type,
            status=status,
            observation=observation,
            issues=issues,
            evidence_id=evidence_id,
            metadata={
                "dispatch_id": asset.dispatch_id,
                "provider_job_id": asset.provider_job_id,
            },
        )


def _verify_retrieval_evidence(
    path: Path,
    asset: RetrievedGenerationAsset,
) -> None:
    if not path.exists():
        raise MediaTechnicalValidationError(
            f"retrieved asset does not exist: {path}"
        )
    if not path.is_file():
        raise MediaTechnicalValidationError(
            f"retrieved asset is not a file: {path}"
        )
    body = path.read_bytes()
    if len(body) != asset.byte_length:
        raise MediaTechnicalValidationError(
            f"retrieved asset byte length mismatch: {path}"
        )
    actual_sha = sha256(body).hexdigest()
    if actual_sha != asset.sha256_hex:
        raise MediaTechnicalValidationError(
            f"retrieved asset SHA-256 mismatch: {path}"
        )


def _evaluate_profile(
    observation: MediaProbeObservation,
    profile: MediaTechnicalProfile,
) -> tuple[MediaTechnicalIssue, ...]:
    issues: list[MediaTechnicalIssue] = []
    if observation.container.lower() not in profile.allowed_containers:
        issues.append(
            MediaTechnicalIssue(
                "container_not_allowed",
                f"container is not allowed: {observation.container}",
            )
        )
    if profile.require_video_stream and observation.video_stream_count < 1:
        issues.append(
            MediaTechnicalIssue(
                "video_stream_missing",
                "at least one video stream is required",
            )
        )
    if observation.video_codec.lower() not in profile.allowed_video_codecs:
        issues.append(
            MediaTechnicalIssue(
                "video_codec_not_allowed",
                f"video codec is not allowed: {observation.video_codec}",
            )
        )
    if not profile.allow_audio_stream and observation.audio_stream_count > 0:
        issues.append(
            MediaTechnicalIssue(
                "audio_stream_not_allowed",
                "audio streams are not allowed",
            )
        )
    if observation.width < profile.min_width:
        issues.append(MediaTechnicalIssue("width_below_minimum", "width is below minimum"))
    if observation.width > profile.max_width:
        issues.append(MediaTechnicalIssue("width_above_maximum", "width is above maximum"))
    if observation.height < profile.min_height:
        issues.append(
            MediaTechnicalIssue("height_below_minimum", "height is below minimum")
        )
    if observation.height > profile.max_height:
        issues.append(
            MediaTechnicalIssue("height_above_maximum", "height is above maximum")
        )
    if observation.frames_per_second < profile.min_frames_per_second:
        issues.append(
            MediaTechnicalIssue("fps_below_minimum", "frame rate is below minimum")
        )
    if observation.frames_per_second > profile.max_frames_per_second:
        issues.append(
            MediaTechnicalIssue("fps_above_maximum", "frame rate is above maximum")
        )
    if (
        observation.duration_seconds + profile.duration_tolerance_seconds
        < profile.min_duration_seconds
    ):
        issues.append(
            MediaTechnicalIssue(
                "duration_below_minimum", "duration is below minimum"
            )
        )
    if (
        observation.duration_seconds - profile.duration_tolerance_seconds
        > profile.max_duration_seconds
    ):
        issues.append(
            MediaTechnicalIssue(
                "duration_above_maximum", "duration is above maximum"
            )
        )
    return tuple(sorted(issues, key=lambda issue: issue.code))


def _observation_from_ffprobe_payload(
    payload: Mapping[str, object],
) -> MediaProbeObservation:
    format_value = payload.get("format")
    streams_value = payload.get("streams")
    if not isinstance(format_value, dict):
        raise MediaTechnicalValidationError("ffprobe format object is missing")
    if not isinstance(streams_value, list):
        raise MediaTechnicalValidationError("ffprobe streams array is missing")

    container = _required_string(format_value, "format_name")
    duration = _required_float(format_value, "duration")
    video_streams = [
        stream
        for stream in streams_value
        if isinstance(stream, dict) and stream.get("codec_type") == "video"
    ]
    audio_streams = [
        stream
        for stream in streams_value
        if isinstance(stream, dict) and stream.get("codec_type") == "audio"
    ]
    if not video_streams:
        return MediaProbeObservation(
            container=container,
            duration_seconds=duration,
            width=0,
            height=0,
            frames_per_second=0.0,
            video_codec="none",
            audio_codec=(
                _required_string(audio_streams[0], "codec_name")
                if audio_streams
                else None
            ),
            video_stream_count=0,
            audio_stream_count=len(audio_streams),
            metadata={"source": "ffprobe"},
        )
    video = video_streams[0]
    fps_value = video.get("avg_frame_rate") or video.get("r_frame_rate")
    fps = _parse_frame_rate(fps_value)
    return MediaProbeObservation(
        container=container,
        duration_seconds=duration,
        width=_required_int(video, "width"),
        height=_required_int(video, "height"),
        frames_per_second=fps,
        video_codec=_required_string(video, "codec_name"),
        audio_codec=(
            _required_string(audio_streams[0], "codec_name")
            if audio_streams
            else None
        ),
        video_stream_count=len(video_streams),
        audio_stream_count=len(audio_streams),
        metadata={"source": "ffprobe"},
    )


def _parse_frame_rate(value: object) -> float:
    if not isinstance(value, str) or not value.strip():
        raise MediaTechnicalValidationError("ffprobe frame rate is missing")
    try:
        fraction = Fraction(value)
    except (ValueError, ZeroDivisionError) as exc:
        raise MediaTechnicalValidationError(
            "ffprobe frame rate is invalid"
        ) from exc
    result = float(fraction)
    _validate_positive_float("frames_per_second", result)
    return result


def _required_string(values: Mapping[str, object], key: str) -> str:
    value = values.get(key)
    if not isinstance(value, str) or not value.strip():
        raise MediaTechnicalValidationError(f"ffprobe {key} is missing")
    return value.strip().lower()


def _required_float(values: Mapping[str, object], key: str) -> float:
    value = values.get(key)
    try:
        result = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise MediaTechnicalValidationError(
            f"ffprobe {key} is invalid"
        ) from exc
    _validate_positive_float(key, result)
    return result


def _required_int(values: Mapping[str, object], key: str) -> int:
    value = values.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise MediaTechnicalValidationError(f"ffprobe {key} is invalid")
    _validate_non_negative_int(key, value)
    return value


def _profile_id(profile: MediaTechnicalProfile) -> str:
    material = "|".join(
        (
            ",".join(profile.allowed_containers),
            ",".join(profile.allowed_video_codecs),
            str(profile.min_width),
            str(profile.min_height),
            str(profile.max_width),
            str(profile.max_height),
            _canonical_float(profile.min_frames_per_second),
            _canonical_float(profile.max_frames_per_second),
            _canonical_float(profile.min_duration_seconds),
            _canonical_float(profile.max_duration_seconds),
            str(profile.require_video_stream),
            str(profile.allow_audio_stream),
            _canonical_float(profile.duration_tolerance_seconds),
        )
    )
    return f"media-profile-{sha256(material.encode('utf-8')).hexdigest()[:16]}"


def _canonical_manifest_material(
    retrieval_manifest: EpisodeGeneratedAssetRetrievalManifest,
    assets: Sequence[ValidatedMediaAsset],
    profile_id: str,
    probe_id: str,
) -> str:
    lines = [
        f"retrieval_manifest_id={retrieval_manifest.retrieval_manifest_id}",
        f"result_manifest_id={retrieval_manifest.result_manifest_id}",
        f"episode_id={retrieval_manifest.episode_id}",
        f"profile_id={profile_id}",
        f"probe_id={probe_id}",
    ]
    lines.extend(
        f"asset_id={asset.asset_id}|evidence_id={asset.evidence_id}|"
        f"status={asset.status.value}|sha256={asset.sha256_hex}"
        for asset in assets
    )
    return "\n".join(lines)


def _normalize_non_blank_values(values: Sequence[str]) -> tuple[str, ...]:
    normalized: list[str] = []
    for value in values:
        _require_non_blank("profile value", value)
        normalized.append(value.strip().lower())
    if len(normalized) != len(set(normalized)):
        raise MediaTechnicalValidationError("profile values must be unique")
    return tuple(normalized)


def _freeze_metadata(metadata: Mapping[str, str]) -> Mapping[str, str]:
    normalized = dict(metadata)
    for key, value in normalized.items():
        _require_non_blank("metadata key", key)
        _require_non_blank(f"metadata value for {key}", value)
    return MappingProxyType(dict(sorted(normalized.items())))


def _validate_sha256(value: str) -> None:
    if len(value) != 64 or any(
        character not in "0123456789abcdef" for character in value
    ):
        raise MediaTechnicalValidationError(
            "sha256_hex must be a lowercase SHA-256 digest"
        )


def _canonical_float(value: float) -> str:
    return format(value, ".12g")


def _require_non_blank(name: str, value: str) -> None:
    if not value or not value.strip():
        raise MediaTechnicalValidationError(f"{name} must not be blank")


def _validate_positive_int(name: str, value: int) -> None:
    if isinstance(value, bool) or value <= 0:
        raise MediaTechnicalValidationError(f"{name} must be greater than zero")


def _validate_non_negative_int(name: str, value: int) -> None:
    if isinstance(value, bool) or value < 0:
        raise MediaTechnicalValidationError(f"{name} must not be negative")


def _validate_positive_float(name: str, value: float) -> None:
    if value <= 0:
        raise MediaTechnicalValidationError(f"{name} must be greater than zero")


def _validate_non_negative_float(name: str, value: float) -> None:
    if value < 0:
        raise MediaTechnicalValidationError(f"{name} must not be negative")
