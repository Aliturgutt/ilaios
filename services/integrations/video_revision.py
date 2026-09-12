"""Bounded prompt-driven revision of authenticated source video.

This module does not create a second Video runtime, policy engine, registry, media
store, or acceptance authority. It translates only explicit, deterministic edit
requests into the existing governed ``video.edit.*`` skills, executes them through
the canonical M18 FFmpeg engine, and binds before/after technical + independent
perceptual evidence to the exact source/output digests.

Unsupported or ambiguous edit language fails closed. Provider-native remix/edit
is intentionally outside this local deterministic slice and may only be added
when an exact capability is independently proven before network effects.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Protocol

from services.source_media import SourceMediaRecord, SourceMediaStore
from src.video_automation.media_technical_validation import (
    FfprobeMediaTechnicalProbe,
    MediaProbeObservation,
)
from src.video_automation.perceptual_review import PerceptualReviewSubmission
from src.video_automation.video_editing import EditExecutionResult
from src.video_automation.video_skills import EditKind, EditOperation

from .video_editing import GovernedVideoEditExecutor
from .video_runtime import VideoRuntimeError


class VideoRevisionError(ValueError):
    """Raised when a source-video revision cannot be materialized exactly."""


class RevisionReviewer(Protocol):
    @property
    def reviewer_id(self) -> str: ...

    def review(
        self,
        *,
        video_path: Path,
        objective: str,
        artifact_sha256: str,
        producer_id: str,
        review_id: str,
    ) -> PerceptualReviewSubmission: ...


class RevisionProbe(Protocol):
    @property
    def probe_id(self) -> str: ...

    def probe(self, path: Path) -> MediaProbeObservation: ...


@dataclass(frozen=True, slots=True)
class VideoRevisionSpec:
    """One explicit local revision instruction bound to one source asset."""

    schema: str
    source_asset_id: str
    source_sha256: str
    kind: EditKind
    parameters: Mapping[str, str | int | float | bool]

    def __post_init__(self) -> None:
        if self.schema != "ilaios.video-revision-spec.v1":
            raise VideoRevisionError("unsupported video revision schema")
        if not self.source_asset_id.startswith("src-"):
            raise VideoRevisionError("revision source asset identity is invalid")
        _sha256("source_sha256", self.source_sha256)
        object.__setattr__(
            self,
            "parameters",
            MappingProxyType(dict(sorted(self.parameters.items()))),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "source_asset_id": self.source_asset_id,
            "source_sha256": self.source_sha256,
            "kind": self.kind.value,
            "parameters": dict(self.parameters),
        }


@dataclass(frozen=True, slots=True)
class VideoRevisionOutcome:
    """Accepted exact-digest result from one governed source revision."""

    spec: VideoRevisionSpec
    edit: EditExecutionResult
    source_observation: MediaProbeObservation
    output_observation: MediaProbeObservation
    source_review: PerceptualReviewSubmission
    output_review: PerceptualReviewSubmission

    def to_runtime_outcome(self) -> dict[str, object]:
        return {
            "final_path": self.edit.output_path,
            "artifact_sha256": self.edit.sha256_hex,
            "semantic_score": self.output_review.score,
            "semantic_threshold": self.output_review.threshold,
            "clip_semantic_min_score": min(
                self.source_review.score,
                self.output_review.score,
            ),
            "generated_shot_count": 0,
            "duration_seconds": self.output_observation.duration_seconds,
            "width": self.output_observation.width,
            "height": self.output_observation.height,
            "frame_rate": self.output_observation.frames_per_second,
            "video_codec": self.output_observation.video_codec,
            "audio_codec": self.output_observation.audio_codec or "none",
            "revision_spec": self.spec.to_dict(),
            "revision_source_asset_id": self.spec.source_asset_id,
            "revision_source_sha256": self.spec.source_sha256,
            "revision_output_sha256": self.edit.sha256_hex,
            "revision_operation": self.spec.kind.value,
            "revision_before_probe_id": self.source_review.review_id,
            "revision_after_probe_id": self.output_review.review_id,
            "revision_source_review_score": self.source_review.score,
            "revision_output_review_score": self.output_review.score,
            "revision_execution_mode": "governed-local-ffmpeg",
            "revision_provider_generation_used": False,
        }


class GovernedVideoRevisionExecutor:
    """Execute one explicit source revision through existing governed edit skills."""

    PRODUCER_ID = "ilaios-governed-video-revision"

    def __init__(
        self,
        source_media: SourceMediaStore,
        editor: GovernedVideoEditExecutor,
        reviewer: RevisionReviewer,
        *,
        probe: RevisionProbe | None = None,
    ) -> None:
        self._source_media = source_media
        self._editor = editor
        self._reviewer = reviewer
        self._probe = probe or FfprobeMediaTechnicalProbe(timeout_seconds=30.0)

    def execute(
        self,
        *,
        request_id: str,
        objective: str,
        source: SourceMediaRecord,
    ) -> VideoRevisionOutcome:
        source_path = self._source_media.require_registered_path(source.asset_id)
        _verify_digest(source_path, source.sha256)
        source_observation = self._probe.probe(source_path)
        _require_source_observation(source, source_observation)

        spec = derive_video_revision_spec(objective, source=source)
        operation = EditOperation(
            operation_id=f"revision-{request_id}",
            kind=spec.kind,
            input_asset_ids=(source.asset_id,),
            output_asset_id=f"revision-{request_id}",
            parameters=spec.parameters,
        )

        source_review = self._reviewer.review(
            video_path=source_path,
            objective=(
                "Authenticated source media for a bounded edit. Judge only that the "
                "sampled frames form coherent real video content suitable for revision; "
                "do not require the requested edit to be present in the source."
            ),
            artifact_sha256=source.sha256,
            producer_id=self.PRODUCER_ID,
            review_id=f"{request_id}-revision-before",
        )
        if not source_review.passed:
            raise VideoRuntimeError("source video failed independent perceptual admission")

        edit = self._editor.execute(operation)
        output_path = Path(edit.output_path)
        _verify_digest(output_path, edit.sha256_hex)
        output_observation = self._probe.probe(output_path)
        _verify_revision_result(spec, source_observation, output_observation)

        output_review = self._reviewer.review(
            video_path=output_path,
            objective=_revision_review_objective(objective, spec),
            artifact_sha256=edit.sha256_hex,
            producer_id=self.PRODUCER_ID,
            review_id=f"{request_id}-revision-after",
        )
        if not output_review.passed:
            raise VideoRuntimeError("revised video failed independent perceptual acceptance")

        return VideoRevisionOutcome(
            spec=spec,
            edit=edit,
            source_observation=source_observation,
            output_observation=output_observation,
            source_review=source_review,
            output_review=output_review,
        )


def derive_video_revision_spec(
    objective: str,
    *,
    source: SourceMediaRecord,
) -> VideoRevisionSpec:
    """Parse exactly one supported explicit edit; ambiguity is never guessed."""

    if not isinstance(objective, str) or not objective.strip():
        raise VideoRevisionError("revision objective must not be blank")
    if objective != objective.strip() or len(objective) > 20_000:
        raise VideoRevisionError("revision objective is not normalized or is too long")

    candidates: list[tuple[EditKind, Mapping[str, str | int | float | bool]]] = []
    trim = _trim_parameters(objective, source.duration_seconds)
    if trim is not None:
        candidates.append((EditKind.TRIM, trim))
    crop = _crop_parameters(objective, source.width, source.height)
    if crop is not None:
        candidates.append((EditKind.CROP, crop))
    scale = _scale_parameters(objective)
    if scale is not None:
        candidates.append((EditKind.SCALE, scale))

    if not candidates:
        raise VideoRevisionError(
            "revision request is not an explicit supported trim, crop, or resize operation"
        )
    if len(candidates) != 1:
        raise VideoRevisionError(
            "revision request contains multiple edit operations; submit one bounded operation at a time"
        )
    kind, parameters = candidates[0]
    return VideoRevisionSpec(
        schema="ilaios.video-revision-spec.v1",
        source_asset_id=source.asset_id,
        source_sha256=source.sha256,
        kind=kind,
        parameters=parameters,
    )


def _trim_parameters(
    objective: str,
    source_duration: float,
) -> Mapping[str, str | int | float | bool] | None:
    patterns = (
        r"\b(?:trim|cut)\s+(?:this|the|my|uploaded|source)\s+video\s+from\s+(?P<start>[^\s,;]+)\s+to\s+(?P<end>[^\s,;]+)",
        r"\b(?:bu|mevcut|yüklediğim|yukledigim|kaynak)\s+videoyu\s+(?P<start>[^\s,;]+)\s*(?:ile|-)\s*(?P<end>[^\s,;]+)\s*(?:arasında|arasinda)\s*(?:kırp|kirp|kes)",
    )
    match = _first_match(objective.casefold(), patterns)
    if match is None:
        return None
    start = _timestamp(match.group("start"))
    end = _timestamp(match.group("end"))
    if start < 0 or end <= start:
        raise VideoRevisionError("trim range must have an end after its start")
    if end > source_duration + 0.25:
        raise VideoRevisionError("trim range exceeds authenticated source duration")
    return {"start_seconds": start, "duration_seconds": end - start}


def _crop_parameters(
    objective: str,
    source_width: int,
    source_height: int,
) -> Mapping[str, str | int | float | bool] | None:
    normalized = objective.casefold()
    if re.search(r"\b(?:crop|kırp|kirp)\b", normalized) is None:
        return None
    match = re.search(
        r"(?<!\d)(?P<width>\d{2,5})\s*[x×]\s*(?P<height>\d{2,5})(?!\d)",
        normalized,
    )
    if match is None:
        raise VideoRevisionError("crop request requires explicit WIDTHxHEIGHT geometry")
    width = int(match.group("width"))
    height = int(match.group("height"))
    x_match = re.search(r"\bx\s*=\s*(\d{1,5})\b", normalized)
    y_match = re.search(r"\by\s*=\s*(\d{1,5})\b", normalized)
    x = 0 if x_match is None else int(x_match.group(1))
    y = 0 if y_match is None else int(y_match.group(1))
    if width <= 0 or height <= 0 or x < 0 or y < 0:
        raise VideoRevisionError("crop geometry is outside supported bounds")
    if x + width > source_width or y + height > source_height:
        raise VideoRevisionError("crop rectangle exceeds authenticated source geometry")
    return {"width": width, "height": height, "x": x, "y": y}


def _scale_parameters(
    objective: str,
) -> Mapping[str, str | int | float | bool] | None:
    normalized = objective.casefold()
    if re.search(
        r"\b(?:resize|scale|rescale|boyutlandır|boyutlandir|ölçekle|olcekle)\b",
        normalized,
    ) is None:
        return None
    match = re.search(
        r"(?<!\d)(?P<width>\d{2,5})\s*[x×]\s*(?P<height>\d{2,5})(?!\d)",
        normalized,
    )
    if match is None:
        raise VideoRevisionError("resize request requires explicit WIDTHxHEIGHT geometry")
    width = int(match.group("width"))
    height = int(match.group("height"))
    if not 16 <= width <= 7680 or not 16 <= height <= 7680:
        raise VideoRevisionError("resize geometry is outside supported bounds")
    fps_match = re.search(r"(?<!\d)(\d{1,3})\s*fps\b", normalized)
    fps = 24 if fps_match is None else int(fps_match.group(1))
    if not 1 <= fps <= 120:
        raise VideoRevisionError("resize frame rate is outside supported bounds")
    return {
        "width": width,
        "height": height,
        "fps": fps,
        "video_codec": "libx264",
        "audio_codec": "aac",
    }


def _timestamp(value: str) -> float:
    normalized = value.strip().casefold().rstrip(".,")
    normalized = re.sub(r"(?:seconds?|secs?|sec|saniye|sn|s)$", "", normalized).strip()
    if not normalized:
        raise VideoRevisionError("trim timestamp is missing")
    parts = normalized.split(":")
    if len(parts) > 3:
        raise VideoRevisionError("trim timestamp is invalid")
    try:
        numbers = [float(part) for part in parts]
    except ValueError as error:
        raise VideoRevisionError("trim timestamp is invalid") from error
    if any(number < 0 for number in numbers):
        raise VideoRevisionError("trim timestamp must not be negative")
    if len(numbers) == 1:
        return numbers[0]
    if any(number >= 60 for number in numbers[1:]):
        raise VideoRevisionError("trim timestamp minute/second component is invalid")
    if len(numbers) == 2:
        return numbers[0] * 60 + numbers[1]
    return numbers[0] * 3600 + numbers[1] * 60 + numbers[2]


def _verify_revision_result(
    spec: VideoRevisionSpec,
    before: MediaProbeObservation,
    after: MediaProbeObservation,
) -> None:
    if after.video_stream_count != 1 or after.width <= 0 or after.height <= 0:
        raise VideoRuntimeError("revised video failed deterministic stream validation")
    if after.audio_stream_count > 1:
        raise VideoRuntimeError("revised video contains an unexpected audio stream count")

    if spec.kind is EditKind.TRIM:
        expected = float(spec.parameters["duration_seconds"])
        if abs(after.duration_seconds - expected) > 1.0:
            raise VideoRuntimeError("trimmed video duration does not match requested range")
        if (after.width, after.height) != (before.width, before.height):
            raise VideoRuntimeError("trim unexpectedly changed source geometry")
        return
    if spec.kind is EditKind.CROP:
        if after.width != int(spec.parameters["width"]) or after.height != int(
            spec.parameters["height"]
        ):
            raise VideoRuntimeError("cropped video geometry does not match requested rectangle")
        if abs(after.duration_seconds - before.duration_seconds) > 1.0:
            raise VideoRuntimeError("crop unexpectedly changed source duration")
        return
    if spec.kind is EditKind.SCALE:
        if after.width != int(spec.parameters["width"]) or after.height != int(
            spec.parameters["height"]
        ):
            raise VideoRuntimeError("resized video geometry does not match requested output")
        expected_fps = float(spec.parameters["fps"])
        if abs(after.frames_per_second - expected_fps) > 0.1:
            raise VideoRuntimeError("resized video frame rate does not match request")
        if abs(after.duration_seconds - before.duration_seconds) > 1.0:
            raise VideoRuntimeError("resize unexpectedly changed source duration")
        return
    raise VideoRuntimeError("revision operation is outside deterministic acceptance")


def _require_source_observation(
    source: SourceMediaRecord,
    observation: MediaProbeObservation,
) -> None:
    if observation.video_stream_count != 1:
        raise VideoRuntimeError("authenticated source video stream identity changed")
    if (observation.width, observation.height) != (source.width, source.height):
        raise VideoRuntimeError("authenticated source video geometry changed after admission")
    if abs(observation.duration_seconds - source.duration_seconds) > 0.25:
        raise VideoRuntimeError("authenticated source video duration changed after admission")
    if observation.video_codec != source.video_codec:
        raise VideoRuntimeError("authenticated source video codec changed after admission")


def _revision_review_objective(objective: str, spec: VideoRevisionSpec) -> str:
    return (
        "This is an authenticated-source video revised by a deterministic local media "
        "operation. Judge that it remains coherent real video content and visibly avoids "
        "corruption, blank output, placeholder/title-card substitution, or unrelated "
        "generated imagery. The deterministic technical gate separately verifies exact "
        f"{spec.kind.value} parameters. USER REVISION REQUEST: {objective}"
    )


def _verify_digest(path: Path, expected: str) -> None:
    if not path.is_file() or path.is_symlink():
        raise VideoRuntimeError("revision media path is unavailable or unsafe")
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != expected:
        raise VideoRuntimeError("revision media digest changed across execution boundary")


def _first_match(value: str, patterns: tuple[str, ...]) -> re.Match[str] | None:
    for pattern in patterns:
        match = re.search(pattern, value, flags=re.IGNORECASE)
        if match is not None:
            return match
    return None


def _sha256(name: str, value: str) -> None:
    if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        raise VideoRevisionError(f"{name} must be a lowercase SHA-256 digest")


__all__ = [
    "GovernedVideoRevisionExecutor",
    "VideoRevisionError",
    "VideoRevisionOutcome",
    "VideoRevisionSpec",
    "derive_video_revision_spec",
]
