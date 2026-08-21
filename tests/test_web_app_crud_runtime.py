from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

import pytest

from services.identity import AuthorizationEngine, IdentityError, IdentityKind, Principal
from services.web_app_auth_contract import (
    WebAppActionPermissionContract,
    WebAppAuthContract,
    WebAppPermissionRequirement,
    WebAppRolePermissionContract,
    compile_authorization_rules,
)
from services.web_app_crud_runtime import WebAppCrudRuntime, WebAppCrudRuntimeError
from src.core.audit_engine import AuditEngine

NOW = datetime(2026, 8, 21, 15, 30, tzinfo=timezone.utc)


def _contract() -> WebAppAuthContract:
    permissions = tuple(
        WebAppPermissionRequirement(
            permission=f"resource.Goal.{operation}",
            scope="resource",
            resource_type="Goal",
            privileged=operation == "delete",
        )
        for operation in ("read", "create", "update", "delete")
    )
    names = tuple(item.permission for item in permissions)
    return WebAppAuthContract(
        schema_version="ilaios.web-app-auth-contract.v1",
        app_id="app-1",
        project_id="project-1",
        spec_sha256="a" * 64,
        identity_chain=("User", "Tenant", "Project", "Role", "Permission", "ResourceScope"),
        roles=(WebAppRolePermissionContract(role="Owner", permissions=names),),
        permissions=permissions,
        routes=(),
        actions=tuple(
            WebAppActionPermissionContract(
                action_id=f"action:{permission}", permission=permission
            )
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


def _principal(*, tenant_id: str = "tenant-1", roles: frozenset[str] | None = None) -> Principal:
    return Principal(
        principal_id="user-1",
        tenant_id=tenant_id,
        kind=IdentityKind.HUMAN,
        roles=roles if roles is not None else frozenset({"Owner"}),
        attributes=frozenset(),
        authentication_methods=frozenset({"mfa"}),
    )


def _runtime() -> tuple[WebAppCrudRuntime, AuditEngine]:
    contract = _contract()
    audit = AuditEngine()
    runtime = WebAppCrudRuntime(
        sqlite3.connect(":memory:"),
        contract,
        AuthorizationEngine(compile_authorization_rules(contract)),
        audit,
    )
    return runtime, audit


def test_crud_lifecycle_is_persistent_versioned_and_audited() -> None:
    runtime, audit = _runtime()
    principal = _principal()

    created = runtime.create(
        principal=principal,
        resource_type="Goal",
        resource_id="goal-1",
        payload={"title": "Ship", "status": "open"},
        idempotency_key="create-1",
        now=NOW,
    )
    assert created.version == 1
    assert runtime.read(
        principal=principal, resource_type="Goal", resource_id="goal-1", now=NOW
    ).payload["title"] == "Ship"

    updated = runtime.update(
        principal=principal,
        resource_type="Goal",
        resource_id="goal-1",
        payload={"title": "Ship", "status": "done"},
        expected_version=1,
        idempotency_key="update-1",
        now=NOW,
    )
    assert updated.version == 2
    assert updated.payload["status"] == "done"

    runtime.delete(
        principal=principal,
        resource_type="Goal",
        resource_id="goal-1",
        expected_version=2,
        now=NOW,
    )
    with pytest.raises(WebAppCrudRuntimeError, match="resource not found"):
        runtime.read(
            principal=principal, resource_type="Goal", resource_id="goal-1", now=NOW
        )
    assert audit.count() == 3


def test_default_deny_rejects_role_without_permission() -> None:
    runtime, _ = _runtime()
    with pytest.raises(IdentityError, match="deny by default"):
        runtime.create(
            principal=_principal(roles=frozenset({"Viewer"})),
            resource_type="Goal",
            resource_id="goal-1",
            payload={"title": "Denied"},
            idempotency_key="create-1",
            now=NOW,
        )


def test_tenant_scope_prevents_cross_tenant_record_visibility() -> None:
    runtime, _ = _runtime()
    runtime.create(
        principal=_principal(),
        resource_type="Goal",
        resource_id="goal-1",
        payload={"title": "Tenant one"},
        idempotency_key="create-1",
        now=NOW,
    )
    with pytest.raises(WebAppCrudRuntimeError) as exc:
        runtime.read(
            principal=_principal(tenant_id="tenant-2"),
            resource_type="Goal",
            resource_id="goal-1",
            now=NOW,
        )
    assert exc.value.code == "NOT_FOUND"


def test_idempotency_replays_same_create_and_rejects_mutated_request() -> None:
    runtime, _ = _runtime()
    principal = _principal()
    first = runtime.create(
        principal=principal,
        resource_type="Goal",
        resource_id="goal-1",
        payload={"title": "Stable"},
        idempotency_key="create-1",
        now=NOW,
    )
    replay = runtime.create(
        principal=principal,
        resource_type="Goal",
        resource_id="goal-1",
        payload={"title": "Stable"},
        idempotency_key="create-1",
        now=NOW,
    )
    assert replay == first
    with pytest.raises(WebAppCrudRuntimeError) as exc:
        runtime.create(
            principal=principal,
            resource_type="Goal",
            resource_id="goal-1",
            payload={"title": "Changed"},
            idempotency_key="create-1",
            now=NOW,
        )
    assert exc.value.code == "IDEMPOTENCY_CONFLICT"


def test_optimistic_concurrency_and_bounded_query_contracts() -> None:
    runtime, _ = _runtime()
    principal = _principal()
    for index, status in enumerate(("open", "done", "open"), start=1):
        runtime.create(
            principal=principal,
            resource_type="Goal",
            resource_id=f"goal-{index}",
            payload={"title": f"Goal {index}", "status": status},
            idempotency_key=f"create-{index}",
            now=NOW,
        )

    page = runtime.list(
        principal=principal,
        resource_type="Goal",
        now=NOW,
        filters={"status": "open"},
        search="Goal",
        sort_field="resource_id",
        descending=True,
        limit=1,
    )
    assert page.total == 2
    assert [item.resource_id for item in page.items] == ["goal-3"]

    with pytest.raises(WebAppCrudRuntimeError) as exc:
        runtime.update(
            principal=principal,
            resource_type="Goal",
            resource_id="goal-1",
            payload={"title": "stale"},
            expected_version=99,
            idempotency_key="update-stale",
            now=NOW,
        )
    assert exc.value.code == "VERSION_CONFLICT"

    with pytest.raises(WebAppCrudRuntimeError) as invalid_page:
        runtime.list(
            principal=principal,
            resource_type="Goal",
            now=NOW,
            limit=101,
        )
    assert invalid_page.value.code == "INVALID_PAGE"
