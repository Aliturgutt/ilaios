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
        if retain_until is not None and retain_until <= now:
            raise WebAppFilesOutputsError("INVALID_RETENTION", "retention must be in the future", 400)
        self._authorize(principal, "create", now)

        digest = hashlib.sha256(content).hexdigest()
        prior = self._db.execute(
            """SELECT MAX(version) AS version FROM web_app_outputs
               WHERE tenant_id=? AND project_id=? AND output_id=?""",
            (principal.tenant_id, self._contract.project_id, output_id),
        ).fetchone()
        version = 1 if prior is None or prior["version"] is None else int(prior["version"]) + 1
        object_key = self._object_key(principal.tenant_id, output_id, version, digest)
        timestamp = self._utc(now)
        retention = None if retain_until is None else self._utc(retain_until)

        self._storage.put(object_key=object_key, content=content)
        try:
            self._db.execute(
                """INSERT INTO web_app_outputs
                   (tenant_id, project_id, output_id, filename, mime_type, size_bytes,
                    sha256, version, object_key, created_at, retain_until)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    principal.tenant_id,
                    self._contract.project_id,
                    output_id,
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
            self._storage.delete(object_key=object_key)
            raise
        return self._read_record(principal.tenant_id, output_id, version)

    def download(
        self,
        *,
        principal: Principal,
        output_id: str,
        version: int,
        now: datetime,
    ) -> tuple[FileOutputRecord, bytes]:
        self._token(output_id, "output_id")
        if version < 1:
            raise WebAppFilesOutputsError("INVALID_VERSION", "version must be positive", 400)
        self._authorize(principal, "read", now)
        record = self._read_record(principal.tenant_id, output_id, version)
        content = self._storage.get(object_key=record.object_key)
        if len(content) != record.size_bytes or hashlib.sha256(content).hexdigest() != record.sha256:
            raise WebAppFilesOutputsError(
                "OUTPUT_INTEGRITY_FAILURE", "stored output failed exact hash/size validation", 500
            )
        return record, content

    def delete(
        self,
        *,
        principal: Principal,
        output_id: str,
        version: int,
        now: datetime,
    ) -> None:
        self._token(output_id, "output_id")
        if version < 1:
            raise WebAppFilesOutputsError("INVALID_VERSION", "version must be positive", 400)
        self._authorize(principal, "delete", now)
        record = self._read_record(principal.tenant_id, output_id, version)
        if record.retain_until is not None and self._parse_utc(record.retain_until) > now.astimezone(timezone.utc):
            raise WebAppFilesOutputsError("RETENTION_ACTIVE", "output is retention protected", 409)
        self._storage.delete(object_key=record.object_key)
        self._db.execute(
            """DELETE FROM web_app_outputs
               WHERE tenant_id=? AND project_id=? AND output_id=? AND version=?""",
            (principal.tenant_id, self._contract.project_id, output_id, version),
        )
        self._db.commit()

    def list_versions(
        self,
        *,
        principal: Principal,
        output_id: str,
        now: datetime,
    ) -> tuple[FileOutputRecord, ...]:
        self._token(output_id, "output_id")
        self._authorize(principal, "read", now)
        rows = self._db.execute(
            """SELECT * FROM web_app_outputs
               WHERE tenant_id=? AND project_id=? AND output_id=? ORDER BY version DESC""",
            (principal.tenant_id, self._contract.project_id, output_id),
        ).fetchall()
        return tuple(self._row(row) for row in rows)

    def _authorize(self, principal: Principal, operation: str, now: datetime) -> None:
        request = action_access_request(
            self._contract,
            action_id=f"action:resource.output.{operation}",
            tenant_id=principal.tenant_id,
            resource_tenant_id=principal.tenant_id,
        )
        authorize_with_canonical_engine(
            self._authorization, principal=principal, request=request, now=now
        )

    def _read_record(self, tenant_id: str, output_id: str, version: int) -> FileOutputRecord:
        row = self._db.execute(
            """SELECT * FROM web_app_outputs
               WHERE tenant_id=? AND project_id=? AND output_id=? AND version=?""",
            (tenant_id, self._contract.project_id, output_id, version),
        ).fetchone()
        if row is None:
            raise WebAppFilesOutputsError("NOT_FOUND", "output not found", 404)
        return self._row(row)

    @staticmethod
    def _row(row: sqlite3.Row) -> FileOutputRecord:
        return FileOutputRecord(
            output_id=str(row["output_id"]),
            tenant_id=str(row["tenant_id"]),
            project_id=str(row["project_id"]),
            filename=str(row["filename"]),
            mime_type=str(row["mime_type"]),
            size_bytes=int(row["size_bytes"]),
            sha256=str(row["sha256"]),
            version=int(row["version"]),
            object_key=str(row["object_key"]),
            created_at=str(row["created_at"]),
            retain_until=None if row["retain_until"] is None else str(row["retain_until"]),
        )

    def _initialize_schema(self) -> None:
        self._db.executescript(
            """
            CREATE TABLE IF NOT EXISTS web_app_outputs (
              tenant_id TEXT NOT NULL,
              project_id TEXT NOT NULL,
              output_id TEXT NOT NULL,
              filename TEXT NOT NULL,
              mime_type TEXT NOT NULL,
              size_bytes INTEGER NOT NULL CHECK(size_bytes > 0),
              sha256 TEXT NOT NULL,
              version INTEGER NOT NULL CHECK(version >= 1),
              object_key TEXT NOT NULL UNIQUE,
              created_at TEXT NOT NULL,
              retain_until TEXT,
              PRIMARY KEY (tenant_id, project_id, output_id, version)
            );
            CREATE INDEX IF NOT EXISTS idx_web_app_outputs_scope
              ON web_app_outputs(tenant_id, project_id, output_id, version);
            """
        )
        self._db.commit()

    @classmethod
    def _mime(cls, mime_type: str) -> None:
        if mime_type not in cls._ALLOWED_MIME:
            raise WebAppFilesOutputsError("INVALID_MIME", "unsupported MIME type", 415)

    @staticmethod
    def _filename(filename: str) -> None:
        if not filename or len(filename) > 180 or filename != filename.strip():
            raise WebAppFilesOutputsError("INVALID_FILENAME", "invalid filename", 400)
        if "/" in filename or "\\" in filename or ".." in filename or not filename.isprintable():
            raise WebAppFilesOutputsError("INVALID_FILENAME", "unsafe filename", 400)

    @staticmethod
    def _token(value: str, field: str) -> None:
        if not value or len(value) > 128 or value != value.strip() or not value.isprintable():
            raise WebAppFilesOutputsError("INVALID_TOKEN", f"invalid {field}", 400)
        allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.:")
        if any(char not in allowed for char in value):
            raise WebAppFilesOutputsError("INVALID_TOKEN", f"invalid {field}", 400)

    def _object_key(self, tenant_id: str, output_id: str, version: int, digest: str) -> str:
        scope = hashlib.sha256(
            f"{tenant_id}\0{self._contract.project_id}".encode("utf-8")
        ).hexdigest()[:24]
        return f"web-app/{scope}/{output_id}/v{version}-{digest}"

    @staticmethod
    def _utc(value: datetime) -> str:
        if value.tzinfo is None:
            raise WebAppFilesOutputsError("INVALID_TIME", "timezone-aware datetime required", 400)
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

    @staticmethod
    def _parse_utc(value: str) -> datetime:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
