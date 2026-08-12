"""Bounded Personal Operations Factory for deterministic review-only automation plans."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import TypedDict


class PersonalOperationsError(PermissionError):
    """Personal operations work violates a bounded authority or approval gate."""


_ALLOWED_ACTIONS = frozenset(
    {
        "calendar_draft",
        "checklist_draft",
        "email_draft",
        "note_draft",
        "reminder_draft",
    }
)


class OperationStepProjection(TypedDict):
    step_id: str
    action: str
    target: str
    payload_sha256: str


class OperationReviewProjection(TypedDict):
    plan_id: str
    objective: str
    plan_sha256: str
    approved_for_review: bool
    approver: str
    external_applied: bool
    steps: tuple[OperationStepProjection, ...]


@dataclass(frozen=True, slots=True)
class OperationStep:
    step_id: str
    action: str
    target: str
    payload_sha256: str


@dataclass(frozen=True, slots=True)
class OperationPlan:
    plan_id: str
    objective: str
    steps: tuple[OperationStep, ...]
    plan_sha256: str
    approved_for_review: bool
    approver: str | None
    external_applied: bool = False


class PersonalOperationsFactory:
    """Create bounded automation plans without touching user accounts or external systems."""

    def __init__(self) -> None:
        self._plans: dict[str, OperationPlan] = {}

    def propose(
        self,
        plan_id: str,
        *,
        objective: str,
        steps: tuple[tuple[str, str, str, str], ...],
    ) -> OperationPlan:
        _require_id(plan_id, "plan_id")
        _require_text(objective, "objective")
        if plan_id in self._plans:
            raise PersonalOperationsError("plan_id already exists")
        if not steps:
            raise PersonalOperationsError("operation plan requires at least one step")

        normalized_steps: list[OperationStep] = []
        seen_ids: set[str] = set()
        for step_id, action, target, payload in steps:
            _require_id(step_id, "step_id")
            _require_text(action, "action")
            _require_text(target, "target")
            _require_text(payload, "payload")
            if step_id in seen_ids:
                raise PersonalOperationsError("step_id must be unique within a plan")
            if action not in _ALLOWED_ACTIONS:
                raise PersonalOperationsError(f"unsupported personal operation action: {action}")
            seen_ids.add(step_id)
            normalized_steps.append(
                OperationStep(
                    step_id=step_id,
                    action=action,
                    target=target.strip(),
                    payload_sha256=hashlib.sha256(payload.encode("utf-8")).hexdigest(),
                )
            )

        canonical = json.dumps(
            {
                "objective": objective.strip(),
                "steps": tuple(
                    {
                        "action": step.action,
                        "payload_sha256": step.payload_sha256,
                        "step_id": step.step_id,
                        "target": step.target,
                    }
                    for step in normalized_steps
                ),
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        plan = OperationPlan(
            plan_id=plan_id,
            objective=objective.strip(),
            steps=tuple(normalized_steps),
            plan_sha256=hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
            approved_for_review=False,
            approver=None,
        )
        self._plans[plan_id] = plan
        return plan

    def approve_for_review(self, plan_id: str, *, approver: str) -> OperationPlan:
        _require_text(approver, "approver")
        plan = self._plans.get(plan_id)
        if plan is None:
            raise PersonalOperationsError("operation plan does not exist")
        if plan.approved_for_review:
            raise PersonalOperationsError("operation plan already approved for review")
        approved = OperationPlan(
            plan_id=plan.plan_id,
            objective=plan.objective,
            steps=plan.steps,
            plan_sha256=plan.plan_sha256,
            approved_for_review=True,
            approver=approver.strip(),
        )
        self._plans[plan_id] = approved
        return approved

    def review_projection(self, plan_id: str) -> OperationReviewProjection:
        plan = self._plans.get(plan_id)
        if plan is None:
            raise PersonalOperationsError("operation plan does not exist")
        if not plan.approved_for_review or plan.approver is None:
            raise PersonalOperationsError("only approved operation plans may project for review")
        return {
            "plan_id": plan.plan_id,
            "objective": plan.objective,
            "plan_sha256": plan.plan_sha256,
            "approved_for_review": True,
            "approver": plan.approver,
            "external_applied": plan.external_applied,
            "steps": tuple(
                {
                    "step_id": step.step_id,
                    "action": step.action,
                    "target": step.target,
                    "payload_sha256": step.payload_sha256,
                }
                for step in plan.steps
            ),
        }

    def apply_external(self, plan_id: str) -> None:
        if plan_id not in self._plans:
            raise PersonalOperationsError("operation plan does not exist")
        raise PersonalOperationsError("external personal-operation mutation is forbidden")


def _require_id(value: str, field: str) -> None:
    if not value or value != value.strip():
        raise PersonalOperationsError(f"{field} must be non-blank and trimmed")


def _require_text(value: str, field: str) -> None:
    if not value or not value.strip():
        raise PersonalOperationsError(f"{field} must be non-blank")
