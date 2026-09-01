"""Govern thumbnail generation through the canonical ILAIOS SkillRegistry."""

from __future__ import annotations

from pathlib import Path

from services.integrations.video_skill_governance import validate_video_skill
from services.runtime.routing import AgentProfile, SkillRegistry
from src.video_automation.thumbnail_generation import (
    ThumbnailArtifact,
    ThumbnailGenerationCoordinator,
)
from src.video_automation.video_skills import VIDEO_SKILLS, ThumbnailRequest, VideoSkillManifest

THUMBNAIL_SKILL_ID = "ilaios.skill.video.thumbnail.generate"


class GovernedThumbnailExecutor:
    """Validate native thumbnail authority before any media mutation occurs."""

    def __init__(
        self,
        registry: SkillRegistry,
        agent: AgentProfile,
        coordinator: ThumbnailGenerationCoordinator,
    ) -> None:
        self._registry = registry
        self._agent = agent
        self._coordinator = coordinator

    def generate(
        self,
        request: ThumbnailRequest,
        *,
        source_path: str | Path,
        source_byte_length: int,
        output_directory: str | Path,
        provenance_reference: str,
    ) -> ThumbnailArtifact:
        validate_video_skill(
            self._registry,
            self._agent,
            _manifest(THUMBNAIL_SKILL_ID),
        )
        return self._coordinator.generate(
            request,
            source_path=source_path,
            source_byte_length=source_byte_length,
            output_directory=output_directory,
            provenance_reference=provenance_reference,
        )


def _manifest(skill_id: str) -> VideoSkillManifest:
    return next(skill for skill in VIDEO_SKILLS if skill.skill_id == skill_id)
