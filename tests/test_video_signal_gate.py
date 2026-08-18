from __future__ import annotations

from pathlib import Path

import pytest

from services.integrations.video_signal_gate import (
    SignalGatedSemanticVideoReviewer,
    VideoSignalGateError,
)
from src.video_automation.media_signal_quality import MediaSignalQualityEvidence
from src.video_automation.perceptual_review import (
    PerceptualReviewerKind,
    PerceptualReviewSubmission,
)
from src.video_automation.video_skills import QaDomain


_SHA = "a" * 64
_CRITERIA_SHA = "b" * 64


class _Probe:
    def __init__(self, *, visual: bool = True, audio: bool = True) -> None:
        self.visual = visual
        self.audio = audio

    def probe(self, path, *, artifact_sha256, byte_length):
        return MediaSignalQualityEvidence(
            evidence_id="signal-evidence-1",
            artifact_sha256=artifact_sha256,
            byte_length=byte_length,
            duration_seconds=4.0,
            black_fraction=0.0 if self.visual else 0.5,
            max_freeze_seconds=0.0,
            silence_fraction=0.0 if self.audio else 0.8,
            max_allowed_black_fraction=0.2,
            max_allowed_freeze_seconds=2.0,
            max_allowed_silence_fraction=0.35,
            visual_passed=self.visual,
            audio_passed=self.audio,
            probe_id="fake-signal-probe",
        )


class _Reviewer:
    reviewer_id = "independent-reviewer"

    def __init__(self) -> None:
        self.calls = 0

    def review(
        self,
        *,
        video_path: Path,
        objective: str,
        artifact_sha256: str,
        producer_id: str,
        review_id: str,
    ) -> PerceptualReviewSubmission:
        self.calls += 1
        return PerceptualReviewSubmission(
            review_id=review_id,
            domain=QaDomain.VISUAL,
            artifact_sha256=artifact_sha256,
            reviewer_id=self.reviewer_id,
            producer_id=producer_id,
            reviewer_kind=PerceptualReviewerKind.INDEPENDENT_MODEL,
            criteria_id="semantic-video",
            criteria_version="1",
            criteria_sha256=_CRITERIA_SHA,
            score=1.0,
            threshold=0.8,
            evidence_references=("semantic-review",),
            provenance_reference="provider:independent-reviewer",
        )


def _media(tmp_path: Path) -> Path:
    path = tmp_path / "artifact.mp4"
    path.write_bytes(b"not-real-media-but-probe-is-faked")
    return path


def test_signal_gate_runs_before_semantic_review_and_retains_final_evidence(
    tmp_path: Path,
) -> None:
    reviewer = _Reviewer()
    gate = SignalGatedSemanticVideoReviewer(reviewer, probe=_Probe())  # type: ignore[arg-type]
    submission = gate.review(
        video_path=_media(tmp_path),
        objective="Create a product film.",
        artifact_sha256=_SHA,
        producer_id="video-producer",
        review_id="review-1",
    )
    assert submission.passed is True
    assert reviewer.calls == 1
    evidence = gate.evidence_for(_SHA)
    assert evidence is not None
    assert evidence.visual_passed is True
    assert evidence.audio_passed is True


def test_visual_signal_failure_blocks_semantic_reviewer(tmp_path: Path) -> None:
    reviewer = _Reviewer()
    gate = SignalGatedSemanticVideoReviewer(
        reviewer,
        probe=_Probe(visual=False),  # type: ignore[arg-type]
    )
    with pytest.raises(VideoSignalGateError, match="visual signal QA failed"):
        gate.review(
            video_path=_media(tmp_path),
            objective="Create a product film.",
            artifact_sha256=_SHA,
            producer_id="video-producer",
            review_id="review-1",
        )
    assert reviewer.calls == 0


def test_audio_signal_failure_blocks_semantic_reviewer(tmp_path: Path) -> None:
    reviewer = _Reviewer()
    gate = SignalGatedSemanticVideoReviewer(
        reviewer,
        probe=_Probe(audio=False),  # type: ignore[arg-type]
    )
    with pytest.raises(VideoSignalGateError, match="audio signal QA failed"):
        gate.review(
            video_path=_media(tmp_path),
            objective="Create a product film.",
            artifact_sha256=_SHA,
            producer_id="video-producer",
            review_id="review-1",
        )
    assert reviewer.calls == 0
