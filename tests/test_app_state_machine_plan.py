from __future__ import annotations

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
    AppStateMachinePlanError,
    StateDefinition,
    StateMachineRequirement,
    TransitionRequirement,
    build_state_machine_plan,
)


def _spec(*, notifications: bool = True) -> ProductSpec:
    capabilities = ("authentication", "rbac", "workflows", "realtime")
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


def _machine() -> StateMachineRequirement:
    return StateMachineRequirement(
        machine_id="request-lifecycle",
        domain_subject="request",
        initial_state="draft",
        states=(
            StateDefinition("draft"),
            StateDefinition("pending"),
            StateDefinition("approved", terminal=True),
        ),
        transitions=(
            TransitionRequirement(
                transition_id="submit",
                from_state="draft",
                to_state="pending",
                actor="member",
                trigger="submit-click",
                action="request.submit",
                permission="request.submit",
                projection="realtime",
            ),
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
        ),
    )


def test_build_state_machine_plan_is_deterministic_and_zero_authority() -> None:
    first = build_state_machine_plan(
        spec=_spec(), architecture=_architecture(), auth_rbac=_auth(), machines=(_machine(),)
    )
    second = build_state_machine_plan(
        spec=_spec(), architecture=_architecture(), auth_rbac=_auth(), machines=(_machine(),)
    )

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


def test_rejects_tampered_architecture_binding() -> None:
    architecture = _architecture()
    architecture = ApplicationArchitecturePlan(
        **{**architecture.__dict__, "spec_sha256": "wrong"}  # type: ignore[attr-defined]
    )
    with pytest.raises(AppStateMachinePlanError, match="architecture plan"):
        build_state_machine_plan(
            spec=_spec(), architecture=architecture, auth_rbac=_auth(), machines=(_machine(),)
        )


def test_rejects_tampered_auth_binding() -> None:
    auth = _auth()
    auth = AuthRbacPlan(
        project_id=auth.project_id,
        spec_sha256=auth.spec_sha256,
        architecture_plan_sha256="wrong",
        data_migration_plan_sha256=auth.data_migration_plan_sha256,
        auth_providers=auth.auth_providers,
        roles=auth.roles,
        actor_role_bindings=auth.actor_role_bindings,
        authentication_required=auth.authentication_required,
        authorization_required=auth.authorization_required,
        session_required=auth.session_required,
        refresh_required=auth.refresh_required,
        logout_required=auth.logout_required,
        recovery_required=auth.recovery_required,
        privileged_mfa_required=auth.privileged_mfa_required,
        high_risk_approval_required=auth.high_risk_approval_required,
        default_deny=True,
        server_authoritative=True,
        ui_visibility_is_authorization=False,
        raw_credentials_allowed_in_plan=False,
        authentication_authority="services.identity.AuthenticationBoundary",
        authorization_authority="services.identity.AuthorizationEngine",
        session_authority="services.identity.SessionRegistry",
        implementation_authority="software-factory",
        direct_permission_mutation_allowed=False,
        plan_sha256=auth.plan_sha256,
    )
    with pytest.raises(AppStateMachinePlanError, match="auth/RBAC plan"):
        build_state_machine_plan(
            spec=_spec(), architecture=_architecture(), auth_rbac=auth, machines=(_machine(),)
        )


def test_rejects_unknown_state_and_actor() -> None:
    bad_state = StateMachineRequirement(
        machine_id="request-lifecycle",
        domain_subject="request",
        initial_state="draft",
        states=(StateDefinition("draft"), StateDefinition("pending", terminal=True)),
        transitions=(
            TransitionRequirement(
                "submit",
                "missing",
                "pending",
                "member",
                "submit-click",
                "request.submit",
                permission="request.submit",
            ),
        ),
    )
    with pytest.raises(AppStateMachinePlanError, match="unknown state"):
        build_state_machine_plan(
            spec=_spec(), architecture=_architecture(), auth_rbac=_auth(), machines=(bad_state,)
        )

    bad_actor = StateMachineRequirement(
        machine_id="request-lifecycle",
        domain_subject="request",
        initial_state="draft",
        states=(StateDefinition("draft"), StateDefinition("pending", terminal=True)),
        transitions=(
            TransitionRequirement(
                "submit",
                "draft",
                "pending",
                "ghost",
                "submit-click",
                "request.submit",
                permission="request.submit",
            ),
        ),
    )
    with pytest.raises(AppStateMachinePlanError, match="unknown ProductSpec actor"):
        build_state_machine_plan(
            spec=_spec(), architecture=_architecture(), auth_rbac=_auth(), machines=(bad_actor,)
        )


def test_authorized_transitions_require_granted_permission() -> None:
    missing_permission = StateMachineRequirement(
        machine_id="request-lifecycle",
        domain_subject="request",
        initial_state="draft",
        states=(StateDefinition("draft"), StateDefinition("pending", terminal=True)),
        transitions=(
            TransitionRequirement(
                "submit", "draft", "pending", "member", "submit-click", "request.submit"
            ),
        ),
    )
    with pytest.raises(AppStateMachinePlanError, match="explicit permission"):
        build_state_machine_plan(
            spec=_spec(),
            architecture=_architecture(),
            auth_rbac=_auth(),
            machines=(missing_permission,),
        )

    wrong_permission = StateMachineRequirement(
        machine_id="request-lifecycle",
        domain_subject="request",
        initial_state="draft",
        states=(StateDefinition("draft"), StateDefinition("pending", terminal=True)),
        transitions=(
            TransitionRequirement(
                "submit",
                "draft",
                "pending",
                "member",
                "submit-click",
                "request.submit",
                permission="request.approve",
            ),
        ),
    )
    with pytest.raises(AppStateMachinePlanError, match="not granted"):
        build_state_machine_plan(
            spec=_spec(),
            architecture=_architecture(),
            auth_rbac=_auth(),
            machines=(wrong_permission,),
        )


def test_high_risk_transition_requires_approval_and_policy() -> None:
    no_approval = StateMachineRequirement(
        machine_id="request-lifecycle",
        domain_subject="request",
        initial_state="pending",
        states=(StateDefinition("pending"), StateDefinition("approved", terminal=True)),
        transitions=(
            TransitionRequirement(
                "approve",
                "pending",
                "approved",
                "admin",
                "approve-click",
                "request.approve",
                permission="request.approve",
                high_risk=True,
            ),
        ),
    )
    with pytest.raises(AppStateMachinePlanError, match="explicit Approval"):
        build_state_machine_plan(
            spec=_spec(), architecture=_architecture(), auth_rbac=_auth(), machines=(no_approval,)
        )

    no_policy = StateMachineRequirement(
        machine_id="request-lifecycle",
        domain_subject="request",
        initial_state="draft",
        states=(StateDefinition("draft"), StateDefinition("pending", terminal=True)),
        transitions=(
            TransitionRequirement(
                "submit",
                "draft",
                "pending",
                "member",
                "submit-click",
                "request.submit",
                permission="request.submit",
                policy_check_required=False,
            ),
        ),
    )
    with pytest.raises(AppStateMachinePlanError, match="Policy"):
        build_state_machine_plan(
            spec=_spec(), architecture=_architecture(), auth_rbac=_auth(), machines=(no_policy,)
        )


def test_projection_requires_declared_architecture_and_capability() -> None:
    with pytest.raises(AppStateMachinePlanError, match="event-stream"):
        build_state_machine_plan(
            spec=_spec(), architecture=_architecture(realtime=False), auth_rbac=_auth(), machines=(_machine(),)
        )

    with pytest.raises(AppStateMachinePlanError, match="notifications ProductSpec capability"):
        build_state_machine_plan(
            spec=_spec(notifications=False),
            architecture=_architecture(),
            auth_rbac=_auth(),
            machines=(_machine(),),
        )


def test_terminal_and_nonterminal_dead_end_rules_fail_closed() -> None:
    terminal_outgoing = StateMachineRequirement(
        machine_id="request-lifecycle",
        domain_subject="request",
        initial_state="approved",
        states=(StateDefinition("approved", terminal=True), StateDefinition("pending", terminal=True)),
        transitions=(
            TransitionRequirement(
                "reopen",
                "approved",
                "pending",
                "admin",
                "reopen-click",
                "request.approve",
                permission="request.approve",
            ),
        ),
    )
    with pytest.raises(AppStateMachinePlanError, match="terminal state"):
        build_state_machine_plan(
            spec=_spec(),
            architecture=_architecture(),
            auth_rbac=_auth(),
            machines=(terminal_outgoing,),
        )

    dead_end = StateMachineRequirement(
        machine_id="request-lifecycle",
        domain_subject="request",
        initial_state="draft",
        states=(StateDefinition("draft"), StateDefinition("pending"), StateDefinition("done", terminal=True)),
        transitions=(
            TransitionRequirement(
                "submit",
                "draft",
                "done",
                "member",
                "submit-click",
                "request.submit",
                permission="request.submit",
            ),
        ),
    )
    with pytest.raises(AppStateMachinePlanError, match="non-terminal state pending"):
        build_state_machine_plan(
            spec=_spec(), architecture=_architecture(), auth_rbac=_auth(), machines=(dead_end,)
        )


def test_duplicate_machine_state_and_transition_ids_are_rejected() -> None:
    with pytest.raises(AppStateMachinePlanError, match="machine_id values must be unique"):
        build_state_machine_plan(
            spec=_spec(),
            architecture=_architecture(),
            auth_rbac=_auth(),
            machines=(_machine(), _machine()),
        )

    duplicate_states = StateMachineRequirement(
        machine_id="dup-states",
        domain_subject="request",
        initial_state="draft",
        states=(StateDefinition("draft"), StateDefinition("draft")),
        transitions=(
            TransitionRequirement(
                "submit",
                "draft",
                "draft",
                "member",
                "submit-click",
                "request.submit",
                permission="request.submit",
            ),
        ),
    )
    with pytest.raises(AppStateMachinePlanError, match="states values must be unique"):
        build_state_machine_plan(
            spec=_spec(),
            architecture=_architecture(),
            auth_rbac=_auth(),
            machines=(duplicate_states,),
        )

    duplicate_transitions = StateMachineRequirement(
        machine_id="dup-transitions",
        domain_subject="request",
        initial_state="draft",
        states=(StateDefinition("draft"), StateDefinition("pending", terminal=True)),
        transitions=(
            TransitionRequirement(
                "submit",
                "draft",
                "pending",
                "member",
                "submit-click",
                "request.submit",
                permission="request.submit",
            ),
            TransitionRequirement(
                "submit",
                "draft",
                "pending",
                "member",
                "submit-again",
                "request.submit",
                permission="request.submit",
            ),
        ),
    )
    with pytest.raises(AppStateMachinePlanError, match="transition_id values must be unique"):
        build_state_machine_plan(
            spec=_spec(),
            architecture=_architecture(),
            auth_rbac=_auth(),
            machines=(duplicate_transitions,),
        )
