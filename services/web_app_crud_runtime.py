"""Governed generic CRUD runtime for Phase 5 generated Web Apps.

The runtime is intentionally subordinate to the canonical Phase-3 auth contract,
``services.identity.AuthorizationEngine`` and core ``AuditEngine``. It owns no
identity, policy, approval, audit, evidence, tenant, or routing authority.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

from services.identity import AuthorizationEngine, Principal
from services.web_app_auth_contract import (
    WebAppAuthContract,
    action_access_request,
    authorize_with_canonical_engine,
)
from src.core.audit_engine import AuditEngine

CrudOperation = Literal["read", "create", "update", "delete"]


class WebAppCrudRuntimeError(RuntimeError):
    """Typed fail-closed CRUD runtime failure."""

    def __init__(self, code: str, message: str, status_code: int) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code


@dataclass(frozen=True, slots=True)
class CrudRecord:
    resource_type: str
    resource_id: str
    tenant_id: str
    project_id: str
    payload: dict[str, object]
    version: int
    created_at: str
    updated_at: str


@dataclass(frozen=True, slots=True)
class CrudPage:
    items: tuple[CrudRecord, ...]
    offset: int
    limit: int
    total: int


class WebAppCrudRuntime:
    """SQLite-backed tenant/project-scoped CRUD runtime with canonical authorization."""

    def __init__(
        self,
        connection: sqlite3.Connection,
        contract: WebAppAuthContract,
        authorization: AuthorizationEngine,
        audit: AuditEngine,
    ) -> None:
        self._db = connection
        self._contract = contract
        self._authorization = authorization
        self._audit = audit
        self._db.row_factory = sqlite3.Row
        self._initialize_schema()

    def create(
        self,
        *,
        principal: Principal,
        resource_type: str,
        resource_id: str,
        payload: dict[str, object],
        idempotency_key: str,
        now: datetime,
    ) -> CrudRecord:
        self._validate_resource(resource_type, resource_id)
        self._validate_payload(payload)
        self._token(idempotency_key, "idempotency_key")
        self._authorize(principal, resource_type, "create", now)
        request_hash = self._request_hash(resource_type, resource_id, payload)
        timestamp = self._utc(now)
        try:
            self._db.execute("BEGIN IMMEDIATE")
            prior = self._db.execute(
                """SELECT request_hash, resource_id FROM web_app_idempotency
                   WHERE tenant_id=? AND project_id=? AND resource_type=? AND operation='create'
                     AND idempotency_key=?""",
                (principal.tenant_id, self._contract.project_id, resource_type, idempotency_key),
            ).fetchone()
            if prior is not None:
                if str(prior["request_hash"]) != request_hash:
                    raise WebAppCrudRuntimeError(
                        "IDEMPOTENCY_CONFLICT", "idempotency key reused with different request", 409
                    )
                record = self._read_row(
                    principal.tenant_id, resource_type, str(prior["resource_id"])
                )
                self._db.commit()
                return record
            try:
                self._db.execute(
                    """INSERT INTO web_app_resources
                       (tenant_id, project_id, resource_type, resource_id, payload_json,
                        version, created_at, updated_at, deleted_at)
                       VALUES (?, ?, ?, ?, ?, 1, ?, ?, NULL)""",
                    (
                        principal.tenant_id,
                        self._contract.project_id,
                        resource_type,
                        resource_id,
                        self._payload_json(payload),
                        timestamp,
                        timestamp,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise WebAppCrudRuntimeError("ALREADY_EXISTS", "resource already exists", 409) from exc
            self._db.execute(
                """INSERT INTO web_app_idempotency
                   (tenant_id, project_id, resource_type, operation, idempotency_key,
                    request_hash, resource_id, created_at)
                   VALUES (?, ?, ?, 'create', ?, ?, ?, ?)""",
                (
                    principal.tenant_id,
                    self._contract.project_id,
                    resource_type,
                    idempotency_key,
                    request_hash,
                    resource_id,
                    timestamp,
                ),
            )
            record = self._read_row(principal.tenant_id, resource_type, resource_id)
            self._db.commit()
        except Exception:
            self._db.rollback()
            self._record_audit(principal, resource_type, "create", "failure", resource_id)
            raise
        self._record_audit(principal, resource_type, "create", "success", resource_id)
        return record

    def read(
        self,
        *,
        principal: Principal,
        resource_type: str,
        resource_id: str,
        now: datetime,
    ) -> CrudRecord:
        self._validate_resource(resource_type, resource_id)
        self._authorize(principal, resource_type, "read", now)
        return self._read_row(principal.tenant_id, resource_type, resource_id)

    def list(
        self,
        *,
        principal: Principal,
        resource_type: str,
        now: datetime,
        offset: int = 0,
        limit: int = 50,
        filters: dict[str, object] | None = None,
        search: str | None = None,
        sort_field: str = "updated_at",
        descending: bool = False,
    ) -> CrudPage:
        self._token(resource_type, "resource_type")
        if offset < 0 or limit < 1 or limit > 100:
            raise WebAppCrudRuntimeError("INVALID_PAGE", "offset/limit outside bounded range", 400)
        self._authorize(principal, resource_type, "read", now)
        rows = self._db.execute(
            """SELECT * FROM web_app_resources
               WHERE tenant_id=? AND project_id=? AND resource_type=? AND deleted_at IS NULL""",
            (principal.tenant_id, self._contract.project_id, resource_type),
        ).fetchall()
        records = [self._row_to_record(row) for row in rows]
        if filters:
            records = [
                item
                for item in records
                if all(item.payload.get(key) == value for key, value in filters.items())
            ]
        if search:
            needle = search.casefold()
            records = [
                item
                for item in records
                if needle in json.dumps(item.payload, sort_keys=True, ensure_ascii=False).casefold()
            ]
        allowed_sort = {"resource_id", "created_at", "updated_at", "version"}
        if sort_field not in allowed_sort:
            raise WebAppCrudRuntimeError("INVALID_SORT", "unsupported sort field", 400)
        records.sort(key=lambda item: getattr(item, sort_field), reverse=descending)
        total = len(records)
        return CrudPage(tuple(records[offset : offset + limit]), offset, limit, total)

    def update(
        self,
        *,
        principal: Principal,
        resource_type: str,
        resource_id: str,
        payload: dict[str, object],
        expected_version: int,
        idempotency_key: str,
        now: datetime,
    ) -> CrudRecord:
        self._validate_resource(resource_type, resource_id)
        self._validate_payload(payload)
        self._token(idempotency_key, "idempotency_key")
        if expected_version < 1:
            raise WebAppCrudRuntimeError("INVALID_VERSION", "expected_version must be positive", 400)
        self._authorize(principal, resource_type, "update", now)
        request_hash = self._request_hash(resource_type, resource_id, payload, expected_version)
        timestamp = self._utc(now)
        try:
            self._db.execute("BEGIN IMMEDIATE")
            prior = self._idempotent_result(
                principal.tenant_id, resource_type, "update", idempotency_key, request_hash
            )
            if prior is not None:
                self._db.commit()
                return prior
            cursor = self._db.execute(
                """UPDATE web_app_resources
                   SET payload_json=?, version=version+1, updated_at=?
                   WHERE tenant_id=? AND project_id=? AND resource_type=? AND resource_id=?
                     AND deleted_at IS NULL AND version=?""",
                (
                    self._payload_json(payload),
                    timestamp,
                    principal.tenant_id,
                    self._contract.project_id,
                    resource_type,
                    resource_id,
                    expected_version,
                ),
            )
            if cursor.rowcount != 1:
                self._raise_missing_or_version(principal.tenant_id, resource_type, resource_id)
            self._store_idempotency(
                principal.tenant_id,
                resource_type,
                "update",
                idempotency_key,
                request_hash,
                resource_id,
                timestamp,
            )
            record = self._read_row(principal.tenant_id, resource_type, resource_id)
            self._db.commit()
        except Exception:
            self._db.rollback()
            self._record_audit(principal, resource_type, "update", "failure", resource_id)
            raise
        self._record_audit(principal, resource_type, "update", "success", resource_id)
        return record

    def delete(
        self,
        *,
        principal: Principal,
        resource_type: str,
        resource_id: str,
        expected_version: int,
        now: datetime,
    ) -> None:
        self._validate_resource(resource_type, resource_id)
        if expected_version < 1:
            raise WebAppCrudRuntimeError("INVALID_VERSION", "expected_version must be positive", 400)
        self._authorize(principal, resource_type, "delete", now)
        timestamp = self._utc(now)
        try:
            self._db.execute("BEGIN IMMEDIATE")
            cursor = self._db.execute(
                """UPDATE web_app_resources
                   SET deleted_at=?, updated_at=?, version=version+1
                   WHERE tenant_id=? AND project_id=? AND resource_type=? AND resource_id=?
                     AND deleted_at IS NULL AND version=?""",
                (
                    timestamp,
                    timestamp,
                    principal.tenant_id,
                    self._contract.project_id,
                    resource_type,
                    resource_id,
                    expected_version,
                ),
            )
            if cursor.rowcount != 1:
                self._raise_missing_or_version(principal.tenant_id, resource_type, resource_id)
            self._db.commit()
        except Exception:
            self._db.rollback()
            self._record_audit(principal, resource_type, "delete", "failure", resource_id)
            raise
        self._record_audit(principal, resource_type, "delete", "success", resource_id)

    def _authorize(
        self,
        principal: Principal,
        resource_type: str,
        operation: CrudOperation,
        now: datetime,
    ) -> None:
        request = action_access_request(
            self._contract,
            action_id=f"action:resource.{resource_type}.{operation}",
            tenant_id=principal.tenant_id,
            resource_tenant_id=principal.tenant_id,
        )
        authorize_with_canonical_engine(
            self._authorization, principal=principal, request=request, now=now
        )

    def _initialize_schema(self) -> None:
        self._db.executescript(
            """
            CREATE TABLE IF NOT EXISTS web_app_resources (
              tenant_id TEXT NOT NULL,
              project_id TEXT NOT NULL,
              resource_type TEXT NOT NULL,
              resource_id TEXT NOT NULL,
              payload_json TEXT NOT NULL,
              version INTEGER NOT NULL CHECK(version >= 1),
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              deleted_at TEXT,
              PRIMARY KEY (tenant_id, project_id, resource_type, resource_id)
            );
            CREATE INDEX IF NOT EXISTS idx_web_app_resources_scope
              ON web_app_resources(tenant_id, project_id, resource_type, updated_at);
            CREATE TABLE IF NOT EXISTS web_app_idempotency (
              tenant_id TEXT NOT NULL,
              project_id TEXT NOT NULL,
              resource_type TEXT NOT NULL,
              operation TEXT NOT NULL,
              idempotency_key TEXT NOT NULL,
              request_hash TEXT NOT NULL,
              resource_id TEXT NOT NULL,
              created_at TEXT NOT NULL,
              PRIMARY KEY (tenant_id, project_id, resource_type, operation, idempotency_key)
            );
            """
        )
        self._db.commit()

    def _read_row(self, tenant_id: str, resource_type: str, resource_id: str) -> CrudRecord:
        row = self._db.execute(
            """SELECT * FROM web_app_resources
               WHERE tenant_id=? AND project_id=? AND resource_type=? AND resource_id=?
                 AND deleted_at IS NULL""",
            (tenant_id, self._contract.project_id, resource_type, resource_id),
        ).fetchone()
        if row is None:
            raise WebAppCrudRuntimeError("NOT_FOUND", "resource not found", 404)
        return self._row_to_record(row)

    def _row_to_record(self, row: sqlite3.Row) -> CrudRecord:
        raw = json.loads(str(row["payload_json"]))
        if not isinstance(raw, dict):
            raise WebAppCrudRuntimeError("CORRUPT_RECORD", "stored payload is not an object", 500)
        payload: dict[str, object] = {str(key): value for key, value in raw.items()}
        return CrudRecord(
            resource_type=str(row["resource_type"]),
            resource_id=str(row["resource_id"]),
            tenant_id=str(row["tenant_id"]),
            project_id=str(row["project_id"]),
            payload=payload,
            version=int(row["version"]),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
        )

    def _idempotent_result(
        self,
        tenant_id: str,
        resource_type: str,
        operation: str,
        key: str,
        request_hash: str,
    ) -> CrudRecord | None:
        row = self._db.execute(
            """SELECT request_hash, resource_id FROM web_app_idempotency
               WHERE tenant_id=? AND project_id=? AND resource_type=? AND operation=?
                 AND idempotency_key=?""",
            (tenant_id, self._contract.project_id, resource_type, operation, key),
        ).fetchone()
        if row is None:
            return None
        if str(row["request_hash"]) != request_hash:
            raise WebAppCrudRuntimeError(
                "IDEMPOTENCY_CONFLICT", "idempotency key reused with different request", 409
            )
        return self._read_row(tenant_id, resource_type, str(row["resource_id"]))

    def _store_idempotency(
        self,
        tenant_id: str,
        resource_type: str,
        operation: str,
        key: str,
        request_hash: str,
        resource_id: str,
        timestamp: str,
    ) -> None:
        self._db.execute(
            """INSERT INTO web_app_idempotency
               (tenant_id, project_id, resource_type, operation, idempotency_key,
                request_hash, resource_id, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                tenant_id,
                self._contract.project_id,
                resource_type,
                operation,
                key,
                request_hash,
                resource_id,
                timestamp,
            ),
        )

    def _raise_missing_or_version(self, tenant_id: str, resource_type: str, resource_id: str) -> None:
        row = self._db.execute(
            """SELECT version FROM web_app_resources
               WHERE tenant_id=? AND project_id=? AND resource_type=? AND resource_id=?
                 AND deleted_at IS NULL""",
            (tenant_id, self._contract.project_id, resource_type, resource_id),
        ).fetchone()
        if row is None:
            raise WebAppCrudRuntimeError("NOT_FOUND", "resource not found", 404)
        raise WebAppCrudRuntimeError("VERSION_CONFLICT", "optimistic concurrency conflict", 409)

    def _record_audit(
        self,
        principal: Principal,
        resource_type: str,
        operation: CrudOperation,
        status: Literal["success", "failure"],
        resource_id: str,
    ) -> None:
        self._audit.record(
            "web_app_crud_runtime",
            f"resource.{resource_type}.{operation}",
            status,
            {
                "principal_id": principal.principal_id,
                "tenant_id": principal.tenant_id,
                "project_id": self._contract.project_id,
                "resource_id": resource_id,
            },
        )

    @staticmethod
    def _payload_json(payload: dict[str, object]) -> str:
        try:
            return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        except (TypeError, ValueError) as exc:
            raise WebAppCrudRuntimeError("INVALID_PAYLOAD", "payload must be JSON serializable", 400) from exc

    @classmethod
    def _request_hash(cls, *values: object) -> str:
        encoded = json.dumps(values, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()

    @classmethod
    def _validate_resource(cls, resource_type: str, resource_id: str) -> None:
        cls._token(resource_type, "resource_type")
        cls._token(resource_id, "resource_id")

    @classmethod
    def _validate_payload(cls, payload: dict[str, object]) -> None:
        if not payload or len(payload) > 200:
            raise WebAppCrudRuntimeError("INVALID_PAYLOAD", "payload must be a bounded object", 400)
        cls._payload_json(payload)

    @staticmethod
    def _token(value: str, field: str) -> None:
        if (
            not value
            or value != value.strip()
            or len(value) > 160
            or any(character.isspace() for character in value)
            or "*" in value
        ):
            raise WebAppCrudRuntimeError("INVALID_TOKEN", f"{field} is not a bounded token", 400)

    @staticmethod
    def _utc(now: datetime) -> str:
        if now.tzinfo is None:
            raise WebAppCrudRuntimeError("INVALID_TIME", "timezone-aware time is required", 400)
        return now.astimezone(timezone.utc).isoformat()
