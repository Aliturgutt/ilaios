"""Pre-acceptance deterministic media-signal gate for provider Video output.

The canonical provider runtime already performs technical validation and an
independent semantic review. This adapter composes the existing FFmpeg-backed
``media_signal_quality`` probe in front of that reviewer so black/frozen visual
output or excessive silence cannot reach semantic/final acceptance merely by
matching the prompt.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from src.video_automation.media_signal_quality import (
    FfmpegMediaSignalQualityProbe,
    MediaSignalQualityEvidence,
)
from src.video_automation.perceptual_review import PerceptualReviewSubmission


class VideoSignalGateError(RuntimeError):
    """Raised when exact-artifact deterministic signal quality fails."""


class SemanticReviewer(Protocol):
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


class SignalGatedSemanticVideoReviewer:
    """Require deterministic signal PASS before independent semantic review."""

    def __init__(
        self,
        delegate: SemanticReviewer,
        *,
        probe: FfmpegMediaSignalQualityProbe | None = None,
    ) -> None:
        self._delegate = delegate
        self._probe = probe or FfmpegMediaSignalQualityProbe()
        self._evidence: dict[str, MediaSignalQualityEvidence] = {}

    @property
    def reviewer_id(self) -> str:
        return self._delegate.reviewer_id

    def review(
        self,
        *,
        video_path: Path,
        objective: str,
        artifact_sha256: str,
        producer_id: str,
        review_id: str,
    ) -> PerceptualReviewSubmission:
        try:
            byte_length = video_path.stat().st_size
        except OSError as exc:
            raise VideoSignalGateError("signal QA input is unavailable") from exc
        evidence = self._probe.probe(
            video_path,
            artifact_sha256=artifact_sha256,
            byte_length=byte_length,
        )
        self._evidence[artifact_sha256] = evidence
        if not evidence.visual_passed:
            raise VideoSignalGateError(
                "deterministic visual signal QA failed before semantic acceptance"
            )
        if not evidence.audio_passed:
            raise VideoSignalGateError(
                "deterministic audio signal QA failed before semantic acceptance"
            )
        return self._delegate.review(
            video_path=video_path,
            objective=objective,
            artifact_sha256=artifact_sha256,
            producer_id=producer_id,
            review_id=review_id,
        )

    def evidence_for(self, artifact_sha256: str) -> MediaSignalQualityEvidence | None:
        return self._evidence.get(artifact_sha256)


__all__ = [
    "SignalGatedSemanticVideoReviewer",
    "VideoSignalGateError",
]
