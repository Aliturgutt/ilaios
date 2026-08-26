from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pytest

from services.identity import AuthorizationEngine, IdentityKind, Principal
from services.web_app_auth_contract import (
    WebAppActionPermissionContract,
    WebAppAuthContract,
    WebAppPermissionRequirement,
    WebAppRolePermissionContract,
    compile_authorization_rules,
)
from services.web_app_integrations_settings_runtime import (
    IntegrationReconciliationResult,
    WebAppIntegrationsSettingsError,
    WebAppIntegrationsSettingsRuntime,
)
from src.core.audit_engine import AuditEngine

NOW = datetime(2026, 8, 26, 3, 0, tzinfo=timezone.utc)


def _contract() -> WebAppAuthContract:
    permissions = (
        WebAppPermissionRequirement("app.view", "project"),
        WebAppPermissionRequirement("project.manage", "project", privileged=True),
        WebAppPermissionRequirement("integration.use", "project", privileged=True),
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
            WebAppActionPermissionContract(action_id=f"action:{name}", permission=name)
            for name in names
        ),
        authentication_required=True,
        default_deny=True,
        server_authoritative=True,
        ui_visibility_is_authorization=False,
        authentication_authority="services.identity.AuthenticationBoundary",
        authorization_authority="services.identity.AuthorizationEngine",
        session_authority="services.identity.SessionRegistry",
    )


def _principal() -> Principal:
    return Principal(
        principal_id="user-1",
        tenant_id="tenant-1",
        kind=IdentityKind.HUMAN,
        roles=frozenset({"Owner"}),
        attributes=frozenset(),
        authentication_methods=frozenset({"mfa"}),
    )


class ReconcileAdapter:
    def __init__(self) -> None:
        self.invoke_calls = 0
        self.resolution = IntegrationReconciliationResult("COMPLETED", {"ok": True})

    def invoke(
        self,
        *,
        capability_ref: str,
        operation: str,
        payload: dict[str, object],
        tenant_id: str,
        project_id: str,
        idempotency_key: str,
    ) -> dict[str, object]:
        self.invoke_calls += 1
        raise TimeoutError("provider result became unknown after dispatch")

    def reconcile(
        self,
        *,
        capability_ref: str,
        operation: str,
        payload: dict[str, object],
        tenant_id: str,
        project_id: str,
        idempotency_key: str,
    ) -> IntegrationReconciliationResult:
        return self.resolution


def _runtime(path: Path, adapter: ReconcileAdapter) -> WebAppIntegrationsSettingsRuntime:
    contract = _contract()
    return WebAppIntegrationsSettingsRuntime(
        sqlite3.connect(path),
        contract,
        AuthorizationEngine(compile_authorization_rules(contract)),
        AuditEngine(),
        adapter,
    )


def _configure(runtime: WebAppIntegrationsSettingsRuntime) -> None:
    runtime.configure_integration(
        principal=_principal(),
        integration_id="crm",
        provider="example",
        capability_ref="capability.crm",
        public_config={},
        enabled=True,
        now=NOW,
    )


def test_process_restart_reconciles_completed_external_effect_without_second_invoke(
    tmp_path: Path,
) -> None:
    db = tmp_path / "integration.sqlite3"
    adapter = ReconcileAdapter()
    first = _runtime(db, adapter)
    _configure(first)

    with pytest.raises(TimeoutError):
        first.invoke(
            principal=_principal(),
            integration_id="crm",
            operation="sync",
            payload={"record": "r-1"},
            idempotency_key="exec-1-step-1",
            now=NOW,
        )
    assert adapter.invoke_calls == 1

    restarted = _runtime(db, adapter)
    reconciled = restarted.reconcile_invocation(
        principal=_principal(),
        integration_id="crm",
        operation="sync",
        payload={"record": "r-1"},
        idempotency_key="exec-1-step-1",
        now=NOW,
    )
    assert reconciled == {"ok": True}

    cached = restarted.invoke(
        principal=_principal(),
        integration_id="crm",
        operation="sync",
        payload={"record": "r-1"},
        idempotency_key="exec-1-step-1",
        now=NOW,
    )
    assert cached == {"ok": True}
    assert adapter.invoke_calls == 1


def test_retry_is_released_only_after_backend_proves_not_executed(tmp_path: Path) -> None:
    db = tmp_path / "integration.sqlite3"
    adapter = ReconcileAdapter()
    runtime = _runtime(db, adapter)
    _configure(runtime)

    with pytest.raises(TimeoutError):
        runtime.invoke(
            principal=_principal(),
            integration_id="crm",
            operation="sync",
            payload={"record": "r-1"},
            idempotency_key="exec-2-step-1",
            now=NOW,
        )

    adapter.resolution = IntegrationReconciliationResult("NOT_EXECUTED")
    assert runtime.reconcile_invocation(
        principal=_principal(),
        integration_id="crm",
        operation="sync",
        payload={"record": "r-1"},
        idempotency_key="exec-2-step-1",
        now=NOW,
    ) == {"status": "RETRY_ALLOWED"}

    adapter.resolution = IntegrationReconciliationResult("COMPLETED", {"ok": True})
    with pytest.raises(TimeoutError):
        runtime.invoke(
            principal=_principal(),
            integration_id="crm",
            operation="sync",
            payload={"record": "r-1"},
            idempotency_key="exec-2-step-1",
            now=NOW,
        )
    assert adapter.invoke_calls == 2


def test_ambiguous_or_mismatched_reconciliation_fails_closed(tmp_path: Path) -> None:
    db = tmp_path / "integration.sqlite3"
    adapter = ReconcileAdapter()
    runtime = _runtime(db, adapter)
    _configure(runtime)

    with pytest.raises(TimeoutError):
        runtime.invoke(
            principal=_principal(),
            integration_id="crm",
            operation="sync",
            payload={"record": "r-1"},
            idempotency_key="exec-3-step-1",
            now=NOW,
        )

    with pytest.raises(WebAppIntegrationsSettingsError) as conflict:
        runtime.reconcile_invocation(
            principal=_principal(),
            integration_id="crm",
            operation="sync",
            payload={"record": "different"},
            idempotency_key="exec-3-step-1",
            now=NOW,
        )
    assert conflict.value.code == "IDEMPOTENCY_CONFLICT"
