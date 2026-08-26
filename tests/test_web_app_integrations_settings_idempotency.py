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

NOW = datetime(2026, 8, 26, 1, 40, tzinfo=timezone.utc)


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


class ReentrantAdapter:
    def __init__(self) -> None:
        self.runtime: WebAppIntegrationsSettingsRuntime | None = None
        self.calls = 0
        self.reentrant_error: WebAppIntegrationsSettingsError | None = None

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
        del capability_ref, tenant_id, project_id
        self.calls += 1
        if self.calls == 1:
            assert self.runtime is not None
            try:
                self.runtime.invoke(
                    principal=_principal(),
                    integration_id="crm",
                    operation=operation,
                    payload=payload,
                    idempotency_key=idempotency_key,
                    now=NOW,
                )
            except WebAppIntegrationsSettingsError as exc:
                self.reentrant_error = exc
        return {"ok": True, "calls": self.calls}


def test_idempotency_claim_is_durable_before_external_capability_invocation() -> None:
    contract = _contract()
    adapter = ReentrantAdapter()
    runtime = WebAppIntegrationsSettingsRuntime(
        sqlite3.connect(":memory:"),
        contract,
        AuthorizationEngine(compile_authorization_rules(contract)),
        AuditEngine(),
        adapter,
    )
    adapter.runtime = runtime
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
        operation="sync",
        payload={"contact_id": "c-1"},
        idempotency_key="execution-1-step-1",
        now=NOW,
    )

    assert first == {"ok": True, "calls": 1}
    assert adapter.calls == 1
    assert adapter.reentrant_error is not None
    assert adapter.reentrant_error.code == "IDEMPOTENCY_PENDING"

    replay = runtime.invoke(
        principal=_principal(),
        integration_id="crm",
        operation="sync",
        payload={"contact_id": "c-1"},
        idempotency_key="execution-1-step-1",
        now=NOW,
    )
    assert replay == first
    assert adapter.calls == 1


def test_pending_claim_rejects_payload_mutation_without_second_provider_call() -> None:
    contract = _contract()
    adapter = ReentrantAdapter()
    db = sqlite3.connect(":memory:")
    runtime = WebAppIntegrationsSettingsRuntime(
        db,
        contract,
        AuthorizationEngine(compile_authorization_rules(contract)),
        AuditEngine(),
        adapter,
    )
    adapter.runtime = runtime
    runtime.configure_integration(
        principal=_principal(),
        integration_id="crm",
        provider="example",
        capability_ref="capability.crm",
        public_config={},
        enabled=True,
        now=NOW,
    )
    db.execute(
        """INSERT INTO web_app_integration_invocation_claims
           (tenant_id, project_id, integration_id, operation, idempotency_key,
            payload_sha256, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            "tenant-1",
            "project-1",
            "crm",
            "sync",
            "execution-2-step-1",
            "0" * 64,
            NOW.isoformat(),
        ),
    )
    db.commit()

    with pytest.raises(WebAppIntegrationsSettingsError) as exc:
        runtime.invoke(
            principal=_principal(),
            integration_id="crm",
            operation="sync",
            payload={"contact_id": "different"},
            idempotency_key="execution-2-step-1",
            now=NOW,
        )
    assert exc.value.code == "IDEMPOTENCY_CONFLICT"
    assert adapter.calls == 0
