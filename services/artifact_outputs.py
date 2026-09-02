"""Governed Files/Outputs persistence for finished-product artifacts.

This is the concrete repository-local implementation of the canonical
ArtifactRecord boundary. It is not a second execution, policy, or evidence
authority. Artifact bytes are immutable and content-addressed; metadata is
scoped by tenant/project/job and persisted in SQLite.
"""

from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


class ArtifactOutputError(RuntimeError):
    """Raised when a governed output artifact cannot be safely persisted/read."""


@dataclass(frozen=True, slots=True)
class ArtifactRecord:
    artifact_id: str
    version_id: str
    tenant_id: str
    project_id: str
    job_id: str
    artifact_type: str
    mime_type: str
    content_hash: str
    size: int
    storage_ref: str
    created_at: str


class GovernedArtifactOutputStore:
    """Immutable content-addressed output bytes plus scoped artifact metadata."""

    def __init__(self, root: Path, database_path: Path) -> None:
        self._root = root
        self._database_path = database_path
        self._objects = root / "objects"
        self._objects.mkdir(parents=True, exist_ok=True)
        database_path.parent.mkdir(parents=True, exist_ok=True)
        self._migrate()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def _migrate(self) -> None:
        with self._connect() as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS artifact_outputs ("
                "artifact_id TEXT NOT NULL, version_id TEXT NOT NULL, "
                "tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, job_id TEXT NOT NULL, "
                "artifact_type TEXT NOT NULL, mime_type TEXT NOT NULL, "
                "content_hash TEXT NOT NULL, size INTEGER NOT NULL, storage_ref TEXT NOT NULL, "
                "created_at TEXT NOT NULL, PRIMARY KEY (artifact_id, version_id))"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_artifact_outputs_scope "
                "ON artifact_outputs(tenant_id, project_id, job_id)"
            )

    def put(
        self,
        *,
        artifact_id: str,
        version_id: str,
        tenant_id: str,
        project_id: str,
        job_id: str,
        artifact_type: str,
        mime_type: str,
        content: bytes,
        now: datetime | None = None,
    ) -> ArtifactRecord:
        for label, value in (
            ("artifact_id", artifact_id),
            ("version_id", version_id),
            ("tenant_id", tenant_id),
            ("project_id", project_id),
            ("job_id", job_id),
            ("artifact_type", artifact_type),
            ("mime_type", mime_type),
        ):
            if not value.strip():
                raise ArtifactOutputError(f"{label} is required")
        if not content:
            raise ArtifactOutputError("artifact content is empty")

        digest = hashlib.sha256(content).hexdigest()
        object_path = self._objects / digest[:2] / digest
        object_path.parent.mkdir(parents=True, exist_ok=True)
        if object_path.exists():
            if object_path.read_bytes() != content:
                raise ArtifactOutputError("content-addressed object integrity conflict")
        else:
            temporary = object_path.with_suffix(".tmp")
            temporary.write_bytes(content)
            temporary.replace(object_path)

        created_at = (now or datetime.now(timezone.utc)).astimezone(timezone.utc).isoformat()
        storage_ref = f"object://sha256/{digest}"
        with self._connect() as connection:
            existing = connection.execute(
                "SELECT content_hash FROM artifact_outputs WHERE artifact_id = ? AND version_id = ?",
                (artifact_id, version_id),
            ).fetchone()
            if existing is not None:
                if str(existing["content_hash"]) != digest:
                    raise ArtifactOutputError("artifact version is immutable")
            else:
                connection.execute(
                    "INSERT INTO artifact_outputs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        artifact_id,
                        version_id,
                        tenant_id,
                        project_id,
                        job_id,
                        artifact_type,
                        mime_type,
                        digest,
                        len(content),
                        storage_ref,
                        created_at,
                    ),
                )
        return ArtifactRecord(
            artifact_id=artifact_id,
            version_id=version_id,
            tenant_id=tenant_id,
            project_id=project_id,
            job_id=job_id,
            artifact_type=artifact_type,
            mime_type=mime_type,
            content_hash=digest,
            size=len(content),
            storage_ref=storage_ref,
            created_at=created_at,
        )

    def read(
        self,
        *,
        artifact_id: str,
        version_id: str,
        tenant_id: str,
        project_id: str,
    ) -> bytes:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM artifact_outputs WHERE artifact_id = ? AND version_id = ?",
                (artifact_id, version_id),
            ).fetchone()
        if row is None:
            raise ArtifactOutputError("artifact version not found")
        if str(row["tenant_id"]) != tenant_id or str(row["project_id"]) != project_id:
            raise ArtifactOutputError("artifact scope mismatch")
        digest = str(row["content_hash"])
        object_path = self._objects / digest[:2] / digest
        if not object_path.is_file():
            raise ArtifactOutputError("artifact object missing")
        content = object_path.read_bytes()
        if hashlib.sha256(content).hexdigest() != digest or len(content) != int(row["size"]):
            raise ArtifactOutputError("artifact integrity check failed")
        return content
