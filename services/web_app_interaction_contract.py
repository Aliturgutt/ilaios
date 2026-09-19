"""Deterministic Phase-4 Web App interaction and state-machine contracts.

This module is contract-only. It does not execute mutations, advance domain state,
publish events, or create alternate Policy/Approval/Tool/Audit/Evidence authorities.
It binds UI intents to planned API mutation contracts and the Phase-3 authorization
contract so downstream runtime work can remain fail-closed and auditable.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Literal

from services.web_app_auth_contract import WebAppAuthContract
from services.web_app_spec import WebAppSpec

ProjectionMode = Literal["none", "notification", "realtime", "realtime+notification"]


class WebAppInteractionContractError(ValueError):
    """The interaction/state-machine contract is incomplete, ambiguous, or unsafe."""


@dataclass(frozen=True, slots=True)
class WebAppStateDefinition:
    state_id: str
    terminal: bool = False


@dataclass(frozen=True, slots=True)
class WebAppTransitionContract:
    transition_id: str
    from_state: str
    to_state: str
    ui_event: str
    api_mutation_id: str
    auth_action_id: str
    permission: str
    policy_required: Literal[True] = True
    admission_required: Literal[True] = True
    approval_required: bool = False
    audit_required: Literal[True] = True
    evidence_required: Literal[True] = True
    projection: ProjectionMode = "none"

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class WebAppStateMachineContract:
    machine_id: str
    domain_subject: str
    initial_state: str
    states: tuple[WebAppStateDefinition, ...]
    transitions: tuple[WebAppTransitionContract, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "machine_id": self.machine_id,
            "domain_subject": self.domain_subject,
            "initial_state": self.initial_state,
            "states": [asdict(state) for state in self.states],
            "transitions": [transition.to_dict() for transition in self.transitions],
        }


@dataclass(frozen=True, slots=True)
class WebAppInteractionContract:
    schema_version: str
    app_id: str
    project_id: str
    spec_sha256: str
    auth_contract_sha256: str
    machines: tuple[WebAppStateMachineContract, ...]
    interaction_chain: tuple[str, ...]
    policy_authority: Literal["canonical-policy-engine"]
    approval_authority: Literal["canonical-approval-engine"]
    tool_authority: Literal["canonical-tool-gateway"]
    validation_authority: Literal["canonical-validation-pipeline"]
    audit_authority: Literal["canonical-audit-evidence-chain"]
    direct_state_mutation_allowed: Literal[False]
    direct_event_publication_allowed: Literal[False]

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "app_id": self.app_id,
            "project_id": self.project_id,
            "spec_sha256": self.spec_sha256,
            "auth_contract_sha256": self.auth_contract_sha256,
            "machines": [machine.to_dict() for machine in self.machines],
            "interaction_chain": list(self.interaction_chain),
            "policy_authority": self.policy_authority,
            "approval_authority": self.approval_authority,
            "tool_authority": self.tool_authority,
            "validation_authority": self.validation_authority,
            "audit_authority": self.audit_authority,
            "direct_state_mutation_allowed": self.direct_state_mutation_allowed,
            "direct_event_publication_allowed": self.direct_event_publication_allowed,
        }

    @property
    def contract_sha256(self) -> str:
        payload = json.dumps(
            self.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()


def compile_web_app_interaction_contract(
    spec: WebAppSpec, auth: WebAppAuthContract
) -> WebAppInteractionContract:
    if auth.app_id != spec.app_id or auth.spec_sha256 != spec.spec_sha256:
        raise WebAppInteractionContractError(
            "Phase-4 interaction contract must bind to the exact WebAppSpec/Auth contract"
        )
    if not auth.default_deny or not auth.server_authoritative:
        raise WebAppInteractionContractError("Phase-3 authorization must remain fail closed")
    machines = _canonical_machines(spec)
    _validate_machines(machines, auth, realtime_available=spec.realtime_required)
    return WebAppInteractionContract(
        schema_version="ilaios.web-app-interaction-contract.v1",
        app_id=spec.app_id,
        project_id=auth.project_id,
        spec_sha256=spec.spec_sha256,
        auth_contract_sha256=auth.contract_sha256,
        machines=machines,
        interaction_chain=(
            "ui-event",
            "api-mutation-contract",
            "authorization",
            "policy",
            "admission",
            "approval-when-required",
            "domain-transition",
            "validation",
            "audit",
            "evidence",
            "notification-realtime-projection",
        ),
        policy_authority="canonical-policy-engine",
        approval_authority="canonical-approval-engine",
        tool_authority="canonical-tool-gateway",
        validation_authority="canonical-validation-pipeline",
        audit_authority="canonical-audit-evidence-chain",
        direct_state_mutation_allowed=False,
        direct_event_publication_allowed=False,
    )


def _canonical_machines(spec: WebAppSpec) -> tuple[WebAppStateMachineContract, ...]:
    workflow_projection: ProjectionMode = (
        "realtime" if spec.realtime_required else "notification"
    )
    return (
        WebAppStateMachineContract(
            "Workflow",
            "workflow",
            "Planning",
            (
                WebAppStateDefinition("Planning"),
                WebAppStateDefinition("Executing"),
                WebAppStateDefinition("Validation"),
                WebAppStateDefinition("Delivery"),
                WebAppStateDefinition("Completed", terminal=True),
            ),
            (
                _transition(
                    "workflow-plan-execute",
                    "Planning",
                    "Executing",
                    "workflow.execute",
                    "project.manage",
                    workflow_projection,
                ),
                _transition(
                    "workflow-execute-validate",
                    "Executing",
                    "Validation",
                    "workflow.validate",
                    "project.manage",
                    workflow_projection,
                ),
                _transition(
                    "workflow-validate-deliver",
                    "Validation",
                    "Delivery",
                    "workflow.deliver",
                    "project.manage",
                    workflow_projection,
                ),
                _transition(
                    "workflow-deliver-complete",
                    "Delivery",
                    "Completed",
                    "workflow.complete",
                    "project.manage",
                    workflow_projection,
                ),
            ),
        ),
        WebAppStateMachineContract(
            "Approval",
            "approval",
            "Pending",
            (
                WebAppStateDefinition("Pending"),
                WebAppStateDefinition("Reviewing"),
                WebAppStateDefinition("Approved", terminal=True),
                WebAppStateDefinition("Rejected", terminal=True),
            ),
            (
                _transition(
                    "approval-pending-reviewing",
                    "Pending",
                    "Reviewing",
                    "approval.review",
                    "approval.review",
                    "notification",
                ),
                _transition(
                    "approval-reviewing-approved",
                    "Reviewing",
                    "Approved",
                    "approval.approve",
                    "approval.review",
                    "notification",
                ),
                _transition(
                    "approval-reviewing-rejected",
                    "Reviewing",
                    "Rejected",
                    "approval.reject",
                    "approval.review",
                    "notification",
                ),
            ),
        ),
        WebAppStateMachineContract(
            "Evidence",
            "evidence",
            "Generated",
            (
                WebAppStateDefinition("Generated"),
                WebAppStateDefinition("Reviewed"),
                WebAppStateDefinition("Verified", terminal=True),
                WebAppStateDefinition("Failed", terminal=True),
            ),
            (
                _transition(
                    "evidence-generated-reviewed",
                    "Generated",
                    "Reviewed",
                    "evidence.review",
                    "evidence.review",
                    "notification",
                ),
                _transition(
                    "evidence-reviewed-verified",
                    "Reviewed",
                    "Verified",
                    "evidence.verify",
                    "evidence.review",
                    "notification",
                ),
                _transition(
                    "evidence-reviewed-failed",
                    "Reviewed",
                    "Failed",
                    "evidence.fail",
                    "evidence.review",
                    "notification",
                ),
            ),
        ),
    )


def _transition(
    transition_id: str,
    from_state: str,
    to_state: str,
    action_name: str,
    permission: str,
    projection: ProjectionMode,
) -> WebAppTransitionContract:
    return WebAppTransitionContract(
        transition_id,
        from_state,
        to_state,
        f"ui:{action_name}",
        f"mutation:{action_name}",
        f"action:{permission}",
        permission,
        projection=projection,
    )


def _validate_machines(
    machines: tuple[WebAppStateMachineContract, ...],
    auth: WebAppAuthContract,
    *,
    realtime_available: bool,
) -> None:
    if tuple(machine.machine_id for machine in machines) != (
        "Workflow",
        "Approval",
        "Evidence",
    ):
        raise WebAppInteractionContractError("required lifecycle machines are incomplete")
    auth_actions = {action.action_id: action.permission for action in auth.actions}
    machine_ids: set[str] = set()
    for machine in machines:
        _token(machine.machine_id, "machine_id")
        _token(machine.domain_subject, "domain_subject")
        if machine.machine_id in machine_ids:
            raise WebAppInteractionContractError("machine_id values must be unique")
        machine_ids.add(machine.machine_id)
        state_ids = tuple(state.state_id for state in machine.states)
        if not state_ids or len(state_ids) != len(set(state_ids)):
            raise WebAppInteractionContractError("state ids must be non-empty and unique")
        if machine.initial_state not in state_ids:
            raise WebAppInteractionContractError("initial state must be declared")
        terminal = {state.state_id for state in machine.states if state.terminal}
        transition_ids: set[str] = set()
        outgoing = {state_id: 0 for state_id in state_ids}
        for transition in machine.transitions:
            _token(transition.transition_id, "transition_id")
            if transition.transition_id in transition_ids:
                raise WebAppInteractionContractError(
                    "transition ids must be unique per machine"
                )
            transition_ids.add(transition.transition_id)
            if transition.from_state not in outgoing or transition.to_state not in outgoing:
                raise WebAppInteractionContractError("transition references undeclared state")
            if transition.from_state in terminal:
                raise WebAppInteractionContractError(
                    "terminal state cannot have outgoing transition"
                )
            outgoing[transition.from_state] += 1
            if auth_actions.get(transition.auth_action_id) != transition.permission:
                raise WebAppInteractionContractError(
                    "transition is not bound to Phase-3 authorization"
                )
            if not transition.policy_required or not transition.admission_required:
                raise WebAppInteractionContractError(
                    "transition cannot bypass policy/admission"
                )
            if not transition.audit_required or not transition.evidence_required:
                raise WebAppInteractionContractError(
                    "transition cannot bypass audit/evidence"
                )
            if (
                transition.projection in {"realtime", "realtime+notification"}
                and not realtime_available
            ):
                raise WebAppInteractionContractError(
                    "realtime projection requires declared realtime capability"
                )
        for state in machine.states:
            if not state.terminal and outgoing[state.state_id] == 0:
                raise WebAppInteractionContractError(
                    "non-terminal state requires outgoing transition"
                )


def _token(value: str, field: str) -> None:
    if not value or value != value.strip() or any(character.isspace() for character in value):
        raise WebAppInteractionContractError(f"{field} must be a non-empty token")
    if "*" in value:
        raise WebAppInteractionContractError(f"{field} cannot contain wildcard authority")
