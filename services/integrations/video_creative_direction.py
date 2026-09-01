"""Governed adapter for ILAIOS Video creative-direction execution.

The adapter validates the canonical ``video.direction.cinematography`` skill in
the existing runtime SkillRegistry before invoking the provider-agnostic domain
executor. It is not a second registry, runtime, policy engine, or orchestrator.
"""

from __future__ import annotations

from collections.abc import Sequence

from services.integrations.video_skill_governance import validate_video_skill
from services.runtime.routing import AgentProfile, SkillRegistry
from src.video_automation.creative_direction_execution import (
    CinematographyExecutionResult,
    CinematographyExecutor,
)
from src.video_automation.models import Shot
from src.video_automation.video_skills import VIDEO_SKILLS, CreativeDirection

DIRECTION_SKILL_ID = "ilaios.skill.video.direction.cinematography"


class GovernedCinematographyExecutor:
    """Execute cinematography only after canonical skill governance succeeds."""

    def __init__(
        self,
        registry: SkillRegistry,
        agent: AgentProfile,
        *,
        executor: CinematographyExecutor | None = None,
    ) -> None:
        self._registry = registry
        self._agent = agent
        self._executor = executor or CinematographyExecutor()

    def execute(
        self,
        shots: Sequence[Shot],
        direction: CreativeDirection,
    ) -> CinematographyExecutionResult:
        manifest = next(
            skill for skill in VIDEO_SKILLS if skill.skill_id == DIRECTION_SKILL_ID
        )
        validate_video_skill(self._registry, self._agent, manifest)
        return self._executor.execute(shots, direction)
