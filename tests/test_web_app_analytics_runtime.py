from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone

import pytest

from services.identity import AuthorizationEngine, IdentityError, IdentityKind, Principal
from services.web_app_analytics_runtime import (
    WebAppAnalyticsRuntime,
    WebAppAnalyticsRuntimeError,
)
from services.web_app_auth_contract import (
    WebAppActionPermissionContract,
    WebAppAuthContract,
    WebAppPermissionRequirement,
    WebAppRolePermissionContract,
    compile_authorization_rules,
)
from services.web_app_crud_runtime import WebAppCrudRuntime
from src.core.audit_engine import AuditEngine

NOW = datetime(2026, 8, 21, 17, 50, tzinfo=timezone.utc)


def _contract() -> WebAppAuthContract:
    permission = WebAppPermissionRequirement(
        permission="resource.Goal.read",
        scope="resource",
        resource_type="Goal",
        privileged=False,
    )
    return WebAppAuthContract(
        schema_version="ilaios.web-app-auth-contract.v1",
        app_id="app-analytics",
        project_id="project-1",
        spec_sha256="b" * 64,
        identity_chain=("User", "Tenant", "Project", "Role", "Permission", "ResourceScope"),
        roles=(WebAppRolePermissionContract(role="Viewer", permissions=(permission.permission,)),),
        permissions=(permission,),
        routes=(),
        actions=(WebAppActionPermissionContract(action_id="action:resource.Goal.read", permission=permission.permission),),
        authentication_required=True,
        default_deny=True,
        server_authoritative=True,
        ui_visibility_is_authorization=False,
        authentication_authority="services.identity.AuthenticationBoundary",
        authorization_authority="services.identity.AuthorizationEngine",
        session_authority="services.identity.SessionRegistry",
    )


def _principal(*, tenant_id: str = "tenant-1", role: str = "Viewer") -> Principal:
    return Principal(
        principal_id="user-1",
        tenant_id=tenant_id,
        kind=IdentityKind.HUMAN,
        roles=frozenset({role}),
        attributes=frozenset(),
        authentication_methods=frozenset({"mfa"}),
    )


def _runtimes(max_records: int = 1000) -> tuple[sqlite3.Connection, WebAppAnalyticsRuntime]:
    contract = _contract()
    authorization = AuthorizationEngine(compile_authorization_rules(contract))
    connection = sqlite3.connect(":memory:")
    crud = WebAppCrudRuntime(connection, contract, authorization, AuditEngine())
    return connection, WebAppAnalyticsRuntime(crud, max_records=max_records)


def _seed(connection: sqlite3.Connection, *, tenant_id: str = "tenant-1") -> None:
    rows = (
        ("goal-1", {"status": "open", "cost": 10}),
        ("goal-2", {"status": "done", "cost": 7.5}),
        ("goal-3", {"status": "open", "cost": "2.5"}),
    )
    for resource_id, payload in rows:
        connection.execute(
            """INSERT INTO web_app_resources
               (tenant_id, project_id, resource_type, resource_id, payload_json,
                version, created_at, updated_at, deleted_at)
               VALUES (?, 'project-1', 'Goal', ?, ?, 1, ?, ?, NULL)""",
            (tenant_id, resource_id, json.dumps(payload, sort_keys=True, separators=(",", ":")), NOW.isoformat(), NOW.isoformat()),
        )
    connection.commit()


def test_count_series_is_derived_from_authenticated_tenant_scoped_data() -> None:
    connection, analytics = _runtimes()
    _seed(connection)
    series = analytics.series(principal=_principal(), resource_type="Goal", dimension="status", metric="count", now=NOW)
    assert [(point.category, point.value, point.records) for point in series.points] == [("done", 1.0, 1), ("open", 2.0, 2)]
    assert series.source_total == 3
    assert series.covered_records == 3
    assert series.truncated is False


def test_sum_series_uses_real_authenticated_payload_values() -> None:
    connection, analytics = _runtimes()
    _seed(connection)
    series = analytics.series(principal=_principal(), resource_type="Goal", dimension="status", metric="sum", metric_field="cost", now=NOW)
    assert {point.category: point.value for point in series.points} == {"done": 7.5, "open": 12.5}


def test_cross_tenant_projection_returns_no_foreign_records() -> None:
    connection, analytics = _runtimes()
    _seed(connection, tenant_id="tenant-1")
    series = analytics.series(principal=_principal(tenant_id="tenant-2"), resource_type="Goal", dimension="status", metric="count", now=NOW)
    assert series.points == ()
    assert series.source_total == 0


def test_default_deny_is_inherited_from_canonical_authorization() -> None:
    connection, analytics = _runtimes()
    _seed(connection)
    with pytest.raises(IdentityError, match="deny by default"):
        analytics.series(principal=_principal(role="Unknown"), resource_type="Goal", dimension="status", metric="count", now=NOW)


def test_invalid_metric_data_fails_closed() -> None:
    connection, analytics = _runtimes()
    _seed(connection)
    connection.execute("UPDATE web_app_resources SET payload_json=? WHERE resource_id='goal-2'", ('{"status":"done","cost":"not-a-number"}',))
    connection.commit()
    with pytest.raises(WebAppAnalyticsRuntimeError) as exc:
        analytics.series(principal=_principal(), resource_type="Goal", dimension="status", metric="sum", metric_field="cost", now=NOW)
    assert exc.value.code == "INVALID_METRIC_VALUE"


def test_bounded_projection_reports_truncation_instead_of_claiming_full_coverage() -> None:
    connection, analytics = _runtimes(max_records=2)
    _seed(connection)
    series = analytics.series(principal=_principal(), resource_type="Goal", dimension="status", metric="count", now=NOW)
    assert series.source_total == 3
    assert series.covered_records == 2
    assert series.truncated is True


def test_field_and_metric_contract_rejects_ambiguous_requests() -> None:
    _, analytics = _runtimes()
    with pytest.raises(WebAppAnalyticsRuntimeError) as missing:
        analytics.series(principal=_principal(), resource_type="Goal", dimension="status", metric="sum", now=NOW)
    assert missing.value.code == "MISSING_METRIC_FIELD"
    with pytest.raises(WebAppAnalyticsRuntimeError) as invalid:
        analytics.series(principal=_principal(), resource_type="Goal", dimension="status;DROP TABLE", metric="count", now=NOW)
    assert invalid.value.code == "INVALID_FIELD"
