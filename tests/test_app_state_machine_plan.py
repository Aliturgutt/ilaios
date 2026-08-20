from __future__ import annotations

from dataclasses import replace
from typing import Any

import pytest

from services.app_architecture_plan import ApplicationArchitecturePlan
from services.app_auth_rbac_plan import (
    ActorRoleBinding,
    AuthRbacPlan,
    PermissionGrant,
    RoleRequirement,
)
from services.app_product_spec import ProductSpec
from services.app_state_machine_plan import (
    AppStateMachinePlan,
    AppStateMachinePlanError,
    StateDefinition,
    StateMachineRequirement,
    TransitionRequirement,
    build_state_machine_plan,
)


def _spec(*, notifications: bool = True) -> ProductSpec:
    capabilities: tuple[str, ...] = ("authentication", "rbac", "workflows", "realtime")
    if notifications:
        capabilities += ("notifications",)
    return ProductSpec(
        project_id="proj-state",
        product_name="state-product",
        objective="governed state transitions",
        platforms=("android", "ios"),
        actors=("member", "admin"),
        screens=("home", "request-detail"),
        capabilities=capabilities,
        locales=("en",),
        accessibility_required=True,
        offline_required=False,
        monetization="free",
        spec_sha256="spec-sha",
    )


def _architecture(*, realtime: bool = True) -> ApplicationArchitecturePlan:
    return ApplicationArchitecturePlan(
        project_id="proj-state",
        spec_sha256="spec-sha",
        architecture_tier="enterprise",
        persistence_mode="relational",
        realtime_mode="event-stream" if realtime else "none",
        file_mode="none",
        native_mode="mobile-capability-pack",
        requires_backend_api=True,
        requires_authentication=True,
        requires_authorization=True,
        requires_migrations=True,
        requires_external_integrations=False,
        requires_commerce_runtime=False,
        implementation_authority="software-factory",
        direct_publication_allowed=False,
        plan_sha256="architecture-sha",
    )


def _auth() -> AuthRbacPlan:
    member = RoleRequirement(
        role_id="member-role",
        grants=(PermissionGrant("request.submit", "project"),),
    )
    admin = RoleRequirement(
        role_id="admin-role",
        grants=(
            PermissionGrant(
                "request.approve",
                "project",
                privileged=True,
                high_risk=True,
                approval_required=True,
            ),
        ),
    )
    return AuthRbacPlan(
        project_id="proj-state",
        spec_sha256="spec-sha",
        architecture_plan_sha256="architecture-sha",
        data_migration_plan_sha256="data-sha",
        auth_providers=("oidc",),
        roles=(member, admin),
        actor_role_bindings=(
            ActorRoleBinding("member", "member-role"),
            ActorRoleBinding("admin", "admin-role"),
        ),
        authentication_required=True,
        authorization_required=True,
        session_required=True,
        refresh_required=True,
        logout_required=True,
        recovery_required=True,
        privileged_mfa_required=True,
        high_risk_approval_required=True,
        default_deny=True,
        server_authoritative=True,
        ui_visibility_is_authorization=False,
        raw_credentials_allowed_in_plan=False,
        authentication_authority="services.identity.AuthenticationBoundary",
        authorization_authority="services.identity.AuthorizationEngine",
        session_authority="services.identity.SessionRegistry",
        implementation_authority="software-factory",
        direct_permission_mutation_allowed=False,
        plan_sha256="auth-sha",
    )


def _transition(**changes: Any) -> TransitionRequirement:
    base = TransitionRequirement(
        transition_id="submit",
        from_state="draft",
        to_state="pending",
        actor="member",
        trigger="submit-click",
        action="request.submit",
        permission="request.submit",
        projection="realtime",
    )
    return replace(base, **changes)


def _machine(
    *,
    transitions: tuple[TransitionRequirement, ...] | None = None,
) -> StateMachineRequirement:
    if transitions is None:
        transitions = (
            _transition(),
            TransitionRequirement(
                transition_id="approve",
                from_state="pending",
                to_state="approved",
                actor="admin",
                trigger="approve-click",
                action="request.approve",
                permission="request.approve",
                high_risk=True,
                approval_required=True,
                projection="realtime+notification",
            ),
        )
    return StateMachineRequirement(
        machine_id="request-lifecycle",
        domain_subject="request",
        initial_state="draft",
        states=(
            StateDefinition("draft"),
            StateDefinition("pending"),
            StateDefinition("approved", terminal=True),
        ),
        transitions=transitions,
    )


def _build(
    *,
    spec: ProductSpec | None = None,
    architecture: ApplicationArchitecturePlan | None = None,
    auth: AuthRbacPlan | None = None,
    machines: tuple[StateMachineRequirement, ...] | None = None,
) -> AppStateMachinePlan:
    return build_state_machine_plan(
        spec=spec or _spec(),
        architecture=architecture or _architecture(),
        auth_rbac=auth or _auth(),
        machines=machines or (_machine(),),
    )


def test_plan_is_deterministic_and_grants_zero_runtime_authority() -> None:
    first = _build()
    second = _build()

    assert first == second
    assert first.transition_count == 2
    assert first.policy_before_transition is True
    assert first.approval_before_high_risk_transition is True
    assert first.audit_after_transition is True
    assert first.evidence_after_transition is True
    assert first.runtime_authority == "execution-coordinator"
    assert first.implementation_authority == "software-factory"
    assert first.direct_state_mutation_allowed is False
    assert first.direct_event_publication_allowed is False
    assert len(first.plan_sha256) == 64


def test_binding_mismatch_fails_closed() -> None:
    with pytest.raises(AppStateMachinePlanError, match="architecture plan"):
        _build(architecture=replace(_architecture(), spec_sha256="wrong"))

    with pytest.raises(AppStateMachinePlanError, match="auth/RBAC plan"):
        _build(auth=replace(_auth(), architecture_plan_sha256="wrong"))


def test_unknown_state_and_actor_fail_closed() -> None:
    bad_state = replace(
        _machine(),
        transitions=(_transition(from_state="missing", to_state="approved"),),
    )
    with pytest.raises(AppStateMachinePlanError, match="unknown state"):
        _build(machines=(bad_state,))

    bad_actor = replace(
        _machine(),
        transitions=(_transition(actor="ghost", to_state="approved"),),
    )
    with pytest.raises(AppStateMachinePlanError, match="unknown ProductSpec actor"):
        _build(machines=(bad_actor,))


def test_authorized_transition_requires_actor_granted_permission() -> None:
    missing = replace(
        _machine(),
        transitions=(_transition(permission=None, to_state="approved"),),
    )
    with pytest.raises(AppStateMachinePlanError, match="explicit permission"):
        _build(machines=(missing,))

    wrong = replace(
        _machine(),
        transitions=(_transition(permission="request.approve", to_state="approved"),),
    )
    with pytest.raises(AppStateMachinePlanError, match="not granted"):
        _build(machines=(wrong,))


def test_high_risk_transition_requires_approval_and_every_transition_requires_policy() -> None:
    no_approval = replace(
        _machine(),
        states=(StateDefinition("draft"), StateDefinition("approved", terminal=True)),
        transitions=(
            _transition(
                actor="admin",
                action="request.approve",
                permission="request.approve",
                to_state="approved",
                high_risk=True,
                approval_required=False,
            ),
        ),
    )
    with pytest.raises(AppStateMachinePlanError, match="explicit Approval"):
        _build(machines=(no_approval,))

    no_policy = replace(
        _machine(),
        states=(StateDefinition("draft"), StateDefinition("approved", terminal=True)),
        transitions=(
            _transition(to_state="approved", policy_check_required=False),
        ),
    )
    with pytest.raises(AppStateMachinePlanError, match="Policy"):
        _build(machines=(no_policy,))


def test_projection_requires_declared_realtime_and_notification_capability() -> None:
    with pytest.raises(AppStateMachinePlanError, match="event-stream"):
        _build(architecture=_architecture(realtime=False))

    with pytest.raises(AppStateMachinePlanError, match="notifications ProductSpec capability"):
        _build(spec=_spec(notifications=False))


def test_terminal_outgoing_and_nonterminal_dead_end_fail_closed() -> None:
    terminal_outgoing = StateMachineRequirement(
        machine_id="terminal-outgoing",
        domain_subject="request",
        initial_state="approved",
        states=(
            StateDefinition("approved", terminal=True),
            StateDefinition("done", terminal=True),
        ),
        transitions=(
            TransitionRequirement(
                "reopen",
                "approved",
                "done",
                "admin",
                "reopen-click",
                "request.approve",
                permission="request.approve",
            ),
        ),
    )
    with pytest.raises(AppStateMachinePlanError, match="terminal state"):
        _build(machines=(terminal_outgoing,))

    dead_end = StateMachineRequirement(
        machine_id="dead-end",
        domain_subject="request",
        initial_state="draft",
        states=(
            StateDefinition("draft"),
            StateDefinition("pending"),
            StateDefinition("done", terminal=True),
        ),
        transitions=(_transition(to_state="done", projection="none"),),
    )
    with pytest.raises(AppStateMachinePlanError, match="non-terminal state pending"):
        _build(machines=(dead_end,))


def test_duplicate_machine_state_and_transition_ids_fail_closed() -> None:
    with pytest.raises(AppStateMachinePlanError, match="machine_id values must be unique"):
        _build(machines=(_machine(), _machine()))

    duplicate_states = replace(
        _machine(),
        states=(StateDefinition("draft"), StateDefinition("draft")),
        transitions=(_transition(to_state="draft", projection="none"),),
    )
    with pytest.raises(AppStateMachinePlanError, match="states values must be unique"):
        _build(machines=(duplicate_states,))

    duplicate_transitions = replace(
        _machine(),
        states=(StateDefinition("draft"), StateDefinition("pending", terminal=True)),
        transitions=(
            _transition(projection="none"),
            _transition(trigger="submit-again", projection="none"),
        ),
    )
    with pytest.raises(AppStateMachinePlanError, match="transition_id values must be unique"):
        _build(machines=(duplicate_transitions,))
