from __future__ import annotations

import pytest

from src.video_automation.assembled_output_technical_validation import (
    AssembledOutputTechnicalValidation,
    AssembledOutputTechnicalValidationStatus,
)
from src.video_automation.media_technical_validation import MediaProbeObservation
from src.video_automation.perceptual_review import (
    PerceptualReviewerKind,
    PerceptualReviewError,
    PerceptualReviewSubmission,
    admit_perceptual_reviews,
)
from src.video_automation.video_quality import QaObservationSource, VideoQualityFoundation
from src.video_automation.video_quality_observations import (
    technical_observation_from_assembled_validation,
)
from src.video_automation.video_skills import QaDomain

ARTIFACT_SHA = "a" * 64
CRITERIA_SHA = "b" * 64


def _submission(
    domain: QaDomain,
    *,
    reviewer_id: str | None = None,
    producer_id: str = "video-producer",
    score: float = 0.95,
    repair_target: str | None = None,
    artifact_sha256: str = ARTIFACT_SHA,
) -> PerceptualReviewSubmission:
    return PerceptualReviewSubmission(
        review_id=f"review-{domain.value}",
        domain=domain,
        artifact_sha256=artifact_sha256,
        reviewer_id=reviewer_id or f"reviewer-{domain.value}",
        producer_id=producer_id,
        reviewer_kind=(
            PerceptualReviewerKind.HUMAN
            if domain is QaDomain.BRAND
            else PerceptualReviewerKind.INDEPENDENT_MODEL
        ),
        criteria_id=f"ilaios.video.{domain.value}-review",
        criteria_version="1.0.0",
        criteria_sha256=CRITERIA_SHA,
        score=score,
        threshold=0.8,
        evidence_references=(f"evidence:{domain.value}:frame-set-001",),
        provenance_reference=f"review-provider:{domain.value}",
        repair_target=repair_target,
    )


def _technical_validation() -> AssembledOutputTechnicalValidation:
    return AssembledOutputTechnicalValidation(
        validation_id="technical-validation-001",
        artifact_id="artifact-001",
        request_id="request-001",
        episode_id="episode-001",
        output_path="/evidence/final.mp4",
        sha256_hex=ARTIFACT_SHA,
        byte_length=1024,
        status=AssembledOutputTechnicalValidationStatus.PASSED,
        observation=MediaProbeObservation(
            container="mp4",
            duration_seconds=5.0,
            width=1080,
            height=1920,
            frames_per_second=30.0,
            video_codec="h264",
            audio_codec="aac",
            video_stream_count=1,
            audio_stream_count=1,
        ),
        issues=(),
        probe_id="ffprobe-json-v1",
    )


def test_human_and_model_reviews_map_to_canonical_observation_sources() -> None:
    visual = _submission(QaDomain.VISUAL).as_observation()
    brand = _submission(QaDomain.BRAND).as_observation()
    assert visual.source is QaObservationSource.INDEPENDENT_MODEL
    assert brand.source is QaObservationSource.HUMAN_REVIEW
    assert visual.domain is QaDomain.VISUAL
    assert brand.domain is QaDomain.BRAND
    assert CRITERIA_SHA in visual.provenance_reference


def test_perceptual_review_rejects_technical_domain() -> None:
    with pytest.raises(PerceptualReviewError, match="visual, audio, and brand"):
        _submission(QaDomain.TECHNICAL)


def test_perceptual_reviewer_cannot_be_artifact_producer() -> None:
    with pytest.raises(PerceptualReviewError, match="independent from artifact producer"):
        _submission(
            QaDomain.VISUAL,
            reviewer_id="video-producer",
            producer_id="video-producer",
        )


def test_failed_perceptual_review_requires_bounded_repair_target() -> None:
    with pytest.raises(PerceptualReviewError, match="requires a bounded repair target"):
        _submission(QaDomain.BRAND, score=0.2)


def test_passed_perceptual_review_cannot_request_repair() -> None:
    with pytest.raises(PerceptualReviewError, match="must not request repair"):
        _submission(QaDomain.BRAND, repair_target="scene:brand")


def test_review_set_rejects_artifact_substitution() -> None:
    forged = _submission(QaDomain.VISUAL, artifact_sha256="c" * 64)
    with pytest.raises(PerceptualReviewError, match="does not match target"):
        admit_perceptual_reviews(
            (forged,),
            artifact_sha256=ARTIFACT_SHA,
            producer_id="video-producer",
        )


def test_review_set_rejects_duplicate_domain() -> None:
    first = _submission(QaDomain.VISUAL)
    second = PerceptualReviewSubmission(
        review_id="review-visual-second",
        domain=QaDomain.VISUAL,
        artifact_sha256=ARTIFACT_SHA,
        reviewer_id="reviewer-visual-second",
        producer_id="video-producer",
        reviewer_kind=PerceptualReviewerKind.HUMAN,
        criteria_id="ilaios.video.visual-review",
        criteria_version="1.0.0",
        criteria_sha256=CRITERIA_SHA,
        score=0.9,
        threshold=0.8,
        evidence_references=("evidence:visual:second",),
        provenance_reference="human-review:second",
    )
    with pytest.raises(PerceptualReviewError, match="at most one review per domain"):
        admit_perceptual_reviews(
            (first, second),
            artifact_sha256=ARTIFACT_SHA,
            producer_id="video-producer",
        )


def test_external_visual_audio_brand_plus_technical_form_complete_qa_set() -> None:
    perceptual = admit_perceptual_reviews(
        (
            _submission(QaDomain.VISUAL),
            _submission(QaDomain.AUDIO),
            _submission(QaDomain.BRAND),
        ),
        artifact_sha256=ARTIFACT_SHA,
        producer_id="video-producer",
    )
    technical = technical_observation_from_assembled_validation(
        _technical_validation(),
        observer_id="technical-observer",
        producer_id="video-producer",
    )
    run = VideoQualityFoundation().evaluate(
        ARTIFACT_SHA,
        (*perceptual, technical),
        evaluator_id="final-evaluator",
    )
    assert run.evaluation.passed
    assert {finding.domain for finding in run.evaluation.findings} == set(QaDomain)


def test_final_evaluator_cannot_be_external_reviewer() -> None:
    perceptual = admit_perceptual_reviews(
        (
            _submission(QaDomain.VISUAL, reviewer_id="final-evaluator"),
            _submission(QaDomain.AUDIO),
            _submission(QaDomain.BRAND),
        ),
        artifact_sha256=ARTIFACT_SHA,
        producer_id="video-producer",
    )
    technical = technical_observation_from_assembled_validation(
        _technical_validation(),
        observer_id="technical-observer",
        producer_id="video-producer",
    )
    with pytest.raises(ValueError, match="externally produced observations"):
        VideoQualityFoundation().evaluate(
            ARTIFACT_SHA,
            (*perceptual, technical),
            evaluator_id="final-evaluator",
        )
