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
from services.web_app_enterprise_table_runtime import (
    EnterpriseTableColumn,
    WebAppEnterpriseTableError,
    WebAppEnterpriseTableRuntime,
)
from src.core.audit_engine import AuditEngine

NOW = datetime(2026, 8, 24, 16, 30, tzinfo=timezone.utc)


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


def _runtime() -> tuple[WebAppCrudRuntime, WebAppEnterpriseTableRuntime]:
    contract = _contract()
    crud = WebAppCrudRuntime(
        sqlite3.connect(":memory:"),
        contract,
        AuthorizationEngine(compile_authorization_rules(contract)),
        AuditEngine(),
    )
    return crud, WebAppEnterpriseTableRuntime(crud)


def _columns() -> tuple[EnterpriseTableColumn, ...]:
    return (
        EnterpriseTableColumn(key="id", label="ID", source="resource_id"),
        EnterpriseTableColumn(key="title", label="Title", source="payload", payload_key="title"),
        EnterpriseTableColumn(key="status", label="Status", source="payload", payload_key="status"),
        EnterpriseTableColumn(key="version", label="Version", source="version"),
    )


def _seed(crud: WebAppCrudRuntime, principal: Principal) -> None:
    for index, status in enumerate(("open", "done", "open"), start=1):
        crud.create(
            principal=principal,
            resource_type="Goal",
            resource_id=f"goal-{index}",
            payload={"title": f"Goal {index}", "status": status},
            idempotency_key=f"create-{index}",
            now=NOW,
        )


def test_table_projects_bounded_filtered_paginated_rows() -> None:
    crud, tables = _runtime()
    principal = _principal()
    _seed(crud, principal)

    page = tables.query(
        principal=principal,
        resource_type="Goal",
        columns=_columns(),
        now=NOW,
        filters={"status": "open"},
        search="Goal",
        sort_key="id",
        descending=True,
        limit=1,
        density="compact",
    )

    assert page.total == 2
    assert page.density == "compact"
    assert page.rows[0].resource_id == "goal-3"
    assert dict(page.rows[0].cells) == {
        "id": "goal-3",
        "title": "Goal 3",
        "status": "open",
        "version": 1,
    }


def test_selection_revalidates_canonical_tenant_scoped_read_access() -> None:
    crud, tables = _runtime()
    tenant_one = _principal()
    _seed(crud, tenant_one)

    page = tables.query(
        principal=tenant_one,
        resource_type="Goal",
        columns=_columns(),
        now=NOW,
        selected_resource_ids=("goal-1", "goal-3"),
    )
    assert page.selected_resource_ids == ("goal-1", "goal-3")

    with pytest.raises(WebAppCrudRuntimeError) as cross_tenant:
        tables.query(
            principal=_principal(tenant_id="tenant-2"),
            resource_type="Goal",
            columns=_columns(),
            now=NOW,
            selected_resource_ids=("goal-1",),
        )
    assert cross_tenant.value.code == "NOT_FOUND"


def test_table_inherits_default_deny_from_canonical_authorization() -> None:
    crud, tables = _runtime()
    _seed(crud, _principal())

    with pytest.raises(IdentityError, match="deny by default"):
        tables.query(
            principal=_principal(roles=frozenset({"Viewer"})),
            resource_type="Goal",
            columns=_columns(),
            now=NOW,
        )


def test_payload_sort_is_rejected_instead_of_sorting_partial_page() -> None:
    crud, tables = _runtime()
    principal = _principal()
    _seed(crud, principal)

    with pytest.raises(WebAppEnterpriseTableError) as exc:
        tables.query(
            principal=principal,
            resource_type="Goal",
            columns=_columns(),
            now=NOW,
            sort_key="title",
        )
    assert exc.value.code == "UNSUPPORTED_SORT"


def test_invalid_columns_density_and_selection_fail_closed() -> None:
    crud, tables = _runtime()
    principal = _principal()
    _seed(crud, principal)

    with pytest.raises(WebAppEnterpriseTableError) as duplicate_column:
        tables.query(
            principal=principal,
            resource_type="Goal",
            columns=(
                EnterpriseTableColumn(key="id", label="ID", source="resource_id"),
                EnterpriseTableColumn(key="id", label="Again", source="version"),
            ),
            now=NOW,
        )
    assert duplicate_column.value.code == "DUPLICATE_COLUMN"

    with pytest.raises(WebAppEnterpriseTableError) as invalid_density:
        tables.query(
            principal=principal,
            resource_type="Goal",
            columns=_columns(),
            now=NOW,
            density="dense",  # type: ignore[arg-type]
        )
    assert invalid_density.value.code == "INVALID_DENSITY"

    with pytest.raises(WebAppEnterpriseTableError) as duplicate_selection:
        tables.query(
            principal=principal,
            resource_type="Goal",
            columns=_columns(),
            now=NOW,
            selected_resource_ids=("goal-1", "goal-1"),
        )
    assert duplicate_selection.value.code == "DUPLICATE_SELECTION"


def test_query_filter_and_search_inputs_are_bounded_fail_closed() -> None:
    crud, tables = _runtime()
    principal = _principal()
    _seed(crud, principal)

    with pytest.raises(WebAppEnterpriseTableError) as too_many_filters:
        tables.query(
            principal=principal,
            resource_type="Goal",
            columns=_columns(),
            now=NOW,
            filters={f"field-{index}": index for index in range(17)},
        )
    assert too_many_filters.value.code == "FILTERS_TOO_LARGE"

    with pytest.raises(WebAppEnterpriseTableError) as invalid_filter_key:
        tables.query(
            principal=principal,
            resource_type="Goal",
            columns=_columns(),
            now=NOW,
            filters={"status\nheader": "open"},
        )
    assert invalid_filter_key.value.code == "INVALID_TOKEN"

    with pytest.raises(WebAppEnterpriseTableError) as oversized_filter_value:
        tables.query(
            principal=principal,
            resource_type="Goal",
            columns=_columns(),
            now=NOW,
            filters={"status": "x" * 513},
        )
    assert oversized_filter_value.value.code == "INVALID_FILTER_VALUE"

    with pytest.raises(WebAppEnterpriseTableError) as nested_filter_value:
        tables.query(
            principal=principal,
            resource_type="Goal",
            columns=_columns(),
            now=NOW,
            filters={"status": {"$ne": "done"}},
        )
    assert nested_filter_value.value.code == "INVALID_FILTER_VALUE"

    with pytest.raises(WebAppEnterpriseTableError) as nonfinite_filter_value:
        tables.query(
            principal=principal,
            resource_type="Goal",
            columns=_columns(),
            now=NOW,
            filters={"score": float("inf")},
        )
    assert nonfinite_filter_value.value.code == "INVALID_FILTER_VALUE"

    with pytest.raises(WebAppEnterpriseTableError) as oversized_search:
        tables.query(
            principal=principal,
            resource_type="Goal",
            columns=_columns(),
            now=NOW,
            search="x" * 513,
        )
    assert oversized_search.value.code == "INVALID_SEARCH"

    with pytest.raises(WebAppEnterpriseTableError) as control_search:
        tables.query(
            principal=principal,
            resource_type="Goal",
            columns=_columns(),
            now=NOW,
            search="Goal\nopen",
        )
    assert control_search.value.code == "INVALID_SEARCH"
