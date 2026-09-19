"""Deterministic Stage-2 enterprise application state-machine contracts.

This module is specification/planning only. It cannot mutate application/domain state,
execute API actions, bypass policy or approval, emit runtime events, write evidence,
deploy, sign, submit, publish, or create a second workflow/runtime authority. Real
execution remains downstream through the canonical ExecutionCoordinator, Software
Factory, Policy/Approval/Tool Gateway, validation, audit and evidence boundaries.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Literal

from services.app_architecture_plan import ApplicationArchitecturePlan
from services.app_auth_rbac_plan import AuthRbacPlan
from services.app_product_spec import ProductSpec


ProjectionMode = Literal["none", "realtime", "notification", "realtime+notification"]


class AppStateMachinePlanError(ValueError):
    """State-machine planning input is invalid, ambiguous, or unsafe."""


@dataclass(frozen=True, slots=True)
class StateDefinition:
    state_id: str
    terminal: bool = False


@dataclass(frozen=True, slots=True)
class TransitionRequirement:
    transition_id: str
    from_state: str
    to_state: str
    actor: str
    trigger: str
    action: str
    permission: str | None = None
    high_risk: bool = False
    approval_required: bool = False
    policy_check_required: bool = True
    projection: ProjectionMode = "none"


@dataclass(frozen=True, slots=True)
class StateMachineRequirement:
    machine_id: str
    domain_subject: str
    initial_state: str
    states: tuple[StateDefinition, ...]
    transitions: tuple[TransitionRequirement, ...]


@dataclass(frozen=True, slots=True)
class AppStateMachinePlan:
    project_id: str
    spec_sha256: str
    architecture_plan_sha256: str
    auth_rbac_plan_sha256: str
    machines: tuple[StateMachineRequirement, ...]
    transition_count: int
    policy_before_transition: Literal[True]
    approval_before_high_risk_transition: Literal[True]
    audit_after_transition: Literal[True]
    evidence_after_transition: Literal[True]
    runtime_authority: Literal["execution-coordinator"]
    implementation_authority: Literal["software-factory"]
    direct_state_mutation_allowed: Literal[False]
    direct_event_publication_allowed: Literal[False]
    plan_sha256: str


def build_state_machine_plan(
    *,
    spec: ProductSpec,
    architecture: ApplicationArchitecturePlan,
    auth_rbac: AuthRbacPlan,
    machines: tuple[StateMachineRequirement, ...],
) -> AppStateMachinePlan:
    """Validate deterministic product state machines without granting runtime authority."""
    if architecture.project_id != spec.project_id or architecture.spec_sha256 != spec.spec_sha256:
        raise AppStateMachinePlanError("architecture plan must be bound to the supplied ProductSpec")
    if (
        auth_rbac.project_id != spec.project_id
        or auth_rbac.spec_sha256 != spec.spec_sha256
        or auth_rbac.architecture_plan_sha256 != architecture.plan_sha256
    ):
        raise AppStateMachinePlanError(
            "auth/RBAC plan must be bound to the supplied ProductSpec and architecture"
        )
    if not machines:
        raise AppStateMachinePlanError("at least one product state machine is required")

    _require_unique(tuple(machine.machine_id for machine in machines), "machine_id")
    known_actors = frozenset(spec.actors)
    actor_permissions = _actor_permissions(auth_rbac)
    total_transitions = 0

    for machine in machines:
        _token(machine.machine_id, "machine_id")
        _token(machine.domain_subject, "domain_subject")
        if not machine.states:
            raise AppStateMachinePlanError(f"state machine {machine.machine_id} requires states")
        if not machine.transitions:
            raise AppStateMachinePlanError(
                f"state machine {machine.machine_id} requires at least one transition"
            )

        state_ids = tuple(state.state_id for state in machine.states)
        _require_unique(state_ids, f"{machine.machine_id}.states")
        state_set = frozenset(state_ids)
        for state in machine.states:
            _token(state.state_id, "state_id")
        if machine.initial_state not in state_set:
            raise AppStateMachinePlanError(
                f"state machine {machine.machine_id} initial state is not declared"
            )

        _require_unique(
            tuple(item.transition_id for item in machine.transitions),
            f"{machine.machine_id}.transition_id",
        )
        outgoing: dict[str, int] = {state_id: 0 for state_id in state_ids}
        terminal_states = frozenset(state.state_id for state in machine.states if state.terminal)
        for transition in machine.transitions:
            _validate_transition(
                transition=transition,
                machine_id=machine.machine_id,
                known_states=state_set,
                known_actors=known_actors,
                actor_permissions=actor_permissions,
                authorization_required=auth_rbac.authorization_required,
                realtime_available=architecture.realtime_mode == "event-stream",
                notifications_available="notifications" in spec.capabilities,
            )
            outgoing[transition.from_state] += 1
            if transition.from_state in terminal_states:
                raise AppStateMachinePlanError(
                    f"terminal state {transition.from_state} cannot have outgoing transitions"
                )
            total_transitions += 1

        for state in machine.states:
            if not state.terminal and outgoing[state.state_id] == 0:
                raise AppStateMachinePlanError(
                    f"non-terminal state {state.state_id} requires an outgoing transition"
                )

    canonical: dict[str, object] = {
        "approval_before_high_risk_transition": True,
        "architecture_plan_sha256": architecture.plan_sha256,
        "audit_after_transition": True,
        "auth_rbac_plan_sha256": auth_rbac.plan_sha256,
        "direct_event_publication_allowed": False,
        "direct_state_mutation_allowed": False,
        "evidence_after_transition": True,
        "implementation_authority": "software-factory",
        "machines": [_machine_payload(machine) for machine in machines],
        "policy_before_transition": True,
        "project_id": spec.project_id,
        "runtime_authority": "execution-coordinator",
        "spec_sha256": spec.spec_sha256,
        "transition_count": total_transitions,
    }
    return AppStateMachinePlan(
        project_id=spec.project_id,
        spec_sha256=spec.spec_sha256,
        architecture_plan_sha256=architecture.plan_sha256,
        auth_rbac_plan_sha256=auth_rbac.plan_sha256,
        machines=machines,
        transition_count=total_transitions,
        policy_before_transition=True,
        approval_before_high_risk_transition=True,
        audit_after_transition=True,
        evidence_after_transition=True,
        runtime_authority="execution-coordinator",
        implementation_authority="software-factory",
        direct_state_mutation_allowed=False,
        direct_event_publication_allowed=False,
        plan_sha256=_sha256_json(canonical),
    )


def _actor_permissions(auth_rbac: AuthRbacPlan) -> dict[str, frozenset[str]]:
    role_permissions = {
        role.role_id: frozenset(grant.permission for grant in role.grants) for role in auth_rbac.roles
    }
    result: dict[str, set[str]] = {}
    for binding in auth_rbac.actor_role_bindings:
        result.setdefault(binding.actor, set()).update(role_permissions[binding.role_id])
    return {actor: frozenset(permissions) for actor, permissions in result.items()}


def _validate_transition(
    *,
    transition: TransitionRequirement,
    machine_id: str,
    known_states: frozenset[str],
    known_actors: frozenset[str],
    actor_permissions: dict[str, frozenset[str]],
    authorization_required: bool,
    realtime_available: bool,
    notifications_available: bool,
) -> None:
    _token(transition.transition_id, "transition_id")
    _token(transition.trigger, "trigger")
    _token(transition.action, "action")
    _token(transition.actor, "actor")
    if transition.from_state not in known_states or transition.to_state not in known_states:
        raise AppStateMachinePlanError(
            f"state machine {machine_id} transition references an unknown state"
        )
    if transition.actor not in known_actors:
        raise AppStateMachinePlanError(
            f"state machine {machine_id} transition references an unknown ProductSpec actor"
        )
    if not transition.policy_check_required:
        raise AppStateMachinePlanError("every state transition requires Policy evaluation")
    if transition.high_risk and not transition.approval_required:
        raise AppStateMachinePlanError("high-risk state transition requires explicit Approval")

    if authorization_required:
        if transition.permission is None:
            raise AppStateMachinePlanError(
                "authorized product state transitions require an explicit permission"
            )
        _token(transition.permission, "permission")
        if transition.permission not in actor_permissions.get(transition.actor, frozenset()):
            raise AppStateMachinePlanError(
                "state transition permission is not granted to the bound ProductSpec actor"
            )
    elif transition.permission is not None:
        raise AppStateMachinePlanError(
            "non-authorized product state transitions cannot invent permission requirements"
        )

    if transition.projection in {"realtime", "realtime+notification"} and not realtime_available:
        raise AppStateMachinePlanError("realtime projection requires event-stream architecture")
    if transition.projection in {"notification", "realtime+notification"} and not notifications_available:
        raise AppStateMachinePlanError(
            "notification projection requires the notifications ProductSpec capability"
        )


def _machine_payload(machine: StateMachineRequirement) -> dict[str, object]:
    return {
        "domain_subject": machine.domain_subject,
        "initial_state": machine.initial_state,
        "machine_id": machine.machine_id,
        "states": [
            {"state_id": state.state_id, "terminal": state.terminal} for state in machine.states
        ],
        "transitions": [
            {
                "action": item.action,
                "actor": item.actor,
                "approval_required": item.approval_required,
                "from_state": item.from_state,
                "high_risk": item.high_risk,
                "permission": item.permission,
                "policy_check_required": item.policy_check_required,
                "projection": item.projection,
                "to_state": item.to_state,
                "transition_id": item.transition_id,
                "trigger": item.trigger,
            }
            for item in machine.transitions
        ],
    }


def _require_unique(values: tuple[str, ...], field: str) -> None:
    for value in values:
        _token(value, field)
    if len(values) != len(set(values)):
        raise AppStateMachinePlanError(f"{field} values must be unique")


def _token(value: str, field: str) -> None:
    if not value or value != value.strip() or any(ch.isspace() for ch in value):
        raise AppStateMachinePlanError(f"{field} must be a non-empty token")
    if "*" in value:
        raise AppStateMachinePlanError(f"{field} cannot contain wildcard authority")


def _sha256_json(payload: dict[str, object]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
