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
from services.web_app_integrations_settings_runtime import (
    WebAppIntegrationsSettingsError,
    WebAppIntegrationsSettingsRuntime,
)
from src.core.audit_engine import AuditEngine

NOW = datetime(2026, 8, 26, 0, 30, tzinfo=timezone.utc)


class MemoryCapabilityAdapter:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

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
        self.calls.append(
            {
                "capability_ref": capability_ref,
                "operation": operation,
                "payload": payload,
                "tenant_id": tenant_id,
                "project_id": project_id,
                "idempotency_key": idempotency_key,
            }
        )
        return {"ok": True, "operation": operation, "count": len(self.calls)}


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
        roles=(
            WebAppRolePermissionContract(role="Owner", permissions=names),
            WebAppRolePermissionContract(role="Viewer", permissions=("app.view",)),
        ),
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


def _principal(*, tenant_id: str = "tenant-1", roles: frozenset[str] | None = None) -> Principal:
    return Principal(
        principal_id="user-1",
        tenant_id=tenant_id,
        kind=IdentityKind.HUMAN,
        roles=roles if roles is not None else frozenset({"Owner"}),
        attributes=frozenset(),
        authentication_methods=frozenset({"mfa"}),
    )


def _runtime() -> tuple[WebAppIntegrationsSettingsRuntime, MemoryCapabilityAdapter, AuditEngine]:
    contract = _contract()
    adapter = MemoryCapabilityAdapter()
    audit = AuditEngine()
    runtime = WebAppIntegrationsSettingsRuntime(
        sqlite3.connect(":memory:"),
        contract,
        AuthorizationEngine(compile_authorization_rules(contract)),
        audit,
        adapter,
    )
    return runtime, adapter, audit


def test_configure_integration_stores_only_non_secret_capability_reference() -> None:
    runtime, _adapter, _audit = _runtime()
    binding = runtime.configure_integration(
        principal=_principal(),
        integration_id="crm",
        provider="example",
        capability_ref="capability.crm.readwrite",
        public_config={"region": "eu", "sync_enabled": True},
        enabled=True,
        now=NOW,
    )
    assert binding.capability_ref == "capability.crm.readwrite"
    assert binding.public_config == {"region": "eu", "sync_enabled": True}

    with pytest.raises(WebAppIntegrationsSettingsError) as exc:
        runtime.configure_integration(
            principal=_principal(),
            integration_id="bad",
            provider="example",
            capability_ref="capability.bad",
            public_config={"api_key": "must-never-be-stored"},
            enabled=True,
            now=NOW,
        )
    assert exc.value.code == "SECRET_CONFIG_FORBIDDEN"


def test_cross_tenant_binding_lookup_fails_closed() -> None:
    runtime, _adapter, _audit = _runtime()
    runtime.configure_integration(
        principal=_principal(),
        integration_id="crm",
        provider="example",
        capability_ref="capability.crm",
        public_config={},
        enabled=True,
        now=NOW,
    )
    with pytest.raises(WebAppIntegrationsSettingsError) as exc:
        runtime.get_integration(
            principal=_principal(tenant_id="tenant-2"), integration_id="crm", now=NOW
        )
    assert exc.value.code == "NOT_FOUND"


def test_invoke_is_idempotent_and_rejects_key_reuse_with_different_payload() -> None:
    runtime, adapter, _audit = _runtime()
    runtime.configure_integration(
        principal=_principal(),
        integration_id="crm",
        provider="example",
        capability_ref="capability.crm",
        public_config={},
        enabled=True,
        now=NOW,
    )
    first = runtime.invoke(
        principal=_principal(),
        integration_id="crm",
        operation="upsert_contact",
        payload={"contact_id": "c-1", "name": "Ada"},
        idempotency_key="job-1-step-1",
        now=NOW,
    )
    second = runtime.invoke(
        principal=_principal(),
        integration_id="crm",
        operation="upsert_contact",
        payload={"name": "Ada", "contact_id": "c-1"},
        idempotency_key="job-1-step-1",
        now=NOW,
    )
    assert first == second
    assert len(adapter.calls) == 1

    with pytest.raises(WebAppIntegrationsSettingsError) as exc:
        runtime.invoke(
            principal=_principal(),
            integration_id="crm",
            operation="upsert_contact",
            payload={"contact_id": "c-2"},
            idempotency_key="job-1-step-1",
            now=NOW,
        )
    assert exc.value.code == "IDEMPOTENCY_CONFLICT"
    assert len(adapter.calls) == 1


def test_secret_like_invocation_payload_fails_before_adapter() -> None:
    runtime, adapter, _audit = _runtime()
    runtime.configure_integration(
        principal=_principal(),
        integration_id="crm",
        provider="example",
        capability_ref="capability.crm",
        public_config={},
        enabled=True,
        now=NOW,
    )
    with pytest.raises(WebAppIntegrationsSettingsError) as exc:
        runtime.invoke(
            principal=_principal(),
            integration_id="crm",
            operation="sync",
            payload={"access_token": "forbidden"},
            idempotency_key="sync-1",
            now=NOW,
        )
    assert exc.value.code == "SECRET_PAYLOAD_FORBIDDEN"
    assert adapter.calls == []


def test_disabled_integration_and_default_deny_role_do_not_invoke_adapter() -> None:
    runtime, adapter, _audit = _runtime()
    runtime.configure_integration(
        principal=_principal(),
        integration_id="crm",
        provider="example",
        capability_ref="capability.crm",
        public_config={},
        enabled=False,
        now=NOW,
    )
    with pytest.raises(WebAppIntegrationsSettingsError) as disabled:
        runtime.invoke(
            principal=_principal(),
            integration_id="crm",
            operation="sync",
            payload={},
            idempotency_key="sync-1",
            now=NOW,
        )
    assert disabled.value.code == "INTEGRATION_DISABLED"

    with pytest.raises(IdentityError, match="deny by default"):
        runtime.configure_integration(
            principal=_principal(roles=frozenset({"Viewer"})),
            integration_id="other",
            provider="example",
            capability_ref="capability.other",
            public_config={},
            enabled=True,
            now=NOW,
        )
    assert adapter.calls == []


def test_project_settings_are_tenant_scoped_and_manage_authorized() -> None:
    runtime, _adapter, audit = _runtime()
    setting = runtime.set_setting(
        principal=_principal(), key="theme", value="dark", now=NOW
    )
    assert setting.value == "dark"
    assert runtime.get_setting(principal=_principal(), key="theme", now=NOW).value == "dark"

    with pytest.raises(WebAppIntegrationsSettingsError) as cross_tenant:
        runtime.get_setting(
            principal=_principal(tenant_id="tenant-2"), key="theme", now=NOW
        )
    assert cross_tenant.value.code == "NOT_FOUND"

    actions = tuple(record.action for record in audit.get_records(component="web_app_integrations_settings_runtime"))
    assert "set_setting" in actions


def test_non_secret_public_config_remains_scalar_and_bounded() -> None:
    runtime, _adapter, _audit = _runtime()
    with pytest.raises(WebAppIntegrationsSettingsError) as nested:
        runtime.configure_integration(
            principal=_principal(),
            integration_id="nested",
            provider="example",
            capability_ref="capability.nested",
            public_config={"options": {"admin": True}},
            enabled=True,
            now=NOW,
        )
    assert nested.value.code == "INVALID_CONFIG"

    with pytest.raises(WebAppIntegrationsSettingsError) as time_error:
        runtime.set_setting(
            principal=_principal(),
            key="theme",
            value="dark",
            now=datetime(2026, 8, 26, 0, 30),
        )
    assert time_error.value.code == "INVALID_TIME"
