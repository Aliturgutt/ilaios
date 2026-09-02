"""Governed raw source-file persistence boundary.

This module stores immutable source bytes outside Knowledge semantics. It owns no
identity, tenant selection, Policy, Approval, Tool Gateway, or Evidence authority.
Callers must supply server-authoritative tenant/project/source scope.
"""

from __future__ import annotations

import hashlib
import os
import sqlite3
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


class GovernedSourceFileError(RuntimeError):
    """Fail-closed source-file persistence failure."""


@dataclass(frozen=True, slots=True)
class SourceFileRecord:
    tenant_id: str
    project_id: str
    source_id: str
    version: int
    filename: str
    mime_type: str
    size_bytes: int
    sha256: str
    object_key: str
    state: str
    retain_until: str | None


class GovernedSourceFileStore:
    """Tenant/project-scoped immutable source bytes with version tombstones.

    Bytes are content-addressed on the local governed runtime filesystem. Metadata is
    SQLite-backed so restart does not lose source/version lineage. This is a concrete
    local runtime adapter, not a claim of cloud object-storage deployment.
    """

    _MAX_BYTES = 25 * 1024 * 1024

    def __init__(self, root: Path) -> None:
        self._root = root
        self._objects = root / "objects"
        self._db_path = root / "source_files.sqlite3"
        self._objects.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(self._db_path)
        self._db.row_factory = sqlite3.Row
        self._db.executescript(
            """
            CREATE TABLE IF NOT EXISTS governed_source_files (
              tenant_id TEXT NOT NULL,
              project_id TEXT NOT NULL,
              source_id TEXT NOT NULL,
              version INTEGER NOT NULL CHECK(version >= 1),
              filename TEXT NOT NULL,
              mime_type TEXT NOT NULL,
              size_bytes INTEGER NOT NULL CHECK(size_bytes > 0),
              sha256 TEXT NOT NULL,
              object_key TEXT NOT NULL,
              state TEXT NOT NULL CHECK(state IN ('active','revoked','deleted')),
              retain_until TEXT,
              PRIMARY KEY (tenant_id, project_id, source_id, version)
            );
            """
        )
        self._db.commit()

    def store(
        self,
        *,
        tenant_id: str,
        project_id: str,
        source_id: str,
        version: int,
        filename: str,
        mime_type: str,
        content: bytes,
        retain_until: datetime | None = None,
    ) -> SourceFileRecord:
        self._scope(tenant_id, "tenant_id")
        self._scope(project_id, "project_id")
        self._scope(source_id, "source_id")
        self._filename(filename)
        if version < 1:
            raise GovernedSourceFileError("source version must be positive")
        if not mime_type or mime_type != mime_type.strip():
            raise GovernedSourceFileError("mime_type is invalid")
        if not content:
            raise GovernedSourceFileError("source file is empty")
        if len(content) > self._MAX_BYTES:
            raise GovernedSourceFileError("source file exceeds bounded size")
        retention = None
        if retain_until is not None:
            normalized = retain_until.astimezone(timezone.utc)
            if normalized <= datetime.now(timezone.utc):
                raise GovernedSourceFileError("retention must be in the future")
            retention = normalized.isoformat()

        digest = hashlib.sha256(content).hexdigest()
        object_key = f"sha256/{digest[:2]}/{digest}"
        path = self._path(object_key)
        self._put_immutable(path, content, digest)
        try:
            self._db.execute(
                """INSERT INTO governed_source_files
                   (tenant_id, project_id, source_id, version, filename, mime_type,
                    size_bytes, sha256, object_key, state, retain_until)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', ?)""",
                (
                    tenant_id,
                    project_id,
                    source_id,
                    version,
                    filename,
                    mime_type,
                    len(content),
                    digest,
                    object_key,
                    retention,
                ),
            )
            self._db.commit()
        except sqlite3.IntegrityError as exc:
            self._db.rollback()
            existing = self.get(
                tenant_id=tenant_id,
                project_id=project_id,
                source_id=source_id,
                version=version,
                include_inactive=True,
            )
            if (
                existing.sha256 == digest
                and existing.filename == filename
                and existing.mime_type == mime_type
                and existing.retain_until == retention
            ):
                return existing
            raise GovernedSourceFileError(
                "source version already exists with different bytes or policy"
            ) from exc
        return self.get(
            tenant_id=tenant_id,
            project_id=project_id,
            source_id=source_id,
            version=version,
        )

    def get(
        self,
        *,
        tenant_id: str,
        project_id: str,
        source_id: str,
        version: int,
        include_inactive: bool = False,
    ) -> SourceFileRecord:
        row = self._db.execute(
            """SELECT * FROM governed_source_files
               WHERE tenant_id=? AND project_id=? AND source_id=? AND version=?""",
            (tenant_id, project_id, source_id, version),
        ).fetchone()
        if row is None:
            raise GovernedSourceFileError("source file version not found")
        record = self._row(row)
        if not include_inactive and record.state != "active":
            raise GovernedSourceFileError("source file version is not active")
        return record

    def read_bytes(
        self,
        *,
        tenant_id: str,
        project_id: str,
        source_id: str,
        version: int,
    ) -> bytes:
        record = self.get(
            tenant_id=tenant_id,
            project_id=project_id,
            source_id=source_id,
            version=version,
        )
        try:
            content = self._path(record.object_key).read_bytes()
        except OSError as exc:
            raise GovernedSourceFileError("source file bytes are unavailable") from exc
        if len(content) != record.size_bytes or hashlib.sha256(content).hexdigest() != record.sha256:
            raise GovernedSourceFileError("source file integrity verification failed")
        return content

    def revoke(self, *, tenant_id: str, project_id: str, source_id: str, version: int) -> None:
        self._set_state(tenant_id, project_id, source_id, version, "revoked")

    def delete(self, *, tenant_id: str, project_id: str, source_id: str, version: int) -> None:
        record = self.get(
            tenant_id=tenant_id,
            project_id=project_id,
            source_id=source_id,
            version=version,
            include_inactive=True,
        )
        if record.retain_until is not None:
            retain_until = datetime.fromisoformat(record.retain_until)
            if retain_until > datetime.now(timezone.utc):
                raise GovernedSourceFileError("source file retention is active")
        self._set_state(tenant_id, project_id, source_id, version, "deleted")
        remaining = self._db.execute(
            "SELECT COUNT(*) AS count FROM governed_source_files WHERE sha256=? AND state!='deleted'",
            (record.sha256,),
        ).fetchone()
        if remaining is not None and int(remaining["count"]) == 0:
            try:
                self._path(record.object_key).unlink()
            except FileNotFoundError:
                pass
            except OSError as exc:
                raise GovernedSourceFileError("source file delete failed") from exc

    def list_versions(
        self, *, tenant_id: str, project_id: str, source_id: str
    ) -> tuple[SourceFileRecord, ...]:
        rows = self._db.execute(
            """SELECT * FROM governed_source_files
               WHERE tenant_id=? AND project_id=? AND source_id=? ORDER BY version DESC""",
            (tenant_id, project_id, source_id),
        ).fetchall()
        return tuple(self._row(row) for row in rows)

    def _set_state(
        self,
        tenant_id: str,
        project_id: str,
        source_id: str,
        version: int,
        state: str,
    ) -> None:
        self.get(
            tenant_id=tenant_id,
            project_id=project_id,
            source_id=source_id,
            version=version,
            include_inactive=True,
        )
        self._db.execute(
            """UPDATE governed_source_files SET state=?
               WHERE tenant_id=? AND project_id=? AND source_id=? AND version=?""",
            (state, tenant_id, project_id, source_id, version),
        )
        self._db.commit()

    def _put_immutable(self, path: Path, content: bytes, digest: str) -> None:
        if path.exists():
            try:
                existing = path.read_bytes()
            except OSError as exc:
                raise GovernedSourceFileError("existing source object is unreadable") from exc
            if hashlib.sha256(existing).hexdigest() != digest:
                raise GovernedSourceFileError(
                    "existing content-addressed object failed integrity"
                )
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix=".source-", dir=path.parent)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
        except OSError as exc:
            raise GovernedSourceFileError("source file persistence failed") from exc
        finally:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass

    def _path(self, object_key: str) -> Path:
        path = (self._objects / object_key).resolve()
        root = self._objects.resolve()
        if root not in path.parents:
            raise GovernedSourceFileError("object key escaped governed storage root")
        return path

    @staticmethod
    def _scope(value: str, name: str) -> None:
        if (
            not value
            or value != value.strip()
            or len(value) > 200
            or "/" in value
            or "\\" in value
            or "\x00" in value
        ):
            raise GovernedSourceFileError(f"{name} is invalid")

    @staticmethod
    def _filename(filename: str) -> None:
        if (
            not filename
            or filename != filename.strip()
            or len(filename) > 180
            or "/" in filename
            or "\\" in filename
            or "\x00" in filename
        ):
            raise GovernedSourceFileError("filename is invalid")

    @staticmethod
    def _row(row: sqlite3.Row) -> SourceFileRecord:
        return SourceFileRecord(
            tenant_id=str(row["tenant_id"]),
            project_id=str(row["project_id"]),
            source_id=str(row["source_id"]),
            version=int(row["version"]),
            filename=str(row["filename"]),
            mime_type=str(row["mime_type"]),
            size_bytes=int(row["size_bytes"]),
            sha256=str(row["sha256"]),
            object_key=str(row["object_key"]),
            state=str(row["state"]),
            retain_until=(
                None if row["retain_until"] is None else str(row["retain_until"])
            ),
        )


__all__ = ["GovernedSourceFileError", "GovernedSourceFileStore", "SourceFileRecord"]
