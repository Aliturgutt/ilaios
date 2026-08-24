from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

import pytest

from services.identity import AuthorizationEngine, IdentityKind, Principal
from services.web_app_auth_contract import (
    WebAppActionPermissionContract,
    WebAppAuthContract,
    WebAppPermissionRequirement,
    WebAppRolePermissionContract,
    compile_authorization_rules,
)
from services.web_app_crud_runtime import WebAppCrudRuntime, WebAppCrudRuntimeError
from services.web_app_realtime_runtime import WebAppRealtimeRuntime
from src.core.audit_engine import AuditEngine

NOW = datetime(2026, 8, 24, 2, 20, tzinfo=timezone.utc)


def _principal() -> Principal:
    return Principal(
        principal_id="user-1",
        tenant_id="tenant-1",
        kind=IdentityKind.HUMAN,
        roles=frozenset({"Operator"}),
        attributes=frozenset(),
        authentication_methods=frozenset({"mfa"}),
    )


def _runtime() -> tuple[WebAppCrudRuntime, WebAppRealtimeRuntime]:
    permissions = tuple(
        WebAppPermissionRequirement(
            permission=f"resource.Goal.{operation}",
            scope="resource",
            resource_type="Goal",
            privileged=False,
        )
        for operation in ("read", "create", "update", "delete")
    )
    permission_names = tuple(permission.permission for permission in permissions)
    contract = WebAppAuthContract(
        schema_version="ilaios.web-app-auth-contract.v1",
        app_id="app-realtime-delete",
        project_id="project-delete",
        spec_sha256="d" * 64,
        identity_chain=("User", "Tenant", "Project", "Role", "Permission", "ResourceScope"),
        roles=(WebAppRolePermissionContract(role="Operator", permissions=permission_names),),
        permissions=permissions,
        routes=(),
        actions=tuple(
            WebAppActionPermissionContract(
                action_id=f"action:{permission}", permission=permission
            )
            for permission in permission_names
        ),
        authentication_required=True,
        default_deny=True,
        server_authoritative=True,
        ui_visibility_is_authorization=False,
        authentication_authority="services.identity.AuthenticationBoundary",
        authorization_authority="services.identity.AuthorizationEngine",
        session_authority="services.identity.SessionRegistry",
    )
    authorization = AuthorizationEngine(compile_authorization_rules(contract))
    crud = WebAppCrudRuntime(sqlite3.connect(":memory:"), contract, authorization, AuditEngine())
    realtime = WebAppRealtimeRuntime(crud)
    return crud, realtime


def test_deleted_projection_requires_canonical_delete_then_uses_tombstone_version() -> None:
    crud, realtime = _runtime()
    principal = _principal()
    record = crud.create(
        principal=principal,
        resource_type="Goal",
        resource_id="goal-1",
        payload={"status": "open"},
        idempotency_key="create-goal-1",
        now=NOW,
    )

    with pytest.raises(WebAppCrudRuntimeError, match="resource not found"):
        realtime.publish(
            principal=principal,
            resource_type="Goal",
            resource_id="goal-1",
            event_type="deleted",
            payload={"status": "deleted"},
            now=NOW,
        )

    crud.delete(
        principal=principal,
        resource_type="Goal",
        resource_id="goal-1",
        expected_version=record.version,
        now=NOW,
    )

    event = realtime.publish(
        principal=principal,
        resource_type="Goal",
        resource_id="goal-1",
        event_type="deleted",
        payload={"status": "deleted"},
        now=NOW,
        resource_version=record.version + 1,
    )

    assert event.event_type == "deleted"
    assert event.resource_version == 2
    assert event.tenant_id == principal.tenant_id


def test_deleted_projection_cannot_replay_tombstone_across_tenants() -> None:
    crud, realtime = _runtime()
    owner = _principal()
    record = crud.create(
        principal=owner,
        resource_type="Goal",
        resource_id="goal-1",
        payload={"status": "open"},
        idempotency_key="create-goal-1",
        now=NOW,
    )
    crud.delete(
        principal=owner,
        resource_type="Goal",
        resource_id="goal-1",
        expected_version=record.version,
        now=NOW,
    )

    attacker = Principal(
        principal_id="user-2",
        tenant_id="tenant-2",
        kind=IdentityKind.HUMAN,
        roles=frozenset({"Operator"}),
        attributes=frozenset(),
        authentication_methods=frozenset({"mfa"}),
    )
    with pytest.raises(WebAppCrudRuntimeError, match="resource not found"):
        realtime.publish(
            principal=attacker,
            resource_type="Goal",
            resource_id="goal-1",
            event_type="deleted",
            payload={"status": "forged"},
            now=NOW,
        )
