"""Governed files/outputs runtime for Phase 9 generated Web Apps.

This module owns no identity, policy, approval, audit, evidence, tenant, credential,
or object-storage authority. Authorization is delegated to the canonical Web App
auth contract/AuthorizationEngine and bytes are delegated to an injected storage
adapter. Metadata is tenant/project scoped and fail-closed.
"""

from __future__ import annotations

import hashlib
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


class WebAppFilesOutputsError(RuntimeError):
    """Typed fail-closed Phase-9 runtime failure."""

    def __init__(self, code: str, message: str, status_code: int) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code


class ObjectStorageAdapter(Protocol):
    """Narrow non-authoritative byte-storage boundary."""

    def put(self, *, object_key: str, content: bytes) -> None: ...

    def get(self, *, object_key: str) -> bytes: ...

    def delete(self, *, object_key: str) -> None: ...


@dataclass(frozen=True, slots=True)
class FileOutputRecord:
    output_id: str
    tenant_id: str
    project_id: str
    filename: str
    mime_type: str
    size_bytes: int
    sha256: str
    version: int
    object_key: str
    created_at: str
    retain_until: str | None


class WebAppFilesOutputsRuntime:
    """Tenant-scoped file/output metadata with canonical authorization and hashing."""

    _ALLOWED_MIME = frozenset(
        {
            "application/json",
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/zip",
            "image/jpeg",
            "image/png",
            "image/webp",
            "text/csv",
            "text/plain",
        }
    )
    _MAX_BYTES = 25 * 1024 * 1024

    def __init__(
        self,
        connection: sqlite3.Connection,
        contract: WebAppAuthContract,
        authorization: AuthorizationEngine,
        audit: AuditEngine,
        storage: ObjectStorageAdapter,
    ) -> None:
        self._db = connection
        self._contract = contract
        self._authorization = authorization
        self._audit = audit
        self._storage = storage
        self._db.row_factory = sqlite3.Row
        self._initialize_schema()

    def store(
        self,
        *,
        principal: Principal,
        output_id: str,
        filename: str,
        mime_type: str,
        content: bytes,
        now: datetime,
        retain_until: datetime | None = None,
    ) -> FileOutputRecord:
        self._token(output_id, "output_id")
        self._filename(filename)
        self._mime(mime_type)
        if not content:
            raise WebAppFilesOutputsError("EMPTY_OUTPUT", "empty output is not accepted", 400)
        if len(content) > self._MAX_BYTES:
            raise WebAppFilesOutputsError("OUTPUT_TOO_LARGE", "output exceeds bounded size", 413)
        timestamp = self._utc(now)
        retention = None if retain_until is None else self._utc(retain_until)
        if retention is not None and self._parse_utc(retention) <= self._parse_utc(timestamp):
            raise WebAppFilesOutputsError("INVALID_RETENTION", "retention must be in the future", 400)
        self._authorize(principal, "create", now)

        digest = hashlib.sha256(content).hexdigest()
        version = self._allocate_version(principal.tenant_id, output_id)
        object_key = self._object_key(principal.tenant_id, output_id, version, digest)
        try:
            self._storage.put(object_key=object_key, content=content)
            self._db.execute(
                """
                INSERT INTO web_app_file_outputs (
                    output_id, tenant_id, project_id, filename, mime_type, size_bytes,
                    sha256, version, object_key, created_at, retain_until
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    output_id,
                    principal.tenant_id,
                    self._contract.project_id,
                    filename,
                    mime_type,
                    len(content),
                    digest,
                    version,
                    object_key,
                    timestamp,
                    retention,
                ),
            )
            self._db.commit()
        except Exception:
            self._db.rollback()
            try:
                self._storage.delete(object_key=object_key)
            except Exception:
                pass
            raise
        record = FileOutputRecord(
            output_id=output_id,
            tenant_id=principal.tenant_id,
            project_id=self._contract.project_id,
            filename=filename,
            mime_type=mime_type,
            size_bytes=len(content),
            sha256=digest,
            version=version,
            object_key=object_key,
            created_at=timestamp,
            retain_until=retention,
        )
        self._audit_success(principal, "store", record, now)
        return record

    def download(
        self,
        *,
        principal: Principal,
        output_id: str,
        version: int,
        now: datetime,
    ) -> tuple[FileOutputRecord, bytes]:
        self._authorize(principal, "read", now)
        record = self._record(principal.tenant_id, output_id, version)
        content = self._storage.get(object_key=record.object_key)
        if hashlib.sha256(content).hexdigest() != record.sha256:
            raise WebAppFilesOutputsError(
                "OUTPUT_INTEGRITY_FAILURE", "stored output hash mismatch", 500
            )
        self._audit_success(principal, "download", record, now)
        return record, content

    def list_versions(
        self, *, principal: Principal, output_id: str, now: datetime
    ) -> tuple[FileOutputRecord, ...]:
        self._authorize(principal, "read", now)
        rows = self._db.execute(
            """
            SELECT * FROM web_app_file_outputs
            WHERE tenant_id = ? AND project_id = ? AND output_id = ?
            ORDER BY version DESC
            """,
            (principal.tenant_id, self._contract.project_id, output_id),
        ).fetchall()
        return tuple(self._from_row(row) for row in rows)

    def delete(
        self,
        *,
        principal: Principal,
        output_id: str,
        version: int,
        now: datetime,
    ) -> None:
        self._authorize(principal, "delete", now)
        record = self._record(principal.tenant_id, output_id, version)
        if record.retain_until is not None and self._parse_utc(record.retain_until) > now.astimezone(timezone.utc):
            raise WebAppFilesOutputsError("RETENTION_ACTIVE", "output retention is active", 409)
        self._storage.delete(object_key=record.object_key)
        self._db.execute(
            "DELETE FROM web_app_file_outputs WHERE tenant_id = ? AND project_id = ? AND output_id = ? AND version = ?",
            (principal.tenant_id, self._contract.project_id, output_id, version),
        )
        self._db.commit()
        self._audit_success(principal, "delete", record, now)

    def _initialize_schema(self) -> None:
        self._db.execute(
            """
            CREATE TABLE IF NOT EXISTS web_app_file_outputs (
                output_id TEXT NOT NULL,
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                filename TEXT NOT NULL,
                mime_type TEXT NOT NULL,
                size_bytes INTEGER NOT NULL,
                sha256 TEXT NOT NULL,
                version INTEGER NOT NULL,
                object_key TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL,
                retain_until TEXT,
                PRIMARY KEY (tenant_id, project_id, output_id, version)
            )
            """
        )
        self._db.commit()

    def _allocate_version(self, tenant_id: str, output_id: str) -> int:
        row = self._db.execute(
            "SELECT COALESCE(MAX(version), 0) AS latest FROM web_app_file_outputs WHERE tenant_id = ? AND project_id = ? AND output_id = ?",
            (tenant_id, self._contract.project_id, output_id),
        ).fetchone()
        return int(row["latest"]) + 1

    def _record(self, tenant_id: str, output_id: str, version: int) -> FileOutputRecord:
        row = self._db.execute(
            "SELECT * FROM web_app_file_outputs WHERE tenant_id = ? AND project_id = ? AND output_id = ? AND version = ?",
            (tenant_id, self._contract.project_id, output_id, version),
        ).fetchone()
        if row is None:
            raise WebAppFilesOutputsError("NOT_FOUND", "output not found", 404)
        return self._from_row(row)

    @staticmethod
    def _from_row(row: sqlite3.Row) -> FileOutputRecord:
        return FileOutputRecord(**dict(row))

    def _authorize(self, principal: Principal, operation: str, now: datetime) -> None:
        authorize_with_canonical_engine(
            self._authorization,
            principal,
            action_access_request(
                self._contract,
                permission=f"resource.output.{operation}",
                resource_type="output",
                resource_id="files-outputs",
                now=now,
            ),
        )

    def _audit_success(
        self, principal: Principal, operation: str, record: FileOutputRecord, now: datetime
    ) -> None:
        self._audit.record(
            component="web_app_files_outputs_runtime",
            action=operation,
            status="success",
            details={
                "principal_id": principal.principal_id,
                "tenant_id": principal.tenant_id,
                "project_id": record.project_id,
                "output_id": record.output_id,
                "version": record.version,
                "mime_type": record.mime_type,
                "size_bytes": record.size_bytes,
                "sha256": record.sha256,
                "timestamp": self._utc(now),
            },
        )

    @classmethod
    def _mime(cls, mime_type: str) -> None:
        if mime_type not in cls._ALLOWED_MIME:
            raise WebAppFilesOutputsError("INVALID_MIME", "unsupported MIME type", 415)

    @staticmethod
    def _filename(filename: str) -> None:
        if (
            not filename
            or filename in {".", ".."}
            or "/" in filename
            or "\\" in filename
            or "\x00" in filename
        ):
            raise WebAppFilesOutputsError("INVALID_FILENAME", "unsafe filename", 400)

    @staticmethod
    def _token(value: str, field: str) -> None:
        if not value or len(value) > 160 or any(char.isspace() for char in value):
            raise WebAppFilesOutputsError("INVALID_IDENTIFIER", f"invalid {field}", 400)

    @staticmethod
    def _object_key(tenant_id: str, output_id: str, version: int, digest: str) -> str:
        safe_tenant = hashlib.sha256(tenant_id.encode("utf-8")).hexdigest()[:24]
        safe_output = hashlib.sha256(output_id.encode("utf-8")).hexdigest()[:24]
        return f"tenant/{safe_tenant}/output/{safe_output}/v{version}/{digest}"

    @staticmethod
    def _utc(value: datetime) -> str:
        if value.tzinfo is None or value.utcoffset() is None:
            raise WebAppFilesOutputsError("INVALID_TIME", "timezone-aware datetime required", 400)
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

    @staticmethod
    def _parse_utc(value: str) -> datetime:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
