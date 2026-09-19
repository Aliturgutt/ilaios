from __future__ import annotations

from dataclasses import replace

import pytest

from services.integrations.video_quality import GovernedVideoQaExecutor
from services.integrations.video_quality_pipeline import (
    GovernedVideoQualityPipeline,
    VideoQualityPipelineError,
)
from services.integrations.video_skill_governance import approve_video_skills
from services.runtime.routing import AgentProfile, SkillRegistry
from src.video_automation.assembled_output_technical_validation import (
    AssembledOutputTechnicalValidation,
    AssembledOutputTechnicalValidationStatus,
)
from src.video_automation.episode_assembly_execution import EpisodeAssemblyArtifact
from src.video_automation.final_episode_acceptance import (
    FinalEpisodeAcceptancePolicy,
    FinalEpisodeAcceptanceStatus,
)
from src.video_automation.media_signal_quality import MediaSignalQualityEvidence
from src.video_automation.media_technical_validation import MediaProbeObservation
from src.video_automation.perceptual_review import (
    PerceptualReviewerKind,
    PerceptualReviewSubmission,
)
from src.video_automation.video_skills import QaDomain

ARTIFACT_SHA = "a" * 64
CRITERIA_SHA = "b" * 64


def _artifact() -> EpisodeAssemblyArtifact:
    return EpisodeAssemblyArtifact(
        artifact_id="artifact-001",
        request_id="request-001",
        episode_id="episode-001",
        executor_id="ffmpeg-assembly-v1",
        output_path="/evidence/final.mp4",
        sha256_hex=ARTIFACT_SHA,
        byte_length=1024,
        container_format="mp4",
        video_codec="h264",
        audio_codec="aac",
        width=1080,
        height=1920,
        frame_rate=30,
        source_asset_ids=("source-001",),
    )


def _technical() -> AssembledOutputTechnicalValidation:
    return AssembledOutputTechnicalValidation(
        validation_id="technical-001",
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


def _signal(*, visual_passed: bool = True, audio_passed: bool = True) -> MediaSignalQualityEvidence:
    black_fraction = 0.01 if visual_passed else 0.8
    freeze_seconds = 0.1 if visual_passed else 3.0
    silence_fraction = 0.01 if audio_passed else 0.8
    return MediaSignalQualityEvidence(
        evidence_id="signal-evidence-001",
        artifact_sha256=ARTIFACT_SHA,
        byte_length=1024,
        duration_seconds=5.0,
        black_fraction=black_fraction,
        max_freeze_seconds=freeze_seconds,
        silence_fraction=silence_fraction,
        max_allowed_black_fraction=0.2,
        max_allowed_freeze_seconds=2.0,
        max_allowed_silence_fraction=0.35,
        visual_passed=visual_passed,
        audio_passed=audio_passed,
        probe_id="ffmpeg-signal-quality-v1",
    )


def _reviews(*, brand_score: float = 0.95) -> tuple[PerceptualReviewSubmission, ...]:
    submissions: list[PerceptualReviewSubmission] = []
    for domain in (QaDomain.VISUAL, QaDomain.AUDIO, QaDomain.BRAND):
        score = brand_score if domain is QaDomain.BRAND else 0.95
        submissions.append(
            PerceptualReviewSubmission(
                review_id=f"review-{domain.value}",
                domain=domain,
                artifact_sha256=ARTIFACT_SHA,
                reviewer_id=f"reviewer-{domain.value}",
                producer_id="video-producer",
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
                evidence_references=(f"evidence:{domain.value}:001",),
                provenance_reference=f"review-provider:{domain.value}",
                repair_target=("scene:brand" if score < 0.8 else None),
            )
        )
    return tuple(submissions)


def _pipeline() -> GovernedVideoQualityPipeline:
    registry = SkillRegistry()
    approve_video_skills(registry)
    qa = GovernedVideoQaExecutor(
        registry,
        AgentProfile(
            "qa-worker",
            frozenset({"media.read", "media.write"}),
        ),
    )
    return GovernedVideoQualityPipeline(
        qa,
        FinalEpisodeAcceptancePolicy(
            required_quality_checks=(
                "audio_quality",
                "brand_quality",
                "technical_quality",
                "visual_quality",
            ),
            min_duration_seconds=1.0,
            max_duration_seconds=10.0,
            require_audio_stream=True,
            min_source_asset_count=1,
        ),
    )


def test_complete_quality_pipeline_accepts_only_one_exact_artifact() -> None:
    result = _pipeline().evaluate(
        _artifact(),
        _technical(),
        _signal(),
        _reviews(),
        producer_id="video-producer",
        technical_observer_id="technical-observer",
        final_evaluator_id="final-evaluator",
    )
    assert result.artifact_sha256 == ARTIFACT_SHA
    assert result.signal_evidence_id == "signal-evidence-001"
    assert result.qa_run.evaluation.passed
    assert result.acceptance.status is FinalEpisodeAcceptanceStatus.ACCEPTED


def test_pipeline_stops_before_perceptual_acceptance_on_visual_signal_failure() -> None:
    with pytest.raises(VideoQualityPipelineError, match="visual signal evidence failed"):
        _pipeline().evaluate(
            _artifact(),
            _technical(),
            _signal(visual_passed=False),
            _reviews(),
            producer_id="video-producer",
            technical_observer_id="technical-observer",
            final_evaluator_id="final-evaluator",
        )


def test_pipeline_stops_before_perceptual_acceptance_on_audio_signal_failure() -> None:
    with pytest.raises(VideoQualityPipelineError, match="audio signal evidence failed"):
        _pipeline().evaluate(
            _artifact(),
            _technical(),
            _signal(audio_passed=False),
            _reviews(),
            producer_id="video-producer",
            technical_observer_id="technical-observer",
            final_evaluator_id="final-evaluator",
        )


def test_pipeline_rejects_incomplete_perceptual_domain_set() -> None:
    with pytest.raises(VideoQualityPipelineError, match="visual, audio, and brand"):
        _pipeline().evaluate(
            _artifact(),
            _technical(),
            _signal(),
            _reviews()[:-1],
            producer_id="video-producer",
            technical_observer_id="technical-observer",
            final_evaluator_id="final-evaluator",
        )


def test_pipeline_rejects_cross_artifact_signal_evidence() -> None:
    forged_signal = replace(_signal(), artifact_sha256="c" * 64)
    with pytest.raises(VideoQualityPipelineError, match="one exact assembled artifact"):
        _pipeline().evaluate(
            _artifact(),
            _technical(),
            forged_signal,
            _reviews(),
            producer_id="video-producer",
            technical_observer_id="technical-observer",
            final_evaluator_id="final-evaluator",
        )


def test_pipeline_rejects_cross_artifact_technical_id() -> None:
    forged = replace(_technical(), artifact_id="different-artifact")
    with pytest.raises(VideoQualityPipelineError, match="artifact ID"):
        _pipeline().evaluate(
            _artifact(),
            forged,
            _signal(),
            _reviews(),
            producer_id="video-producer",
            technical_observer_id="technical-observer",
            final_evaluator_id="final-evaluator",
        )


def test_failed_brand_review_cannot_reach_final_acceptance() -> None:
    result = _pipeline().evaluate(
        _artifact(),
        _technical(),
        _signal(),
        _reviews(brand_score=0.2),
        producer_id="video-producer",
        technical_observer_id="technical-observer",
        final_evaluator_id="final-evaluator",
    )
    assert not result.qa_run.evaluation.passed
    assert result.acceptance.status is FinalEpisodeAcceptanceStatus.REJECTED
    assert result.qa_run.repairs[0].target == "scene:brand"
