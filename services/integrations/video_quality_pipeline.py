"""Composition adapter for complete evidence-backed Video quality acceptance.

This adapter does not create a new orchestrator or acceptance authority. It
requires deterministic visual/audio signal evidence, independently produced
VISUAL/AUDIO/BRAND perceptual reviews, the existing TECHNICAL validation, the
canonical governed four-domain QA evaluator, and the existing final episode
acceptance coordinator to agree on the same artifact before returning a result.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from services.integrations.video_acceptance import VideoFinalAcceptanceCoordinator
from services.integrations.video_quality import GovernedVideoQaExecutor
from src.video_automation.assembled_output_technical_validation import (
    AssembledOutputTechnicalValidation,
)
from src.video_automation.episode_assembly_execution import EpisodeAssemblyArtifact
from src.video_automation.final_episode_acceptance import (
    FinalEpisodeAcceptanceDecision,
    FinalEpisodeAcceptancePolicy,
)
from src.video_automation.media_signal_quality import MediaSignalQualityEvidence
from src.video_automation.perceptual_review import (
    PerceptualReviewSubmission,
    admit_perceptual_reviews,
)
from src.video_automation.video_quality import VideoQaRun
from src.video_automation.video_quality_observations import (
    technical_observation_from_assembled_validation,
)
from src.video_automation.video_skills import QaDomain


class VideoQualityPipelineError(ValueError):
    """Raised when the evidence set cannot safely reach final acceptance."""


@dataclass(frozen=True, slots=True)
class VideoQualityPipelineResult:
    """Immutable composition result; acceptance authority remains downstream."""

    artifact_sha256: str
    signal_evidence_id: str
    qa_run: VideoQaRun
    acceptance: FinalEpisodeAcceptanceDecision


class GovernedVideoQualityPipeline:
    """Bind all quality evidence to one exact artifact and existing authorities."""

    def __init__(
        self,
        qa_executor: GovernedVideoQaExecutor,
        acceptance_policy: FinalEpisodeAcceptancePolicy,
    ) -> None:
        self._qa_executor = qa_executor
        self._acceptance = VideoFinalAcceptanceCoordinator(acceptance_policy)

    def evaluate(
        self,
        artifact: EpisodeAssemblyArtifact,
        technical_validation: AssembledOutputTechnicalValidation,
        signal_evidence: MediaSignalQualityEvidence,
        perceptual_reviews: tuple[PerceptualReviewSubmission, ...],
        *,
        producer_id: str,
        technical_observer_id: str,
        final_evaluator_id: str,
        prior_attempts: Mapping[str, int] | None = None,
    ) -> VideoQualityPipelineResult:
        _require_exact_artifact(
            artifact,
            technical_validation,
            signal_evidence,
        )
        if not signal_evidence.visual_passed:
            raise VideoQualityPipelineError(
                "visual signal evidence failed before perceptual final evaluation"
            )
        if not signal_evidence.audio_passed:
            raise VideoQualityPipelineError(
                "audio signal evidence failed before perceptual final evaluation"
            )

        perceptual = admit_perceptual_reviews(
            perceptual_reviews,
            artifact_sha256=artifact.sha256_hex,
            producer_id=producer_id,
        )
        required_perceptual_domains = {
            QaDomain.VISUAL,
            QaDomain.AUDIO,
            QaDomain.BRAND,
        }
        if {item.domain for item in perceptual} != required_perceptual_domains:
            raise VideoQualityPipelineError(
                "complete Video quality requires visual, audio, and brand perceptual evidence"
            )

        technical = technical_observation_from_assembled_validation(
            technical_validation,
            observer_id=technical_observer_id,
            producer_id=producer_id,
        )
        qa_run = self._qa_executor.evaluate(
            artifact.sha256_hex,
            (*perceptual, technical),
            evaluator_id=final_evaluator_id,
            prior_attempts=prior_attempts,
        )
        acceptance = self._acceptance.evaluate(
            artifact,
            technical_validation,
            qa_run,
        )
        return VideoQualityPipelineResult(
            artifact_sha256=artifact.sha256_hex,
            signal_evidence_id=signal_evidence.evidence_id,
            qa_run=qa_run,
            acceptance=acceptance,
        )


def _require_exact_artifact(
    artifact: EpisodeAssemblyArtifact,
    technical_validation: AssembledOutputTechnicalValidation,
    signal_evidence: MediaSignalQualityEvidence,
) -> None:
    identities = {
        artifact.sha256_hex,
        technical_validation.sha256_hex,
        signal_evidence.artifact_sha256,
    }
    if len(identities) != 1:
        raise VideoQualityPipelineError(
            "quality evidence does not reference one exact assembled artifact"
        )
    if technical_validation.artifact_id != artifact.artifact_id:
        raise VideoQualityPipelineError(
            "technical validation artifact ID does not match assembly artifact"
        )
    if technical_validation.request_id != artifact.request_id:
        raise VideoQualityPipelineError(
            "technical validation request ID does not match assembly artifact"
        )
    if technical_validation.episode_id != artifact.episode_id:
        raise VideoQualityPipelineError(
            "technical validation episode ID does not match assembly artifact"
        )
    if technical_validation.byte_length != artifact.byte_length:
        raise VideoQualityPipelineError(
            "technical validation byte length does not match assembly artifact"
        )
    if signal_evidence.byte_length != artifact.byte_length:
        raise VideoQualityPipelineError(
            "signal evidence byte length does not match assembly artifact"
        )
