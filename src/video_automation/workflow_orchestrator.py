"""Canonical M30 end-to-end Video Automation workflow orchestrator."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class WorkflowOrchestrationError(ValueError):
    """Raised when workflow progression would violate a canonical gate."""


class WorkflowStage(Enum):
    CREATED = "created"
    RESEARCHED = "researched"
    SCRIPTED = "scripted"
    SCENES_PLANNED = "scenes_planned"
    SHOTS_PLANNED = "shots_planned"
    ASSETS_PLANNED = "assets_planned"
    ASSETS_ACQUIRED = "assets_acquired"
    VOICE_READY = "voice_ready"
    AUDIO_READY = "audio_ready"
    CAPTIONS_READY = "captions_ready"
    TIMELINE_READY = "timeline_ready"
    RENDERED = "rendered"
    TECHNICALLY_VALIDATED = "technically_validated"
    CONTENT_VALIDATED = "content_validated"
    PUBLISH_READY = "publish_ready"
    COMPLETED = "completed"


_ORDER = tuple(WorkflowStage)


@dataclass(frozen=True, slots=True)
class WorkflowGate:
    dependencies_satisfied: bool = True
    policy_allows: bool = True
    validation_passed: bool = True
    job_state_allows: bool = True

    @property
    def passed(self) -> bool:
        return (
            self.dependencies_satisfied
            and self.policy_allows
            and self.validation_passed
            and self.job_state_allows
        )


@dataclass(frozen=True, slots=True)
class WorkflowProgress:
    job_id: str
    stage: WorkflowStage


class VideoWorkflowOrchestrator:
    """Advance the canonical workflow without provider-specific implementation logic."""

    def start(self, job_id: str) -> WorkflowProgress:
        if not job_id or job_id != job_id.strip():
            raise WorkflowOrchestrationError("job_id must be non-blank and trimmed")
        return WorkflowProgress(job_id, WorkflowStage.CREATED)

    def advance(
        self,
        progress: WorkflowProgress,
        target: WorkflowStage,
        gate: WorkflowGate,
    ) -> WorkflowProgress:
        current_index = _ORDER.index(progress.stage)
        target_index = _ORDER.index(target)
        if target_index != current_index + 1:
            raise WorkflowOrchestrationError("workflow stages must advance exactly one step")
        if not gate.passed:
            raise WorkflowOrchestrationError("workflow gate did not pass")
        return WorkflowProgress(progress.job_id, target)
