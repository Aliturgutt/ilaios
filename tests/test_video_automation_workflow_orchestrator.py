from __future__ import annotations

import pytest

from src.video_automation.workflow_orchestrator import (
    VideoWorkflowOrchestrator,
    WorkflowGate,
    WorkflowOrchestrationError,
    WorkflowStage,
)


def test_workflow_advances_one_canonical_stage_when_gate_passes() -> None:
    orchestrator = VideoWorkflowOrchestrator()
    progress = orchestrator.start("job-1")
    progress = orchestrator.advance(progress, WorkflowStage.RESEARCHED, WorkflowGate())
    progress = orchestrator.advance(progress, WorkflowStage.SCRIPTED, WorkflowGate())
    assert progress.stage is WorkflowStage.SCRIPTED


def test_workflow_cannot_skip_stages() -> None:
    orchestrator = VideoWorkflowOrchestrator()
    progress = orchestrator.start("job-1")
    with pytest.raises(WorkflowOrchestrationError, match="exactly one"):
        orchestrator.advance(progress, WorkflowStage.SCRIPTED, WorkflowGate())


def test_workflow_cannot_bypass_policy_validation_or_state_gate() -> None:
    orchestrator = VideoWorkflowOrchestrator()
    progress = orchestrator.start("job-1")
    for gate in (
        WorkflowGate(dependencies_satisfied=False),
        WorkflowGate(policy_allows=False),
        WorkflowGate(validation_passed=False),
        WorkflowGate(job_state_allows=False),
    ):
        with pytest.raises(WorkflowOrchestrationError, match="gate"):
            orchestrator.advance(progress, WorkflowStage.RESEARCHED, gate)
