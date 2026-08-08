"""Deterministic, inspectable goal planning without execution authority."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum


class ProposalError(ValueError):
    """Raised when a goal or its bounded task graph is invalid."""


class RiskClass(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class DataClass(str, Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


@dataclass(frozen=True, slots=True)
class BudgetEnvelope:
    max_attempts: int
    max_runtime_seconds: int
    max_external_spend_minor: int = 0

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ProposalError("max_attempts must be positive")
        if self.max_runtime_seconds < 1:
            raise ProposalError("max_runtime_seconds must be positive")
        if self.max_external_spend_minor < 0:
            raise ProposalError("max_external_spend_minor cannot be negative")


@dataclass(frozen=True, slots=True)
class GoalSpec:
    objective: str
    acceptance_criteria: tuple[str, ...]
    risk_class: RiskClass
    data_class: DataClass
    budget: BudgetEnvelope

    def __post_init__(self) -> None:
        if not self.objective or self.objective != self.objective.strip():
            raise ProposalError("objective must be non-blank and trimmed")
        if not self.acceptance_criteria:
            raise ProposalError("at least one acceptance criterion is required")
        if any(not item or item != item.strip() for item in self.acceptance_criteria):
            raise ProposalError("acceptance criteria must be non-blank and trimmed")


@dataclass(frozen=True, slots=True)
class ProposedTask:
    task_id: str
    responsibility: str
    dependencies: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.task_id or self.task_id != self.task_id.strip():
            raise ProposalError("task_id must be non-blank and trimmed")
        if not self.responsibility or self.responsibility != self.responsibility.strip():
            raise ProposalError("responsibility must be non-blank and trimmed")
        if self.task_id in self.dependencies:
            raise ProposalError("a task cannot depend on itself")


@dataclass(frozen=True, slots=True)
class ExecutionProposal:
    proposal_id: str
    goal: GoalSpec
    tasks: tuple[ProposedTask, ...]
    topological_order: tuple[str, ...]
    privileged_execution_authorized: bool = False

    def inspect(self) -> dict[str, object]:
        """Return a stable, serializable view with no execution capability."""
        return _proposal_payload(self.goal, self.tasks, self.topological_order) | {
            "proposal_id": self.proposal_id,
            "privileged_execution_authorized": self.privileged_execution_authorized,
        }


def propose_execution(
    goal: GoalSpec,
    tasks: tuple[ProposedTask, ...],
    *,
    max_tasks: int = 64,
) -> ExecutionProposal:
    """Validate a bounded DAG and derive a deterministic proposal identity."""
    if not tasks:
        raise ProposalError("at least one task is required")
    if len(tasks) > max_tasks:
        raise ProposalError("task graph exceeds max_tasks")

    by_id = {task.task_id: task for task in tasks}
    if len(by_id) != len(tasks):
        raise ProposalError("task_id values must be unique")
    unknown = sorted(
        dependency
        for task in tasks
        for dependency in task.dependencies
        if dependency not in by_id
    )
    if unknown:
        raise ProposalError(f"unknown task dependencies: {', '.join(unknown)}")

    remaining = {task_id: set(task.dependencies) for task_id, task in by_id.items()}
    order: list[str] = []
    while remaining:
        ready = sorted(task_id for task_id, dependencies in remaining.items() if not dependencies)
        if not ready:
            raise ProposalError("task graph must be acyclic")
        order.extend(ready)
        for task_id in ready:
            del remaining[task_id]
        for dependencies in remaining.values():
            dependencies.difference_update(ready)

    normalized_tasks = tuple(sorted(tasks, key=lambda task: task.task_id))
    topological_order = tuple(order)
    payload = _proposal_payload(goal, normalized_tasks, topological_order)
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()[:24]
    return ExecutionProposal(
        proposal_id=f"proposal-{digest}",
        goal=goal,
        tasks=normalized_tasks,
        topological_order=topological_order,
    )


def _proposal_payload(
    goal: GoalSpec,
    tasks: tuple[ProposedTask, ...],
    topological_order: tuple[str, ...],
) -> dict[str, object]:
    return {
        "goal": {
            "objective": goal.objective,
            "acceptance_criteria": list(goal.acceptance_criteria),
            "risk_class": goal.risk_class.value,
            "data_class": goal.data_class.value,
            "budget": {
                "max_attempts": goal.budget.max_attempts,
                "max_runtime_seconds": goal.budget.max_runtime_seconds,
                "max_external_spend_minor": goal.budget.max_external_spend_minor,
            },
        },
        "tasks": [
            {
                "task_id": task.task_id,
                "responsibility": task.responsibility,
                "dependencies": list(task.dependencies),
            }
            for task in tasks
        ],
        "topological_order": list(topological_order),
    }
