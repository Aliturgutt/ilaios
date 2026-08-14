"""Deterministic real-media signal QA for visual and audio Video domains.

This module supplies bounded *signal-quality* evidence (black/frozen visual
intervals and silent audio intervals) for an exact artifact. It is intentionally
not a substitute for semantic/perceptual or brand review. FFmpeg execution is
routed through the existing M18 command-runner boundary.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Protocol

from .ffmpeg_media_engine import (
    CommandRunner,
    FfmpegMediaEngine,
    FfmpegMediaEngineError,
    MediaProbe,
    SubprocessCommandRunner,
)
from .video_quality import QaObservationSource, VideoQaObservation
from .video_skills import QaDomain

_DURATION_PATTERN = r"([0-9]+(?:\.[0-9]+)?)"
_BLACK_DURATION = re.compile(rf"black_duration:{_DURATION_PATTERN}")
_FREEZE_DURATION = re.compile(rf"freeze_duration:\s*{_DURATION_PATTERN}")
_SILENCE_DURATION = re.compile(rf"silence_duration:\s*{_DURATION_PATTERN}")


class MediaSignalQualityError(ValueError):
    """Raised when artifact-bound signal QA cannot be completed safely."""


@dataclass(frozen=True, slots=True)
class VisualSignalPolicy:
    max_black_fraction: float = 0.20
    max_freeze_seconds: float = 2.0

    def __post_init__(self) -> None:
        _fraction("max_black_fraction", self.max_black_fraction)
        if self.max_freeze_seconds < 0:
            raise MediaSignalQualityError("max_freeze_seconds must not be negative")


@dataclass(frozen=True, slots=True)
class AudioSignalPolicy:
    max_silence_fraction: float = 0.35

    def __post_init__(self) -> None:
        _fraction("max_silence_fraction", self.max_silence_fraction)


@dataclass(frozen=True, slots=True)
class MediaSignalQualityEvidence:
    evidence_id: str
    artifact_sha256: str
    byte_length: int
    duration_seconds: float
    black_fraction: float
    max_freeze_seconds: float
    silence_fraction: float
    max_allowed_black_fraction: float
    max_allowed_freeze_seconds: float
    max_allowed_silence_fraction: float
    visual_passed: bool
    audio_passed: bool
    probe_id: str

    def __post_init__(self) -> None:
        _text("evidence_id", self.evidence_id)
        _sha256(self.artifact_sha256)
        _text("probe_id", self.probe_id)
        if self.byte_length <= 0:
            raise MediaSignalQualityError("byte_length must be positive")
        if self.duration_seconds <= 0:
            raise MediaSignalQualityError("duration_seconds must be positive")
        _fraction("black_fraction", self.black_fraction)
        _fraction("silence_fraction", self.silence_fraction)
        _fraction("max_allowed_black_fraction", self.max_allowed_black_fraction)
        _fraction("max_allowed_silence_fraction", self.max_allowed_silence_fraction)
        if self.max_freeze_seconds < 0 or self.max_allowed_freeze_seconds < 0:
            raise MediaSignalQualityError("freeze durations must not be negative")
        expected_visual = (
            self.black_fraction <= self.max_allowed_black_fraction
            and self.max_freeze_seconds <= self.max_allowed_freeze_seconds
        )
        expected_audio = self.silence_fraction <= self.max_allowed_silence_fraction
        if self.visual_passed is not expected_visual:
            raise MediaSignalQualityError("visual signal disposition is inconsistent")
        if self.audio_passed is not expected_audio:
            raise MediaSignalQualityError("audio signal disposition is inconsistent")


class MediaProbeEngine(Protocol):
    def probe(self, path: str | Path) -> MediaProbe:
        """Return normalized media probe evidence."""


class FfmpegMediaSignalQualityProbe:
    """Measure bounded visual/audio signal defects on one exact media artifact."""

    probe_id = "ffmpeg-signal-quality-v1"

    def __init__(
        self,
        *,
        visual_policy: VisualSignalPolicy | None = None,
        audio_policy: AudioSignalPolicy | None = None,
        media_probe: MediaProbeEngine | None = None,
        runner: CommandRunner | None = None,
        ffmpeg_executable: str = "ffmpeg",
        timeout_seconds: float = 120.0,
    ) -> None:
        _text("ffmpeg_executable", ffmpeg_executable)
        if timeout_seconds <= 0:
            raise MediaSignalQualityError("timeout_seconds must be positive")
        self._visual_policy = visual_policy or VisualSignalPolicy()
        self._audio_policy = audio_policy or AudioSignalPolicy()
        self._media_probe = media_probe or FfmpegMediaEngine(
            timeout_seconds=timeout_seconds
        )
        self._runner = runner or SubprocessCommandRunner()
        self._ffmpeg = ffmpeg_executable
        self._timeout_seconds = timeout_seconds

    def probe(
        self,
        path: str | Path,
        *,
        artifact_sha256: str,
        byte_length: int,
    ) -> MediaSignalQualityEvidence:
        _sha256(artifact_sha256)
        if byte_length <= 0:
            raise MediaSignalQualityError("byte_length must be positive")
        source = Path(path)
        if source.is_symlink():
            raise MediaSignalQualityError("symbolic-link QA inputs are prohibited")
        if not source.exists() or not source.is_file():
            raise MediaSignalQualityError("QA input must be an existing regular file")
        body = source.read_bytes()
        if not body:
            raise MediaSignalQualityError("QA input must not be empty")
        if len(body) != byte_length:
            raise MediaSignalQualityError("QA input byte length mismatch")
        if sha256(body).hexdigest() != artifact_sha256:
            raise MediaSignalQualityError("QA input SHA-256 mismatch")

        technical = self._media_probe.probe(source)
        if technical.duration_seconds <= 0:
            raise MediaSignalQualityError("QA media duration must be positive")
        stream_types = {stream.get("codec_type") for stream in technical.streams}
        if "video" not in stream_types:
            raise MediaSignalQualityError("visual signal QA requires a video stream")
        if "audio" not in stream_types:
            raise MediaSignalQualityError("audio signal QA requires an audio stream")

        visual_log = self._run(
            (
                self._ffmpeg,
                "-v",
                "info",
                "-i",
                str(source),
                "-vf",
                "blackdetect=d=0.1:pix_th=0.10,freezedetect=n=-60dB:d=0.1",
                "-an",
                "-f",
                "null",
                "-",
            )
        )
        audio_log = self._run(
            (
                self._ffmpeg,
                "-v",
                "info",
                "-i",
                str(source),
                "-af",
                "silencedetect=noise=-50dB:d=0.1",
                "-vn",
                "-f",
                "null",
                "-",
            )
        )

        duration = technical.duration_seconds
        black_seconds = sum(_values(_BLACK_DURATION, visual_log))
        freeze_durations = _values(_FREEZE_DURATION, visual_log)
        silence_seconds = sum(_values(_SILENCE_DURATION, audio_log))
        black_fraction = min(1.0, black_seconds / duration)
        silence_fraction = min(1.0, silence_seconds / duration)
        max_freeze = max(freeze_durations, default=0.0)
        visual_passed = (
            black_fraction <= self._visual_policy.max_black_fraction
            and max_freeze <= self._visual_policy.max_freeze_seconds
        )
        audio_passed = silence_fraction <= self._audio_policy.max_silence_fraction
        material = "|".join(
            (
                artifact_sha256,
                str(byte_length),
                _number(duration),
                _number(black_fraction),
                _number(max_freeze),
                _number(silence_fraction),
                _number(self._visual_policy.max_black_fraction),
                _number(self._visual_policy.max_freeze_seconds),
                _number(self._audio_policy.max_silence_fraction),
                str(visual_passed),
                str(audio_passed),
                self.probe_id,
            )
        )
        evidence_id = (
            "media-signal-evidence-"
            + sha256(material.encode("utf-8")).hexdigest()[:20]
        )
        return MediaSignalQualityEvidence(
            evidence_id=evidence_id,
            artifact_sha256=artifact_sha256,
            byte_length=byte_length,
            duration_seconds=duration,
            black_fraction=black_fraction,
            max_freeze_seconds=max_freeze,
            silence_fraction=silence_fraction,
            max_allowed_black_fraction=self._visual_policy.max_black_fraction,
            max_allowed_freeze_seconds=self._visual_policy.max_freeze_seconds,
            max_allowed_silence_fraction=self._audio_policy.max_silence_fraction,
            visual_passed=visual_passed,
            audio_passed=audio_passed,
            probe_id=self.probe_id,
        )

    def _run(self, argv: tuple[str, ...]) -> str:
        try:
            result = self._runner.run(argv, timeout_seconds=self._timeout_seconds)
        except FfmpegMediaEngineError as exc:
            raise MediaSignalQualityError("FFmpeg signal QA failed") from exc
        return "\n".join((result.stdout, result.stderr))


def signal_quality_observations(
    evidence: MediaSignalQualityEvidence,
    *,
    observer_id: str,
    producer_id: str,
) -> tuple[VideoQaObservation, VideoQaObservation]:
    """Convert bounded signal evidence into VISUAL and AUDIO QA observations."""

    visual = VideoQaObservation(
        observation_id=f"visual-signal:{evidence.evidence_id}",
        domain=QaDomain.VISUAL,
        artifact_sha256=evidence.artifact_sha256,
        observer_id=observer_id,
        producer_id=producer_id,
        source=QaObservationSource.DETERMINISTIC_PROBE,
        score=1.0 if evidence.visual_passed else 0.0,
        threshold=1.0,
        evidence_reference=f"{evidence.evidence_id}:visual",
        provenance_reference=f"probe:{evidence.probe_id}",
        repair_target=(
            None
            if evidence.visual_passed
            else f"artifact:{evidence.artifact_sha256}:visual-signal"
        ),
    )
    audio = VideoQaObservation(
        observation_id=f"audio-signal:{evidence.evidence_id}",
        domain=QaDomain.AUDIO,
        artifact_sha256=evidence.artifact_sha256,
        observer_id=observer_id,
        producer_id=producer_id,
        source=QaObservationSource.DETERMINISTIC_PROBE,
        score=1.0 if evidence.audio_passed else 0.0,
        threshold=1.0,
        evidence_reference=f"{evidence.evidence_id}:audio",
        provenance_reference=f"probe:{evidence.probe_id}",
        repair_target=(
            None
            if evidence.audio_passed
            else f"artifact:{evidence.artifact_sha256}:audio-signal"
        ),
    )
    return visual, audio


def _values(pattern: re.Pattern[str], text: str) -> tuple[float, ...]:
    return tuple(float(match.group(1)) for match in pattern.finditer(text))


def _number(value: float) -> str:
    return format(value, ".12g")


def _fraction(name: str, value: float) -> None:
    if value < 0 or value > 1:
        raise MediaSignalQualityError(f"{name} must be between zero and one")


def _sha256(value: str) -> None:
    if len(value) != 64 or any(
        character not in "0123456789abcdef" for character in value
    ):
        raise MediaSignalQualityError("artifact identity must be lowercase SHA-256")


def _text(name: str, value: str) -> None:
    if not value or value != value.strip():
        raise MediaSignalQualityError(f"{name} must be non-blank and trimmed")
