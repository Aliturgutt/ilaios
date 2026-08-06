"""Technical validation of assembled episode outputs.

This module consumes immutable assembly artifact evidence, re-verifies the
assembled file, probes it through the provider-independent media probe
contract, compares observed properties with the explicit assembly output
policy, and emits immutable final technical validation evidence.

It does not render, repair, transcode, publish, download, or mutate media.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
from hashlib import sha256
from pathlib import Path
from types import MappingProxyType

from .episode_assembly_execution import EpisodeAssemblyArtifact
from .media_technical_validation import MediaProbeObservation, MediaTechnicalProbe


class AssembledOutputTechnicalValidationError(ValueError):
    """Raised when an assembled output cannot be validated safely."""


class AssembledOutputTechnicalValidationStatus(str, Enum):
    """Normalized technical validation result for an assembled output."""

    PASSED = "passed"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class AssembledOutputTechnicalIssue:
    """One deterministic mismatch between expected and observed output."""

    code: str
    message: str

    def __post_init__(self) -> None:
        _require_non_blank("code", self.code)
        _require_non_blank("message", self.message)


@dataclass(frozen=True, slots=True)
class AssembledOutputTechnicalValidation:
    """Immutable technical validation evidence for one assembled artifact."""

    validation_id: str
    artifact_id: str
    request_id: str
    episode_id: str
    output_path: str
    sha256_hex: str
    byte_length: int
    status: AssembledOutputTechnicalValidationStatus
    observation: MediaProbeObservation
    issues: tuple[AssembledOutputTechnicalIssue, ...]
    probe_id: str
    metadata: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in (
            "validation_id",
            "artifact_id",
            "request_id",
            "episode_id",
            "output_path",
            "sha256_hex",
            "probe_id",
        ):
            _require_non_blank(name, getattr(self, name))
        _validate_sha256(self.sha256_hex)
        if self.byte_length <= 0:
            raise AssembledOutputTechnicalValidationError(
                "byte_length must be greater than zero"
            )
        if (
            self.status is AssembledOutputTechnicalValidationStatus.PASSED
            and self.issues
        ):
            raise AssembledOutputTechnicalValidationError(
                "passed validation must not contain issues"
            )
        if (
            self.status is AssembledOutputTechnicalValidationStatus.FAILED
            and not self.issues
        ):
            raise AssembledOutputTechnicalValidationError(
                "failed validation must contain at least one issue"
            )
        object.__setattr__(self, "metadata", _freeze_metadata(self.metadata))


class AssembledOutputTechnicalValidationCoordinator:
    """Re-verify and technically validate one assembled episode artifact."""

    def __init__(
        self,
        probe: MediaTechnicalProbe,
        *,
        frame_rate_tolerance: float = 0.01,
    ) -> None:
        if frame_rate_tolerance < 0:
            raise AssembledOutputTechnicalValidationError(
                "frame_rate_tolerance must not be negative"
            )
        self._probe = probe
        self._frame_rate_tolerance = frame_rate_tolerance

    def validate(
        self,
        artifact: EpisodeAssemblyArtifact,
    ) -> AssembledOutputTechnicalValidation:
        path = Path(artifact.output_path)
        _verify_artifact_evidence(path, artifact)
        observation = self._probe.probe(path)
        issues = _evaluate_observation(
            artifact,
            observation,
            frame_rate_tolerance=self._frame_rate_tolerance,
        )
        status = (
            AssembledOutputTechnicalValidationStatus.PASSED
            if not issues
            else AssembledOutputTechnicalValidationStatus.FAILED
        )
        material = "|".join(
            (
                artifact.artifact_id,
                artifact.sha256_hex,
                self._probe.probe_id,
                _canonical_container(observation.container),
                observation.video_codec.lower(),
                (observation.audio_codec or "none").lower(),
                str(observation.width),
                str(observation.height),
                _canonical_float(observation.frames_per_second),
                _canonical_float(observation.duration_seconds),
                ",".join(issue.code for issue in issues),
            )
        )
        validation_id = (
            "assembled-output-validation-"
            f"{sha256(material.encode('utf-8')).hexdigest()[:16]}"
        )
        return AssembledOutputTechnicalValidation(
            validation_id=validation_id,
            artifact_id=artifact.artifact_id,
            request_id=artifact.request_id,
            episode_id=artifact.episode_id,
            output_path=artifact.output_path,
            sha256_hex=artifact.sha256_hex,
            byte_length=artifact.byte_length,
            status=status,
            observation=observation,
            issues=issues,
            probe_id=self._probe.probe_id,
            metadata={
                "executor_id": artifact.executor_id,
                "source_asset_count": str(len(artifact.source_asset_ids)),
            },
        )


def _verify_artifact_evidence(
    path: Path,
    artifact: EpisodeAssemblyArtifact,
) -> None:
    if not path.exists():
        raise AssembledOutputTechnicalValidationError(
            f"assembled output does not exist: {path}"
        )
    if not path.is_file():
        raise AssembledOutputTechnicalValidationError(
            f"assembled output is not a file: {path}"
        )
    body = path.read_bytes()
    if len(body) != artifact.byte_length:
        raise AssembledOutputTechnicalValidationError(
            f"assembled output byte length mismatch: {path}"
        )
    if sha256(body).hexdigest() != artifact.sha256_hex:
        raise AssembledOutputTechnicalValidationError(
            f"assembled output SHA-256 mismatch: {path}"
        )


def _evaluate_observation(
    artifact: EpisodeAssemblyArtifact,
    observation: MediaProbeObservation,
    *,
    frame_rate_tolerance: float,
) -> tuple[AssembledOutputTechnicalIssue, ...]:
    issues: list[AssembledOutputTechnicalIssue] = []

    if observation.video_stream_count < 1:
        issues.append(
            AssembledOutputTechnicalIssue(
                "video_stream_missing",
                "assembled output must contain at least one video stream",
            )
        )

    expected_container = _canonical_container(artifact.container_format)
    observed_container = _canonical_container(observation.container)
    if observed_container != expected_container:
        issues.append(
            AssembledOutputTechnicalIssue(
                "container_mismatch",
                (
                    f"expected container {artifact.container_format}, "
                    f"observed {observation.container}"
                ),
            )
        )

    if observation.video_codec.lower() != artifact.video_codec.lower():
        issues.append(
            AssembledOutputTechnicalIssue(
                "video_codec_mismatch",
                (
                    f"expected video codec {artifact.video_codec}, "
                    f"observed {observation.video_codec}"
                ),
            )
        )

    observed_audio_codec = (
        observation.audio_codec.lower()
        if observation.audio_codec is not None
        else None
    )
    if observed_audio_codec != artifact.audio_codec.lower():
        issues.append(
            AssembledOutputTechnicalIssue(
                "audio_codec_mismatch",
                (
                    f"expected audio codec {artifact.audio_codec}, "
                    f"observed {observation.audio_codec or 'none'}"
                ),
            )
        )

    if observation.width != artifact.width:
        issues.append(
            AssembledOutputTechnicalIssue(
                "width_mismatch",
                f"expected width {artifact.width}, observed {observation.width}",
            )
        )

    if observation.height != artifact.height:
        issues.append(
            AssembledOutputTechnicalIssue(
                "height_mismatch",
                f"expected height {artifact.height}, observed {observation.height}",
            )
        )

    if (
        abs(observation.frames_per_second - float(artifact.frame_rate))
        > frame_rate_tolerance
    ):
        issues.append(
            AssembledOutputTechnicalIssue(
                "frame_rate_mismatch",
                (
                    f"expected frame rate {artifact.frame_rate}, "
                    f"observed {observation.frames_per_second}"
                ),
            )
        )

    return tuple(sorted(issues, key=lambda issue: issue.code))


def _canonical_container(value: str) -> str:
    normalized = value.strip().lower()
    aliases = {
        "mp4": "mp4",
        "mov,mp4,m4a,3gp,3g2,mj2": "mp4",
        "mov": "mov",
        "quicktime": "mov",
        "webm": "webm",
        "matroska,webm": "webm",
        "matroska": "matroska",
    }
    return aliases.get(normalized, normalized)


def _freeze_metadata(metadata: Mapping[str, str]) -> Mapping[str, str]:
    normalized = dict(metadata)
    for key, value in normalized.items():
        _require_non_blank("metadata key", key)
        _require_non_blank(f"metadata value for {key}", value)
    return MappingProxyType(dict(sorted(normalized.items())))


def _canonical_float(value: float) -> str:
    return format(value, ".12g")


def _validate_sha256(value: str) -> None:
    if len(value) != 64 or any(
        character not in "0123456789abcdef" for character in value
    ):
        raise AssembledOutputTechnicalValidationError(
            "sha256_hex must be a lowercase SHA-256 digest"
        )


def _require_non_blank(name: str, value: str) -> None:
    if not value or not value.strip():
        raise AssembledOutputTechnicalValidationError(
            f"{name} must not be blank"
        )
