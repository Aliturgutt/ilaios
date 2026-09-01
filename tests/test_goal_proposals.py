"""Deterministic bounded proposal tests for PLATFORM.P06."""

from __future__ import annotations

import pytest

from services.control_plane import (
    BudgetEnvelope,
    DataClass,
    GoalSpec,
    ProposalError,
    ProposedTask,
    RiskClass,
    propose_execution,
)


def _goal() -> GoalSpec:
    return GoalSpec(
        objective="Produce an inspectable governed result",
        acceptance_criteria=("Output is validated", "Evidence is durable"),
        risk_class=RiskClass.MEDIUM,
        data_class=DataClass.INTERNAL,
        budget=BudgetEnvelope(max_attempts=3, max_runtime_seconds=600),
    )


def test_proposal_is_deterministic_inspectable_and_non_privileged() -> None:
    tasks = (
        ProposedTask("validate", "Validate output", ("produce",)),
        ProposedTask("produce", "Produce output", ("prepare",)),
        ProposedTask("prepare", "Prepare inputs"),
    )

    first = propose_execution(_goal(), tasks)
    second = propose_execution(_goal(), tuple(reversed(tasks)))

    assert first == second
    assert first.topological_order == ("prepare", "produce", "validate")
    assert first.privileged_execution_authorized is False
    assert first.inspect()["goal"] == {
        "objective": "Produce an inspectable governed result",
        "acceptance_criteria": ["Output is validated", "Evidence is durable"],
        "risk_class": "medium",
        "data_class": "internal",
        "budget": {
            "max_attempts": 3,
            "max_runtime_seconds": 600,
            "max_external_spend_minor": 0,
        },
    }


@pytest.mark.parametrize(  # type: ignore[misc, unused-ignore]
    "tasks, message",
    [
        (
            (ProposedTask("one", "One", ("missing",)),),
            "unknown task dependencies",
        ),
        (
            (
                ProposedTask("one", "One", ("two",)),
                ProposedTask("two", "Two", ("one",)),
            ),
            "acyclic",
        ),
    ],
)
def test_invalid_dependency_graphs_fail_closed(
    tasks: tuple[ProposedTask, ...], message: str
) -> None:
    with pytest.raises(ProposalError, match=message):
        propose_execution(_goal(), tasks)


def test_task_bound_is_enforced() -> None:
    tasks = tuple(ProposedTask(f"task-{index}", "Bounded") for index in range(3))
    with pytest.raises(ProposalError, match="exceeds max_tasks"):
        propose_execution(_goal(), tasks, max_tasks=2)
