"""Govern social publishing execution through the canonical SkillRegistry.

The underlying M24/M25 publishing package and execution modules remain the
provider-neutral implementation. This adapter only adds the existing native
``video.publish.social`` authority check before the external side-effect
boundary is entered.
"""

from __future__ import annotations

from typing import Protocol

from services.integrations.video_skill_governance import validate_video_skill
from services.runtime.routing import AgentProfile, SkillRegistry
from src.video_automation.publishing_execution import PublishingExecutionReport
from src.video_automation.publishing_package_preparation import (
    EpisodePublishingPackageManifest,
)
from src.video_automation.video_skills import VIDEO_SKILLS, VideoSkillManifest

PUBLISH_SKILL_ID = "ilaios.skill.video.publish.social"


class PublishingExecution(Protocol):
    """Narrow boundary implemented by the existing PublishingExecutionCoordinator."""

    def execute(
        self, manifest: EpisodePublishingPackageManifest
    ) -> PublishingExecutionReport:
        """Execute one already-prepared publishing manifest."""


class GovernedVideoPublishingExecutor:
    """Fail closed on skill authority before any social side effect occurs."""

    def __init__(
        self,
        registry: SkillRegistry,
        agent: AgentProfile,
        executor: PublishingExecution,
    ) -> None:
        self._registry = registry
        self._agent = agent
        self._executor = executor

    def execute(
        self, manifest: EpisodePublishingPackageManifest
    ) -> PublishingExecutionReport:
        validate_video_skill(
            self._registry,
            self._agent,
            _manifest(PUBLISH_SKILL_ID),
        )
        return self._executor.execute(manifest)


def _manifest(skill_id: str) -> VideoSkillManifest:
    return next(skill for skill in VIDEO_SKILLS if skill.skill_id == skill_id)
