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
from services.web_app_integrations_settings_runtime import (
    WebAppIntegrationsSettingsError,
    WebAppIntegrationsSettingsRuntime,
)
from src.core.audit_engine import AuditEngine

NOW = datetime(2026, 8, 26, 6, 36, tzinfo=timezone.utc)


class NoopCapabilityAdapter:
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
        raise AssertionError("project setting persistence must not invoke a provider capability")


def _runtime() -> tuple[WebAppIntegrationsSettingsRuntime, Principal]:
    permissions = (
        WebAppPermissionRequirement("app.view", "project"),
        WebAppPermissionRequirement("project.manage", "project", privileged=True),
    )
    names = tuple(item.permission for item in permissions)
    contract = WebAppAuthContract(
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
    principal = Principal(
        principal_id="user-1",
        tenant_id="tenant-1",
        kind=IdentityKind.HUMAN,
        roles=frozenset({"Owner"}),
        attributes=frozenset(),
        authentication_methods=frozenset({"mfa"}),
    )
    runtime = WebAppIntegrationsSettingsRuntime(
        sqlite3.connect(":memory:"),
        contract,
        AuthorizationEngine(compile_authorization_rules(contract)),
        AuditEngine(),
        NoopCapabilityAdapter(),
    )
    return runtime, principal


def test_secret_like_project_setting_keys_fail_closed_before_persistence() -> None:
    runtime, principal = _runtime()

    for key in ("api_key", "access-token", "provider_password", "clientCredential"):
        with pytest.raises(WebAppIntegrationsSettingsError) as exc:
            runtime.set_setting(principal=principal, key=key, value="forbidden", now=NOW)
        assert exc.value.code == "SECRET_SETTING_FORBIDDEN"

        with pytest.raises(WebAppIntegrationsSettingsError) as missing:
            runtime.get_setting(principal=principal, key=key, now=NOW)
        assert missing.value.code == "NOT_FOUND"


def test_non_secret_project_setting_remains_supported() -> None:
    runtime, principal = _runtime()

    saved = runtime.set_setting(principal=principal, key="theme", value="dark", now=NOW)

    assert saved.key == "theme"
    assert runtime.get_setting(principal=principal, key="theme", now=NOW).value == "dark"
