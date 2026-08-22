from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

import pytest

from services.app_auth_rbac_plan import AuthRbacPlan, PermissionGrant, RoleRequirement
from services.app_domain_model import DomainEntity, DomainField, DomainModelPlan
from services.app_enterprise_runtime import (
    AppEnterpriseRuntime,
    AppEnterpriseRuntimeError,
    bind_enterprise_runtime,
)
from services.app_product_spec import ProductSpec
from services.identity import AuthorizationEngine, IdentityKind, Principal
from services.web_app_auth_contract import (
    WebAppActionPermissionContract,
    WebAppAuthContract,
    WebAppPermissionRequirement,
    WebAppRolePermissionContract,
    compile_authorization_rules,
)
from services.web_app_crud_runtime import WebAppCrudRuntime, WebAppCrudRuntimeError
from src.core.audit_engine import AuditEngine

NOW = datetime(2026, 8, 22, 15, 0, tzinfo=timezone.utc)
SPEC_SHA = "a" * 64
ARCH_SHA = "b" * 64
DOMAIN_SHA = "c" * 64
AUTH_SHA = "d" * 64


def _spec() -> ProductSpec:
    return ProductSpec(
        project_id="project-1",
        product_name="EnterpriseApp",
        objective="Run one governed cross-platform application backend",
        platforms=("android", "ios"),
        actors=("operator",),
        screens=("goals",),
        capabilities=("authentication", "rbac", "crud"),
        locales=("en",),
        accessibility_required=True,
        offline_required=False,
        monetization="free",
        spec_sha256=SPEC_SHA,
    )


def _domain() -> DomainModelPlan:
    entity = DomainEntity(
        entity_id="Goal",
        tenant_owned=True,
        fields=(
            DomainField("id", "uuid", unique=True),
            DomainField("tenant_id", "uuid", indexed=True),
            DomainField("created_at", "datetime"),
            DomainField("updated_at", "datetime"),
            DomainField("title", "string"),
        ),
    )
    return DomainModelPlan(
        project_id="project-1",
        spec_sha256=SPEC_SHA,
        architecture_plan_sha256=ARCH_SHA,
        entities=(entity,),
        tenant_isolation_required=True,
        stable_ids_required=True,
        timestamps_required=True,
        implementation_authority="software-factory",
        direct_database_mutation_allowed=False,
        model_sha256=DOMAIN_SHA,
    )


def _auth(*, include_create: bool = True) -> AuthRbacPlan:
    operations = ["read", "update", "delete"]
    if include_create:
        operations.append("create")
    grants = tuple(
        PermissionGrant(permission=f"resource.Goal.{operation}", scope="resource", resource="Goal")
        for operation in operations
    )
    return AuthRbacPlan(
        project_id="project-1",
        spec_sha256=SPEC_SHA,
        architecture_plan_sha256=ARCH_SHA,
        data_migration_plan_sha256="e" * 64,
        auth_providers=("oidc",),
        roles=(RoleRequirement(role_id="Owner", grants=grants),),
        actor_role_bindings=(),
        authentication_required=True,
        authorization_required=True,
        session_required=True,
        refresh_required=True,
        logout_required=True,
        recovery_required=True,
        privileged_mfa_required=False,
        high_risk_approval_required=False,
        default_deny=True,
        server_authoritative=True,
        ui_visibility_is_authorization=False,
        raw_credentials_allowed_in_plan=False,
        authentication_authority="services.identity.AuthenticationBoundary",
        authorization_authority="services.identity.AuthorizationEngine",
        session_authority="services.identity.SessionRegistry",
        implementation_authority="software-factory",
        direct_permission_mutation_allowed=False,
        plan_sha256=AUTH_SHA,
    )


def _backend_contract() -> WebAppAuthContract:
    permissions = tuple(
        WebAppPermissionRequirement(
            permission=f"resource.Goal.{operation}",
            scope="resource",
            resource_type="Goal",
        )
        for operation in ("read", "create", "update", "delete")
    )
    names = tuple(item.permission for item in permissions)
    return WebAppAuthContract(
        schema_version="ilaios.web-app-auth-contract.v1",
        app_id="enterprise-app",
        project_id="project-1",
        spec_sha256=SPEC_SHA,
        identity_chain=("User", "Tenant", "Project", "Role", "Permission", "ResourceScope"),
        roles=(WebAppRolePermissionContract(role="Owner", permissions=names),),
        permissions=permissions,
        routes=(),
        actions=tuple(
            WebAppActionPermissionContract(action_id=f"action:{permission}", permission=permission)
            for permission in names
        ),
        authentication_required=True,
        default_deny=True,
        server_authoritative=True,
        ui_visibility_is_authorization=False,
        authentication_authority="services.identity.AuthenticationBoundary",
        authorization_authority="services.identity.AuthorizationEngine",
        session_authority="services.identity.SessionRegistry",
    )


def _principal(*, roles: frozenset[str] = frozenset({"Owner"})) -> Principal:
    return Principal(
        principal_id="user-1",
        tenant_id="tenant-1",
        kind=IdentityKind.HUMAN,
        roles=roles,
        attributes=frozenset(),
        authentication_methods=frozenset({"mfa"}),
    )


def _runtime() -> tuple[AppEnterpriseRuntime, AuditEngine]:
    contract = _backend_contract()
    binding = bind_enterprise_runtime(
        spec=_spec(), domain_model=_domain(), auth_rbac=_auth(), backend_contract=contract
    )
    audit = AuditEngine()
    backend = WebAppCrudRuntime(
        sqlite3.connect(":memory:"),
        contract,
        AuthorizationEngine(compile_authorization_rules(contract)),
        audit,
    )
    return AppEnterpriseRuntime(binding, backend), audit


def test_cross_platform_spec_reuses_real_persistent_crud_backend() -> None:
    runtime, audit = _runtime()
    created = runtime.create(
        principal=_principal(),
        entity="Goal",
        resource_id="goal-1",
        payload={"title": "Ship governed app runtime"},
        idempotency_key="create-1",
        now=NOW,
    )
    observed = runtime.read(
        principal=_principal(), entity="Goal", resource_id="goal-1", now=NOW
    )
    page = runtime.list(principal=_principal(), entity="Goal", now=NOW)

    assert created == observed
    assert page.items == (created,)
    assert runtime.binding.operations == ("create", "read", "list", "update", "delete")
    assert runtime.binding.backend_authority == "services.web_app_crud_runtime.WebAppCrudRuntime"
    assert runtime.binding.authorization_authority == "services.identity.AuthorizationEngine"
    assert runtime.binding.direct_database_authority is False
    assert audit.count() == 1


def test_update_delete_preserve_optimistic_concurrency_and_audit() -> None:
    runtime, audit = _runtime()
    created = runtime.create(
        principal=_principal(), entity="Goal", resource_id="goal-2",
        payload={"title": "Initial"}, idempotency_key="create-2", now=NOW,
    )
    updated = runtime.update(
        principal=_principal(), entity="Goal", resource_id="goal-2",
        payload={"title": "Updated"}, expected_version=created.version,
        idempotency_key="update-2", now=NOW,
    )
    assert updated.version == 2
    assert updated.payload == {"title": "Updated"}

    with pytest.raises(WebAppCrudRuntimeError, match="optimistic concurrency"):
        runtime.update(
            principal=_principal(), entity="Goal", resource_id="goal-2",
            payload={"title": "Stale"}, expected_version=1,
            idempotency_key="update-stale", now=NOW,
        )

    runtime.delete(
        principal=_principal(), entity="Goal", resource_id="goal-2",
        expected_version=updated.version, now=NOW,
    )
    with pytest.raises(WebAppCrudRuntimeError, match="resource not found"):
        runtime.read(principal=_principal(), entity="Goal", resource_id="goal-2", now=NOW)
    assert audit.count() == 4


def test_binding_fails_closed_when_stage2_permission_is_missing() -> None:
    with pytest.raises(AppEnterpriseRuntimeError, match="missing runtime permission"):
        bind_enterprise_runtime(
            spec=_spec(), domain_model=_domain(), auth_rbac=_auth(include_create=False),
            backend_contract=_backend_contract(),
        )


def test_binding_fails_closed_on_stale_product_spec_lineage() -> None:
    backend = _backend_contract()
    stale = ProductSpec(
        project_id="project-1", product_name="EnterpriseApp", objective="stale",
        platforms=("android",), actors=("operator",), screens=("goals",),
        capabilities=("crud",), locales=("en",), accessibility_required=True,
        offline_required=False, monetization="free", spec_sha256="f" * 64,
    )
    with pytest.raises(AppEnterpriseRuntimeError, match="domain model"):
        bind_enterprise_runtime(
            spec=stale, domain_model=_domain(), auth_rbac=_auth(), backend_contract=backend,
        )


def test_entity_outside_bound_domain_is_rejected_before_backend_access() -> None:
    runtime, _ = _runtime()
    with pytest.raises(AppEnterpriseRuntimeError, match="not admitted"):
        runtime.read(principal=_principal(), entity="Secret", resource_id="secret-1", now=NOW)
