from __future__ import annotations

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
        roles=(
            WebAppRolePermissionContract(role="Viewer", permissions=(permission.permission,)),
            WebAppRolePermissionContract(role="Owner", permissions=(permission.permission,)),
        ),
        permissions=(permission,),
        routes=(),
        actions=(
            WebAppActionPermissionContract(
                action_id="action:resource.Goal.read", permission=permission.permission
            ),
        ),
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


def _runtimes(max_records: int = 1000) -> tuple[WebAppCrudRuntime, WebAppAnalyticsRuntime]:
    contract = _contract()
    authorization = AuthorizationEngine(compile_authorization_rules(contract))
    crud = WebAppCrudRuntime(sqlite3.connect(":memory:"), contract, authorization, AuditEngine())
    return crud, WebAppAnalyticsRuntime(crud, max_records=max_records)


def _seed(crud: WebAppCrudRuntime, *, tenant_id: str = "tenant-1") -> None:
    owner_contract = _contract()
    owner_auth = AuthorizationEngine(compile_authorization_rules(owner_contract))
    del owner_auth
    principal = _principal(tenant_id=tenant_id, role="Owner")
    # Seed through the same database/runtime path without adding analytics write authority.
    # The test contract grants read only, so insert directly as fixture data.
    rows = (
        ("goal-1", {"status": "open", "cost": 10}),
        ("goal-2", {"status": "done", "cost": 7.5}),
        ("goal-3", {"status": "open", "cost": "2.5"}),
    )
    for resource_id, payload in rows:
        crud._db.execute(  # noqa: SLF001 - fixture setup proves projection behavior only
            """INSERT INTO web_app_resources
               (tenant_id, project_id, resource_type, resource_id, payload_json,
                version, created_at, updated_at, deleted_at)
               VALUES (?, 'project-1', 'Goal', ?, ?, 1, ?, ?, NULL)""",
            (
                principal.tenant_id,
                resource_id,
                __import__("json").dumps(payload, sort_keys=True, separators=(",", ":")),
                NOW.isoformat(),
                NOW.isoformat(),
            ),
        )
    crud._db.commit()  # noqa: SLF001


def test_count_series_is_derived_from_authenticated_tenant_scoped_data() -> None:
    crud, analytics = _runtimes()
    _seed(crud)

    series = analytics.series(
        principal=_principal(),
        resource_type="Goal",
        dimension="status",
        metric="count",
        now=NOW,
    )

    assert [(point.category, point.value, point.records) for point in series.points] == [
        ("done", 1.0, 1),
        ("open", 2.0, 2),
    ]
    assert series.source_total == 3
    assert series.covered_records == 3
    assert series.truncated is False


def test_sum_series_uses_real_authenticated_payload_values() -> None:
    crud, analytics = _runtimes()
    _seed(crud)

    series = analytics.series(
        principal=_principal(),
        resource_type="Goal",
        dimension="status",
        metric="sum",
        metric_field="cost",
        now=NOW,
    )

    values = {point.category: point.value for point in series.points}
    assert values == {"done": 7.5, "open": 12.5}


def test_cross_tenant_projection_returns_no_foreign_records() -> None:
    crud, analytics = _runtimes()
    _seed(crud, tenant_id="tenant-1")

    series = analytics.series(
        principal=_principal(tenant_id="tenant-2"),
        resource_type="Goal",
        dimension="status",
        metric="count",
        now=NOW,
    )

    assert series.points == ()
    assert series.source_total == 0


def test_default_deny_is_inherited_from_canonical_authorization() -> None:
    crud, analytics = _runtimes()
    _seed(crud)

    with pytest.raises(IdentityError, match="deny by default"):
        analytics.series(
            principal=_principal(role="Unknown"),
            resource_type="Goal",
            dimension="status",
            metric="count",
            now=NOW,
        )


def test_invalid_or_missing_metric_data_fails_closed() -> None:
    crud, analytics = _runtimes()
    _seed(crud)
    crud._db.execute(  # noqa: SLF001
        "UPDATE web_app_resources SET payload_json=? WHERE resource_id='goal-2'",
        ('{"status":"done","cost":"not-a-number"}',),
    )
    crud._db.commit()  # noqa: SLF001

    with pytest.raises(WebAppAnalyticsRuntimeError) as exc:
        analytics.series(
            principal=_principal(),
            resource_type="Goal",
            dimension="status",
            metric="sum",
            metric_field="cost",
            now=NOW,
        )
    assert exc.value.code == "INVALID_METRIC_VALUE"


def test_bounded_projection_reports_truncation_instead_of_claiming_full_coverage() -> None:
    crud, analytics = _runtimes(max_records=2)
    _seed(crud)

    series = analytics.series(
        principal=_principal(),
        resource_type="Goal",
        dimension="status",
        metric="count",
        now=NOW,
    )

    assert series.source_total == 3
    assert series.covered_records == 2
    assert series.truncated is True


def test_field_and_metric_contract_rejects_ambiguous_requests() -> None:
    _, analytics = _runtimes()

    with pytest.raises(WebAppAnalyticsRuntimeError) as missing:
        analytics.series(
            principal=_principal(),
            resource_type="Goal",
            dimension="status",
            metric="sum",
            now=NOW,
        )
    assert missing.value.code == "MISSING_METRIC_FIELD"

    with pytest.raises(WebAppAnalyticsRuntimeError) as invalid:
        analytics.series(
            principal=_principal(),
            resource_type="Goal",
            dimension="status;DROP TABLE",
            metric="count",
            now=NOW,
        )
    assert invalid.value.code == "INVALID_FIELD"
