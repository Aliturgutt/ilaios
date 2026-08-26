"""Governed Phase-10 integrations/settings runtime for generated Web Apps.

This module creates no credential, identity, policy, approval, audit/evidence, tenant,
or provider authority. Integrations reference bounded non-secret capabilities and invoke
an injected backend capability adapter only after canonical Web App authorization.
Project settings remain tenant/project scoped and fail closed.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol

from services.identity import AuthorizationEngine, Principal
from services.web_app_auth_contract import (
    WebAppAuthContract,
    action_access_request,
    authorize_with_canonical_engine,
)
from src.core.audit_engine import AuditEngine


class WebAppIntegrationsSettingsError(RuntimeError):
    def __init__(self, code: str, message: str, status_code: int) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code


class IntegrationCapabilityAdapter(Protocol):
    """Non-secret backend capability boundary; implementation owns no auth authority."""

    def invoke(
        self,
        *,
        capability_ref: str,
        operation: str,
        payload: dict[str, object],
        tenant_id: str,
        project_id: str,
        idempotency_key: str,
    ) -> dict[str, object]: ...


@dataclass(frozen=True, slots=True)
class IntegrationBinding:
    integration_id: str
    tenant_id: str
    project_id: str
    provider: str
    capability_ref: str
    enabled: bool
    public_config: dict[str, object]
    updated_at: str


@dataclass(frozen=True, slots=True)
class ProjectSetting:
    key: str
    value: str
    updated_at: str


class WebAppIntegrationsSettingsRuntime:
    _MAX_PUBLIC_CONFIG_KEYS = 24
    _MAX_TEXT = 512
    _MAX_PAYLOAD_BYTES = 64 * 1024
    _SECRET_MARKERS = (
        "secret",
        "password",
        "passwd",
        "token",
        "api_key",
        "apikey",
        "private_key",
        "credential",
        "authorization",
        "cookie",
    )

    def __init__(
        self,
        connection: sqlite3.Connection,
        contract: WebAppAuthContract,
        authorization: AuthorizationEngine,
        audit: AuditEngine,
        capability_adapter: IntegrationCapabilityAdapter,
    ) -> None:
        self._db = connection
        self._contract = contract
        self._authorization = authorization
        self._audit = audit
        self._capability_adapter = capability_adapter
        self._db.row_factory = sqlite3.Row
        self._initialize_schema()

    def configure_integration(
        self,
        *,
        principal: Principal,
        integration_id: str,
        provider: str,
        capability_ref: str,
        public_config: dict[str, object],
        enabled: bool,
        now: datetime,
    ) -> IntegrationBinding:
        self._token(integration_id, "integration_id")
        self._token(provider, "provider")
        self._token(capability_ref, "capability_ref")
        timestamp = self._utc(now)
        normalized = self._public_config(public_config)
        self._authorize(principal, "project.manage", now)
        encoded = json.dumps(normalized, sort_keys=True, separators=(",", ":"))
        self._db.execute(
            """INSERT INTO web_app_integrations
               (tenant_id, project_id, integration_id, provider, capability_ref,
                enabled, public_config_json, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(tenant_id, project_id, integration_id) DO UPDATE SET
                 provider=excluded.provider,
                 capability_ref=excluded.capability_ref,
                 enabled=excluded.enabled,
                 public_config_json=excluded.public_config_json,
                 updated_at=excluded.updated_at""",
            (
                principal.tenant_id,
                self._contract.project_id,
                integration_id,
                provider,
                capability_ref,
                1 if enabled else 0,
                encoded,
                timestamp,
            ),
        )
        self._db.commit()
        self._audit_success("configure_integration", principal, integration_id, now)
        return self.get_integration(principal=principal, integration_id=integration_id, now=now)

    def get_integration(
        self, *, principal: Principal, integration_id: str, now: datetime
    ) -> IntegrationBinding:
        self._token(integration_id, "integration_id")
        self._utc(now)
        self._authorize(principal, "app.view", now)
        row = self._db.execute(
            """SELECT * FROM web_app_integrations
               WHERE tenant_id=? AND project_id=? AND integration_id=?""",
            (principal.tenant_id, self._contract.project_id, integration_id),
        ).fetchone()
        if row is None:
            raise WebAppIntegrationsSettingsError("NOT_FOUND", "integration not found", 404)
        return self._integration_row(row)

    def invoke(
        self,
        *,
        principal: Principal,
        integration_id: str,
        operation: str,
        payload: dict[str, object],
        idempotency_key: str,
        now: datetime,
    ) -> dict[str, object]:
        self._token(integration_id, "integration_id")
        self._token(operation, "operation")
        self._token(idempotency_key, "idempotency_key")
        self._utc(now)
        self._authorize(principal, "integration.use", now)
        binding = self._read_binding(principal.tenant_id, integration_id)
        if not binding.enabled:
            raise WebAppIntegrationsSettingsError("INTEGRATION_DISABLED", "integration is disabled", 409)
        payload_json = self._safe_payload(payload)
        payload_sha = hashlib.sha256(payload_json.encode("utf-8")).hexdigest()
        prior = self._db.execute(
            """SELECT payload_sha256, response_json FROM web_app_integration_invocations
               WHERE tenant_id=? AND project_id=? AND integration_id=?
                 AND operation=? AND idempotency_key=?""",
            (
                principal.tenant_id,
                self._contract.project_id,
                integration_id,
                operation,
                idempotency_key,
            ),
        ).fetchone()
        if prior is not None:
            if str(prior["payload_sha256"]) != payload_sha:
                raise WebAppIntegrationsSettingsError(
                    "IDEMPOTENCY_CONFLICT", "idempotency key was already used for different input", 409
                )
            value = json.loads(str(prior["response_json"]))
            if not isinstance(value, dict):
                raise WebAppIntegrationsSettingsError("INVALID_CHECKPOINT", "cached response is invalid", 500)
            return value

        response = self._capability_adapter.invoke(
            capability_ref=binding.capability_ref,
            operation=operation,
            payload=json.loads(payload_json),
            tenant_id=principal.tenant_id,
            project_id=self._contract.project_id,
            idempotency_key=idempotency_key,
        )
        response_json = self._safe_payload(response)
        self._db.execute(
            """INSERT INTO web_app_integration_invocations
               (tenant_id, project_id, integration_id, operation, idempotency_key,
                payload_sha256, response_json, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                principal.tenant_id,
                self._contract.project_id,
                integration_id,
                operation,
                idempotency_key,
                payload_sha,
                response_json,
                self._utc(now),
            ),
        )
        self._db.commit()
        self._audit_success("invoke_integration", principal, integration_id, now)
        result = json.loads(response_json)
        if not isinstance(result, dict):
            raise WebAppIntegrationsSettingsError("INVALID_RESPONSE", "capability response is invalid", 502)
        return result

    def set_setting(
        self, *, principal: Principal, key: str, value: str, now: datetime
    ) -> ProjectSetting:
        self._token(key, "setting_key")
        self._text(value, "setting_value")
        timestamp = self._utc(now)
        self._authorize(principal, "project.manage", now)
        self._db.execute(
            """INSERT INTO web_app_project_settings
               (tenant_id, project_id, setting_key, setting_value, updated_at)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(tenant_id, project_id, setting_key) DO UPDATE SET
                 setting_value=excluded.setting_value,
                 updated_at=excluded.updated_at""",
            (principal.tenant_id, self._contract.project_id, key, value, timestamp),
        )
        self._db.commit()
        self._audit_success("set_setting", principal, key, now)
        return ProjectSetting(key=key, value=value, updated_at=timestamp)

    def get_setting(
        self, *, principal: Principal, key: str, now: datetime
    ) -> ProjectSetting:
        self._token(key, "setting_key")
        self._utc(now)
        self._authorize(principal, "app.view", now)
        row = self._db.execute(
            """SELECT setting_key, setting_value, updated_at FROM web_app_project_settings
               WHERE tenant_id=? AND project_id=? AND setting_key=?""",
            (principal.tenant_id, self._contract.project_id, key),
        ).fetchone()
        if row is None:
            raise WebAppIntegrationsSettingsError("NOT_FOUND", "setting not found", 404)
        return ProjectSetting(
            key=str(row["setting_key"]), value=str(row["setting_value"]), updated_at=str(row["updated_at"])
        )

    def _read_binding(self, tenant_id: str, integration_id: str) -> IntegrationBinding:
        row = self._db.execute(
            """SELECT * FROM web_app_integrations
               WHERE tenant_id=? AND project_id=? AND integration_id=?""",
            (tenant_id, self._contract.project_id, integration_id),
        ).fetchone()
        if row is None:
            raise WebAppIntegrationsSettingsError("NOT_FOUND", "integration not found", 404)
        return self._integration_row(row)

    def _authorize(self, principal: Principal, permission: str, now: datetime) -> None:
        request = action_access_request(
            self._contract,
            action_id=f"action:{permission}",
            tenant_id=principal.tenant_id,
            resource_tenant_id=principal.tenant_id,
        )
        authorize_with_canonical_engine(self._authorization, principal=principal, request=request, now=now)

    def _audit_success(self, operation: str, principal: Principal, target: str, now: datetime) -> None:
        self._audit.record(
            "web_app_integrations_settings_runtime",
            operation,
            "success",
            {
                "principal_id": principal.principal_id,
                "tenant_id": principal.tenant_id,
                "project_id": self._contract.project_id,
                "target": target,
            },
            timestamp=now.astimezone(timezone.utc),
        )

    def _public_config(self, value: dict[str, object]) -> dict[str, object]:
        if len(value) > self._MAX_PUBLIC_CONFIG_KEYS:
            raise WebAppIntegrationsSettingsError("CONFIG_TOO_LARGE", "public config has too many keys", 400)
        normalized: dict[str, object] = {}
        for key, item in value.items():
            self._token(key, "config_key")
            if self._looks_secret(key):
                raise WebAppIntegrationsSettingsError("SECRET_CONFIG_FORBIDDEN", "secret-like config key is forbidden", 400)
            if item is None or isinstance(item, (bool, int, float)):
                normalized[key] = item
            elif isinstance(item, str):
                self._text(item, "config_value")
                normalized[key] = item
            else:
                raise WebAppIntegrationsSettingsError("INVALID_CONFIG", "public config must be scalar", 400)
        return normalized

    def _safe_payload(self, payload: dict[str, object]) -> str:
        for key in payload:
            if self._looks_secret(str(key)):
                raise WebAppIntegrationsSettingsError("SECRET_PAYLOAD_FORBIDDEN", "secret-like payload key is forbidden", 400)
        try:
            encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise WebAppIntegrationsSettingsError("INVALID_PAYLOAD", "payload must be JSON-safe", 400) from exc
        if len(encoded.encode("utf-8")) > self._MAX_PAYLOAD_BYTES:
            raise WebAppIntegrationsSettingsError("PAYLOAD_TOO_LARGE", "payload exceeds bounded size", 413)
        return encoded

    @classmethod
    def _looks_secret(cls, key: str) -> bool:
        lowered = key.casefold().replace("-", "_")
        return any(marker in lowered for marker in cls._SECRET_MARKERS)

    @classmethod
    def _token(cls, value: str, field: str) -> None:
        if not value or value != value.strip() or len(value) > 128 or not value.isprintable():
            raise WebAppIntegrationsSettingsError("INVALID_TOKEN", f"invalid {field}", 400)
        if any(ch in value for ch in ("/", "\\", "\x00")):
            raise WebAppIntegrationsSettingsError("INVALID_TOKEN", f"invalid {field}", 400)

    @classmethod
    def _text(cls, value: str, field: str) -> None:
        if len(value) > cls._MAX_TEXT or not value.isprintable():
            raise WebAppIntegrationsSettingsError("INVALID_TEXT", f"invalid {field}", 400)

    @staticmethod
    def _utc(value: datetime) -> str:
        if value.tzinfo is None or value.utcoffset() is None:
            raise WebAppIntegrationsSettingsError("INVALID_TIME", "timezone-aware datetime required", 400)
        return value.astimezone(timezone.utc).isoformat()

    @staticmethod
    def _integration_row(row: sqlite3.Row) -> IntegrationBinding:
        config = json.loads(str(row["public_config_json"]))
        if not isinstance(config, dict):
            raise WebAppIntegrationsSettingsError("INVALID_CONFIG_STATE", "stored config is invalid", 500)
        return IntegrationBinding(
            integration_id=str(row["integration_id"]),
            tenant_id=str(row["tenant_id"]),
            project_id=str(row["project_id"]),
            provider=str(row["provider"]),
            capability_ref=str(row["capability_ref"]),
            enabled=bool(int(row["enabled"])),
            public_config=config,
            updated_at=str(row["updated_at"]),
        )

    def _initialize_schema(self) -> None:
        self._db.executescript(
            """
            CREATE TABLE IF NOT EXISTS web_app_integrations (
              tenant_id TEXT NOT NULL,
              project_id TEXT NOT NULL,
              integration_id TEXT NOT NULL,
              provider TEXT NOT NULL,
              capability_ref TEXT NOT NULL,
              enabled INTEGER NOT NULL CHECK(enabled IN (0, 1)),
              public_config_json TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              PRIMARY KEY (tenant_id, project_id, integration_id)
            );
            CREATE TABLE IF NOT EXISTS web_app_project_settings (
              tenant_id TEXT NOT NULL,
              project_id TEXT NOT NULL,
              setting_key TEXT NOT NULL,
              setting_value TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              PRIMARY KEY (tenant_id, project_id, setting_key)
            );
            CREATE TABLE IF NOT EXISTS web_app_integration_invocations (
              tenant_id TEXT NOT NULL,
              project_id TEXT NOT NULL,
              integration_id TEXT NOT NULL,
              operation TEXT NOT NULL,
              idempotency_key TEXT NOT NULL,
              payload_sha256 TEXT NOT NULL,
              response_json TEXT NOT NULL,
              created_at TEXT NOT NULL,
              PRIMARY KEY (tenant_id, project_id, integration_id, operation, idempotency_key)
            );
            """
        )
        self._db.commit()
