"""Govern selective Video repair execution through the canonical SkillRegistry."""

from __future__ import annotations

from pathlib import Path

from services.integrations.video_skill_governance import validate_video_skill
from services.runtime.routing import AgentProfile, SkillRegistry
from src.video_automation.selective_repair_execution import (
    RepairExecutionEvidence,
    SelectiveRepairExecutionCoordinator,
)
from src.video_automation.video_skills import VIDEO_SKILLS, RepairRequest, VideoSkillManifest

REPAIR_SKILL_ID = "ilaios.skill.video.repair.selective"


class GovernedSelectiveRepairExecutor:
    """Validate media-mutation authority before one bounded repair attempt."""

    def __init__(
        self,
        registry: SkillRegistry,
        agent: AgentProfile,
        coordinator: SelectiveRepairExecutionCoordinator,
    ) -> None:
        self._registry = registry
        self._agent = agent
        self._coordinator = coordinator

    def execute(
        self,
        request: RepairRequest,
        *,
        source_path: str | Path,
        source_artifact_sha256: str,
        source_byte_length: int,
        output_directory: str | Path,
        provenance_reference: str,
    ) -> RepairExecutionEvidence:
        validate_video_skill(
            self._registry,
            self._agent,
            _manifest(REPAIR_SKILL_ID),
        )
        return self._coordinator.execute(
            request,
            source_path=source_path,
            source_artifact_sha256=source_artifact_sha256,
            source_byte_length=source_byte_length,
            output_directory=output_directory,
            provenance_reference=provenance_reference,
        )


def _manifest(skill_id: str) -> VideoSkillManifest:
    return next(skill for skill in VIDEO_SKILLS if skill.skill_id == skill_id)
