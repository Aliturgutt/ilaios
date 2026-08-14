"""Governed Video Factory QA adapter over the canonical SkillRegistry.

This adapter wires the existing Video QA and selective-repair skills into the
single runtime governance chain.  It does not define a second registry,
provider router, policy engine, evidence store, or workflow orchestrator.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from services.integrations.video_skill_governance import validate_video_skill
from services.runtime.routing import AgentProfile, SkillRegistry
from src.video_automation.final_episode_acceptance import FinalEpisodeQualityCheck
from src.video_automation.video_quality import (
    VideoQaObservation,
    VideoQaRun,
    VideoQualityFoundation,
)
from src.video_automation.video_skills import VIDEO_SKILLS, QaDomain, VideoSkillManifest

QA_SKILL_ID = "ilaios.skill.video.qa.evaluate"
REPAIR_SKILL_ID = "ilaios.skill.video.repair.selective"


class GovernedVideoQaExecutor:
    """Run four-domain QA only after canonical skill governance succeeds."""

    def __init__(
        self,
        registry: SkillRegistry,
        agent: AgentProfile,
        *,
        foundation: VideoQualityFoundation | None = None,
    ) -> None:
        self._registry = registry
        self._agent = agent
        self._foundation = foundation or VideoQualityFoundation()

    def evaluate(
        self,
        artifact_sha256: str,
        observations: Sequence[VideoQaObservation],
        *,
        evaluator_id: str,
        prior_attempts: Mapping[str, int] | None = None,
    ) -> VideoQaRun:
        validate_video_skill(self._registry, self._agent, _manifest(QA_SKILL_ID))
        if any(not observation.passed for observation in observations):
            validate_video_skill(
                self._registry,
                self._agent,
                _manifest(REPAIR_SKILL_ID),
            )
        return self._foundation.evaluate(
            artifact_sha256,
            observations,
            evaluator_id=evaluator_id,
            prior_attempts=prior_attempts,
        )


def acceptance_quality_checks(run: VideoQaRun) -> tuple[FinalEpisodeQualityCheck, ...]:
    """Project independent QA findings into the existing final acceptance boundary."""
    return tuple(
        FinalEpisodeQualityCheck(
            check_code=_acceptance_code(finding.domain),
            passed=finding.passed,
            evidence_id=finding.evidence_reference,
            detail=(
                f"{finding.domain.value} QA score "
                f"{format(finding.score, '.12g')} against threshold "
                f"{format(finding.threshold, '.12g')}"
            ),
        )
        for finding in sorted(run.evaluation.findings, key=lambda item: item.domain.value)
    )


def _manifest(skill_id: str) -> VideoSkillManifest:
    return next(skill for skill in VIDEO_SKILLS if skill.skill_id == skill_id)


def _acceptance_code(domain: QaDomain) -> str:
    return f"{domain.value}_quality"
