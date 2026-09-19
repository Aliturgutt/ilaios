"""Govern ILAIOS-native video editing through the canonical SkillRegistry.

This adapter selects the existing immutable ``video.edit.*`` manifest for one
``EditOperation`` and validates it before delegating to the existing M13/M18
editing executor. It does not define another registry, media engine, asset
store, policy authority, or workflow orchestrator.
"""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType
from typing import Protocol

from services.integrations.video_skill_governance import validate_video_skill
from services.runtime.routing import AgentProfile, SkillRegistry
from src.video_automation.video_editing import EditExecutionResult
from src.video_automation.video_skills import (
    VIDEO_SKILLS,
    EditKind,
    EditOperation,
    VideoSkillManifest,
)

_EDIT_SKILL_IDS: Mapping[EditKind, str] = MappingProxyType(
    {
        EditKind.TRIM: "ilaios.skill.video.edit.trim",
        EditKind.CONCATENATE: "ilaios.skill.video.edit.concatenate",
        EditKind.OVERLAY: "ilaios.skill.video.edit.overlay",
        EditKind.CROP: "ilaios.skill.video.edit.crop",
        EditKind.SCALE: "ilaios.skill.video.edit.scale",
        EditKind.AUDIO_MIX: "ilaios.skill.video.edit.audio-mix",
    }
)


class VideoEditExecution(Protocol):
    """Narrow execution boundary implemented by the existing VideoEditExecutor."""

    def execute(self, operation: EditOperation) -> EditExecutionResult:
        """Execute one already-governed edit operation."""


class GovernedVideoEditExecutor:
    """Validate exact edit-skill authority before any media mutation occurs."""

    def __init__(
        self,
        registry: SkillRegistry,
        agent: AgentProfile,
        executor: VideoEditExecution,
    ) -> None:
        self._registry = registry
        self._agent = agent
        self._executor = executor

    def execute(self, operation: EditOperation) -> EditExecutionResult:
        validate_video_skill(
            self._registry,
            self._agent,
            _manifest(edit_skill_id(operation.kind)),
        )
        return self._executor.execute(operation)


def edit_skill_id(kind: EditKind) -> str:
    """Return the canonical native skill ID for one edit kind."""

    return _EDIT_SKILL_IDS[kind]


def _manifest(skill_id: str) -> VideoSkillManifest:
    return next(skill for skill in VIDEO_SKILLS if skill.skill_id == skill_id)
