"""Compose four-domain Video QA with the existing final episode acceptance gate.

The adapter adds no new acceptance authority. It verifies that QA evidence is
artifact-bound, complete, and independently aggregated, then projects the
existing ``VideoQaRun`` into ``FinalEpisodeQualityCheck`` records consumed by
the canonical final acceptance coordinator.
"""

from __future__ import annotations

from services.integrations.video_quality import acceptance_quality_checks
from src.video_automation.assembled_output_technical_validation import (
    AssembledOutputTechnicalValidation,
)
from src.video_automation.episode_assembly_execution import EpisodeAssemblyArtifact
from src.video_automation.final_episode_acceptance import (
    FinalEpisodeAcceptanceCoordinator,
    FinalEpisodeAcceptanceDecision,
    FinalEpisodeAcceptancePolicy,
)
from src.video_automation.video_quality import VideoQaRun
from src.video_automation.video_skills import QaDomain

REQUIRED_VIDEO_QUALITY_CHECKS = tuple(
    sorted(f"{domain.value}_quality" for domain in QaDomain)
)


class VideoFinalAcceptanceError(ValueError):
    """Raised when Video QA cannot safely enter final acceptance."""


class VideoFinalAcceptanceCoordinator:
    """Bind exact four-domain QA evidence to the existing final acceptance gate."""

    def __init__(self, policy: FinalEpisodeAcceptancePolicy) -> None:
        missing = set(REQUIRED_VIDEO_QUALITY_CHECKS) - set(
            policy.required_quality_checks
        )
        if missing:
            raise VideoFinalAcceptanceError(
                "final Video acceptance policy is missing QA domains: "
                + ", ".join(sorted(missing))
            )
        self._coordinator = FinalEpisodeAcceptanceCoordinator(policy)

    def evaluate(
        self,
        artifact: EpisodeAssemblyArtifact,
        technical_validation: AssembledOutputTechnicalValidation,
        qa_run: VideoQaRun,
    ) -> FinalEpisodeAcceptanceDecision:
        _validate_qa_run(artifact, technical_validation, qa_run)
        return self._coordinator.evaluate(
            artifact,
            technical_validation,
            acceptance_quality_checks(qa_run),
        )


def _validate_qa_run(
    artifact: EpisodeAssemblyArtifact,
    technical_validation: AssembledOutputTechnicalValidation,
    qa_run: VideoQaRun,
) -> None:
    if qa_run.artifact_sha256 != artifact.sha256_hex:
        raise VideoFinalAcceptanceError(
            "Video QA artifact SHA-256 does not match assembly artifact"
        )
    if qa_run.artifact_sha256 != technical_validation.sha256_hex:
        raise VideoFinalAcceptanceError(
            "Video QA artifact SHA-256 does not match technical validation"
        )
    if qa_run.evaluation.artifact_sha256 != qa_run.artifact_sha256:
        raise VideoFinalAcceptanceError(
            "Video QA evaluation artifact identity is inconsistent"
        )

    findings = qa_run.evaluation.findings
    if len(findings) != len(QaDomain) or {item.domain for item in findings} != set(
        QaDomain
    ):
        raise VideoFinalAcceptanceError(
            "final Video acceptance requires all four QA domains"
        )
    if len(qa_run.observations) != len(QaDomain) or {
        item.domain for item in qa_run.observations
    } != set(QaDomain):
        raise VideoFinalAcceptanceError(
            "final Video acceptance requires all four QA observations"
        )
    if any(
        observation.artifact_sha256 != qa_run.artifact_sha256
        for observation in qa_run.observations
    ):
        raise VideoFinalAcceptanceError(
            "Video QA observation artifact identity is inconsistent"
        )

    evaluator_id = qa_run.evaluation.evaluator_id
    observer_ids = {item.observer_id for item in qa_run.observations}
    producer_ids = {item.producer_id for item in qa_run.observations}
    if evaluator_id in observer_ids or evaluator_id in producer_ids:
        raise VideoFinalAcceptanceError(
            "final Video evaluator must remain independent from evidence production"
        )
