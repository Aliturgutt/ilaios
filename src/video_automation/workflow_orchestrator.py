"""Canonical M30 end-to-end Video Automation workflow orchestrator."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Any


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


@dataclass(frozen=True, slots=True)
class WorkflowStep:
    """One provider-neutral executable step in the canonical workflow."""

    target: WorkflowStage
    gate: WorkflowGate
    execute: Callable[[Mapping[str, Any]], Any]
    output_key: str

    def __post_init__(self) -> None:
        if not self.output_key or self.output_key != self.output_key.strip():
            raise WorkflowOrchestrationError("output_key must be non-blank and trimmed")


@dataclass(frozen=True, slots=True)
class WorkflowRunResult:
    """Immutable result of one complete canonical workflow run."""

    progress: WorkflowProgress
    outputs: Mapping[str, Any]
    executed_stages: tuple[WorkflowStage, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "outputs", MappingProxyType(dict(self.outputs)))


class VideoWorkflowOrchestrator:
    """Coordinate the complete canonical workflow without provider-specific logic."""

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

    def run(
        self,
        job_id: str,
        steps: Sequence[WorkflowStep],
        *,
        initial_context: Mapping[str, Any] | None = None,
    ) -> WorkflowRunResult:
        """Execute the full ordered workflow, stopping before any failed gate.

        Step callables are injected by composition root code. This keeps provider SDKs
        and module-specific implementation details outside the M30 orchestrator while
        still proving that M30 coordinates the complete canonical dependency chain.
        """

        expected_targets = _ORDER[1:]
        actual_targets = tuple(step.target for step in steps)
        if actual_targets != expected_targets:
            raise WorkflowOrchestrationError(
                "complete workflow requires every canonical stage exactly once and in order"
            )

        progress = self.start(job_id)
        context: dict[str, Any] = dict(initial_context or {})
        context["job_id"] = job_id
        executed: list[WorkflowStage] = []

        for step in steps:
            next_progress = self.advance(progress, step.target, step.gate)
            if step.output_key in context:
                raise WorkflowOrchestrationError(
                    f"workflow output key already exists: {step.output_key}"
                )
            output = step.execute(MappingProxyType(dict(context)))
            if output is None:
                raise WorkflowOrchestrationError(
                    f"workflow step produced no output: {step.target.value}"
                )
            context[step.output_key] = output
            progress = next_progress
            executed.append(step.target)

        if progress.stage is not WorkflowStage.COMPLETED:
            raise WorkflowOrchestrationError("workflow did not reach completed stage")

        return WorkflowRunResult(
            progress=progress,
            outputs=context,
            executed_stages=tuple(executed),
        )
