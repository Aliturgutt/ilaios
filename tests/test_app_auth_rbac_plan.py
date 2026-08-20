from __future__ import annotations

import pytest

from services.app_architecture_plan import (
    ApplicationArchitecturePlan,
    plan_application_architecture,
)
from services.app_auth_rbac_plan import (
    ActorRoleBinding,
    AppAuthRbacPlanError,
    PermissionGrant,
    RoleRequirement,
    build_auth_rbac_plan,
)
from services.app_data_migration_plan import DataMigrationPlan, build_data_migration_plan
from services.app_domain_model import DomainModelPlan, build_domain_model
from services.app_product_spec import (
    ProductSpec,
    admit_project,
    build_product_spec,
    classify_risk,
    resolve_capabilities,
)


def _spec(
    capabilities: tuple[str, ...] = ("authentication", "rbac", "project-access"),
) -> ProductSpec:
    admission = admit_project(
        project_id="project-auth-rbac-test",
        intent="new",
        objective="Build a tenant-scoped governed application",
        platforms=("android", "ios"),
    )
    return build_product_spec(
        admission=admission,
        product_name="Auth RBAC Test",
        actors=("owner", "member"),
        screens=("projects", "settings"),
        capabilities=capabilities,
    )


def _architecture(spec: ProductSpec) -> ApplicationArchitecturePlan:
    return plan_application_architecture(
        spec=spec,
        capability_assessments=resolve_capabilities(spec),
        risk=classify_risk(spec),
    )


def _domain_model(
    spec: ProductSpec, architecture: ApplicationArchitecturePlan
) -> DomainModelPlan:
    return build_domain_model(spec=spec, architecture=architecture, entities=())


def _data_migration(
    spec: ProductSpec, architecture: ApplicationArchitecturePlan
) -> DataMigrationPlan:
    return build_data_migration_plan(
        spec=spec,
        architecture=architecture,
        domain_model=_domain_model(spec, architecture),
        tables=(),
        steps=(),
    )


def _roles() -> tuple[RoleRequirement, ...]:
    return (
        RoleRequirement(
            role_id="owner",
            grants=(
                PermissionGrant("project.read", "project"),
                PermissionGrant("project.manage", "project", privileged=True),
                PermissionGrant(
                    "project.delete",
                    "project",
                    privileged=True,
                    high_risk=True,
                    approval_required=True,
                ),
            ),
        ),
        RoleRequirement(
            role_id="member",
            grants=(
                PermissionGrant("project.read", "project"),
                PermissionGrant("task.update", "resource", resource="task"),
            ),
        ),
    )


def _bindings() -> tuple[ActorRoleBinding, ...]:
    return (
        ActorRoleBinding("owner", "owner"),
        ActorRoleBinding("member", "member"),
    )


def test_auth_rbac_plan_reuses_canonical_identity_authorities() -> None:
    spec = _spec()
    architecture = _architecture(spec)
    plan = build_auth_rbac_plan(
        spec=spec,
        architecture=architecture,
        data_migration=_data_migration(spec, architecture),
        auth_providers=("oidc", "google", "apple"),
        roles=_roles(),
        actor_role_bindings=_bindings(),
    )

    assert plan.authentication_required is True
    assert plan.authorization_required is True
    assert plan.default_deny is True
    assert plan.server_authoritative is True
    assert plan.ui_visibility_is_authorization is False
    assert plan.raw_credentials_allowed_in_plan is False
    assert plan.privileged_mfa_required is True
    assert plan.high_risk_approval_required is True
    assert plan.authentication_authority == "services.identity.AuthenticationBoundary"
    assert plan.authorization_authority == "services.identity.AuthorizationEngine"
    assert plan.session_authority == "services.identity.SessionRegistry"
    assert plan.implementation_authority == "software-factory"
    assert plan.direct_permission_mutation_allowed is False
    assert len(plan.plan_sha256) == 64


def test_auth_rbac_plan_is_deterministic_for_identical_inputs() -> None:
    spec = _spec()
    architecture = _architecture(spec)
    data_migration = _data_migration(spec, architecture)

    first = build_auth_rbac_plan(
        spec=spec,
        architecture=architecture,
        data_migration=data_migration,
        auth_providers=("oidc",),
        roles=_roles(),
        actor_role_bindings=_bindings(),
    )
    second = build_auth_rbac_plan(
        spec=spec,
        architecture=architecture,
        data_migration=data_migration,
        auth_providers=("oidc",),
        roles=_roles(),
        actor_role_bindings=_bindings(),
    )

    assert first == second
    assert first.plan_sha256 == second.plan_sha256


def test_authorization_without_authentication_fails_closed() -> None:
    spec = _spec(("rbac", "project-access"))
    architecture = _architecture(spec)

    with pytest.raises(AppAuthRbacPlanError, match="requires authenticated"):
        build_auth_rbac_plan(
            spec=spec,
            architecture=architecture,
            data_migration=_data_migration(spec, architecture),
            auth_providers=(),
            roles=_roles(),
            actor_role_bindings=_bindings(),
        )


def test_authentication_requires_explicit_provider_contract() -> None:
    spec = _spec()
    architecture = _architecture(spec)

    with pytest.raises(AppAuthRbacPlanError, match="at least one auth provider"):
        build_auth_rbac_plan(
            spec=spec,
            architecture=architecture,
            data_migration=_data_migration(spec, architecture),
            auth_providers=(),
            roles=_roles(),
            actor_role_bindings=_bindings(),
        )


def test_every_product_actor_requires_a_role_binding() -> None:
    spec = _spec()
    architecture = _architecture(spec)

    with pytest.raises(AppAuthRbacPlanError, match="every ProductSpec actor"):
        build_auth_rbac_plan(
            spec=spec,
            architecture=architecture,
            data_migration=_data_migration(spec, architecture),
            auth_providers=("oidc",),
            roles=_roles(),
            actor_role_bindings=(ActorRoleBinding("owner", "owner"),),
        )


def test_actor_binding_cannot_reference_unknown_role() -> None:
    spec = _spec()
    architecture = _architecture(spec)

    with pytest.raises(AppAuthRbacPlanError, match="unknown role"):
        build_auth_rbac_plan(
            spec=spec,
            architecture=architecture,
            data_migration=_data_migration(spec, architecture),
            auth_providers=("oidc",),
            roles=_roles(),
            actor_role_bindings=(
                ActorRoleBinding("owner", "administrator"),
                ActorRoleBinding("member", "member"),
            ),
        )


def test_high_risk_permission_requires_approval_contract() -> None:
    spec = _spec()
    architecture = _architecture(spec)
    unsafe_roles = (
        RoleRequirement(
            role_id="owner",
            grants=(
                PermissionGrant(
                    "project.delete",
                    "project",
                    high_risk=True,
                    approval_required=False,
                ),
            ),
        ),
        _roles()[1],
    )

    with pytest.raises(AppAuthRbacPlanError, match="requires explicit approval"):
        build_auth_rbac_plan(
            spec=spec,
            architecture=architecture,
            data_migration=_data_migration(spec, architecture),
            auth_providers=("oidc",),
            roles=unsafe_roles,
            actor_role_bindings=_bindings(),
        )


def test_permission_scope_cannot_use_wildcard_authority() -> None:
    spec = _spec()
    architecture = _architecture(spec)
    unsafe_roles = (
        RoleRequirement(
            role_id="owner",
            grants=(PermissionGrant("project.*", "project"),),
        ),
        _roles()[1],
    )

    with pytest.raises(AppAuthRbacPlanError, match="wildcard authority"):
        build_auth_rbac_plan(
            spec=spec,
            architecture=architecture,
            data_migration=_data_migration(spec, architecture),
            auth_providers=("oidc",),
            roles=unsafe_roles,
            actor_role_bindings=_bindings(),
        )
