from __future__ import annotations

from dataclasses import replace

import pytest

from services.web_app_auth_contract import (
    WebAppActionPermissionContract,
    WebAppAuthContract,
    compile_web_app_auth_contract,
)
from services.web_app_interaction_contract import (
    WebAppInteractionContract,
    WebAppInteractionContractError,
    compile_web_app_interaction_contract,
)
from services.web_app_spec import WebAppResourceSpec, WebAppSpec


def _spec(*, realtime: bool = True) -> WebAppSpec:
    return WebAppSpec(
        app_id="webapp-phase4",
        app_kind="dashboard",
        objective_sha256="objective-sha",
        locales=("en",),
        auth_required=True,
        resources=(WebAppResourceSpec("projects", ("create", "read", "update", "delete")),),
        tables_required=True,
        charts_required=True,
        external_api_required=False,
        realtime_required=realtime,
        booking_required=False,
        commerce_required=False,
        cms_required=False,
        reference_semantic_sha256=None,
        reference_design_constraints=(),
        acceptance_requirements=("phase4-contract",),
    )


def _compile(
    *, realtime: bool = True
) -> tuple[WebAppSpec, WebAppAuthContract, WebAppInteractionContract]:
    spec = _spec(realtime=realtime)
    auth = compile_web_app_auth_contract(spec, project_id="project-phase4")
    return spec, auth, compile_web_app_interaction_contract(spec, auth)


def test_contract_is_deterministic_and_has_zero_runtime_authority() -> None:
    spec, auth, first = _compile()
    second = compile_web_app_interaction_contract(spec, auth)
    assert first == second
    assert first.contract_sha256 == second.contract_sha256
    assert len(first.contract_sha256) == 64
    assert first.auth_contract_sha256 == auth.contract_sha256
    assert first.direct_state_mutation_allowed is False
    assert first.direct_event_publication_allowed is False
    assert first.interaction_chain == (
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
    )


def test_required_workflow_approval_evidence_state_machines_are_exact() -> None:
    _, _, contract = _compile()
    machines = {machine.machine_id: machine for machine in contract.machines}
    assert tuple(machines) == ("Workflow", "Approval", "Evidence")
    assert tuple(state.state_id for state in machines["Workflow"].states) == (
        "Planning",
        "Executing",
        "Validation",
        "Delivery",
        "Completed",
    )
    assert tuple(state.state_id for state in machines["Approval"].states) == (
        "Pending",
        "Reviewing",
        "Approved",
        "Rejected",
    )
    assert tuple(state.state_id for state in machines["Evidence"].states) == (
        "Generated",
        "Reviewed",
        "Verified",
        "Failed",
    )
    assert machines["Workflow"].states[-1].terminal is True
    assert machines["Approval"].states[-1].terminal is True
    assert machines["Evidence"].states[-1].terminal is True


def test_every_transition_binds_ui_mutation_auth_policy_admission_audit_and_evidence() -> None:
    _, auth, contract = _compile()
    actions = {item.action_id: item.permission for item in auth.actions}
    for machine in contract.machines:
        for transition in machine.transitions:
            assert transition.ui_event.startswith("ui:")
            assert transition.api_mutation_id.startswith("mutation:")
            assert actions[transition.auth_action_id] == transition.permission
            assert transition.policy_required is True
            assert transition.admission_required is True
            assert transition.audit_required is True
            assert transition.evidence_required is True


def test_non_realtime_spec_uses_notification_projection_only() -> None:
    _, _, contract = _compile(realtime=False)
    workflow = next(
        machine for machine in contract.machines if machine.machine_id == "Workflow"
    )
    assert {transition.projection for transition in workflow.transitions} == {"notification"}


def test_spec_or_auth_binding_mismatch_fails_closed() -> None:
    spec = _spec()
    auth = compile_web_app_auth_contract(spec, project_id="project-phase4")
    with pytest.raises(WebAppInteractionContractError, match="exact WebAppSpec/Auth"):
        compile_web_app_interaction_contract(replace(spec, app_id="other-app"), auth)
    unsafe_auth = replace(auth, default_deny=False)  # type: ignore[arg-type]
    with pytest.raises(WebAppInteractionContractError, match="fail closed"):
        compile_web_app_interaction_contract(spec, unsafe_auth)


def test_missing_phase3_action_binding_fails_closed() -> None:
    spec = _spec()
    auth = compile_web_app_auth_contract(spec, project_id="project-phase4")
    actions = tuple(
        item for item in auth.actions if item.action_id != "action:project.manage"
    )
    assert all(isinstance(item, WebAppActionPermissionContract) for item in actions)
    tampered = replace(auth, actions=actions)
    with pytest.raises(WebAppInteractionContractError, match="Phase-3 authorization"):
        compile_web_app_interaction_contract(spec, tampered)
