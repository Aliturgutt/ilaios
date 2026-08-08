from __future__ import annotations

from typing import Any

import pytest

from src.video_automation.workflow_orchestrator import (
    VideoWorkflowOrchestrator,
    WorkflowGate,
    WorkflowOrchestrationError,
    WorkflowStage,
    WorkflowStep,
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


def _full_steps(*, blocked_stage: WorkflowStage | None = None) -> tuple[WorkflowStep, ...]:
    steps: list[WorkflowStep] = []
    for stage in tuple(WorkflowStage)[1:]:
        gate = WorkflowGate(validation_passed=stage is not blocked_stage)

        def execute(context: dict[str, Any] | Any, current: WorkflowStage = stage) -> str:
            assert context["job_id"] == "job-1"
            return f"{current.value}-output"

        steps.append(
            WorkflowStep(
                target=stage,
                gate=gate,
                execute=execute,
                output_key=f"{stage.value}_result",
            )
        )
    return tuple(steps)


def test_m30_coordinates_every_canonical_stage_to_completion() -> None:
    result = VideoWorkflowOrchestrator().run("job-1", _full_steps())

    assert result.progress.stage is WorkflowStage.COMPLETED
    assert result.executed_stages == tuple(WorkflowStage)[1:]
    assert result.outputs["job_id"] == "job-1"
    for stage in tuple(WorkflowStage)[1:]:
        assert result.outputs[f"{stage.value}_result"] == f"{stage.value}-output"


def test_m30_stops_before_executing_a_stage_whose_gate_fails() -> None:
    executed: list[WorkflowStage] = []
    steps: list[WorkflowStep] = []
    blocked = WorkflowStage.CONTENT_VALIDATED

    for stage in tuple(WorkflowStage)[1:]:
        def execute(context: Any, current: WorkflowStage = stage) -> str:
            executed.append(current)
            return current.value

        steps.append(
            WorkflowStep(
                target=stage,
                gate=WorkflowGate(validation_passed=stage is not blocked),
                execute=execute,
                output_key=f"{stage.value}_result",
            )
        )

    with pytest.raises(WorkflowOrchestrationError, match="gate"):
        VideoWorkflowOrchestrator().run("job-1", tuple(steps))

    assert blocked not in executed
    assert WorkflowStage.TECHNICALLY_VALIDATED in executed
    assert WorkflowStage.PUBLISH_READY not in executed
    assert WorkflowStage.COMPLETED not in executed


def test_m30_rejects_partial_or_out_of_order_workflow_definition() -> None:
    steps = list(_full_steps())
    with pytest.raises(WorkflowOrchestrationError, match="every canonical stage"):
        VideoWorkflowOrchestrator().run("job-1", tuple(steps[:-1]))

    steps[0], steps[1] = steps[1], steps[0]
    with pytest.raises(WorkflowOrchestrationError, match="every canonical stage"):
        VideoWorkflowOrchestrator().run("job-1", tuple(steps))


def test_m30_rejects_step_without_output() -> None:
    steps = list(_full_steps())
    first = steps[0]
    steps[0] = WorkflowStep(
        target=first.target,
        gate=first.gate,
        execute=lambda context: None,
        output_key=first.output_key,
    )

    with pytest.raises(WorkflowOrchestrationError, match="produced no output"):
        VideoWorkflowOrchestrator().run("job-1", tuple(steps))
