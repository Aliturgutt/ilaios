"""Tenant-scoped admission and immutable request binding for existing Web source.

Uploaded source archives are untrusted user inputs. They are validated by the
existing fail-closed ``WebSourceArchiveIngestor`` before this store records
principal/tenant ownership. Admission does not execute imported code and does not
grant revision, build, provider, deployment, or acceptance authority.
"""

from __future__ import annotations

import hashlib
import json
import secrets
import shutil
import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from services.web_source_ingestion import (
    WebSourceArchiveIngestor,
    WebSourceFile,
    WebSourceIngestionError,
    WebSourceSnapshot,
)

MAX_UNBOUND_WEB_SOURCE_ASSETS = 2
MAX_UNBOUND_WEB_SOURCE_BYTES = 300 * 1024 * 1024
UNBOUND_WEB_SOURCE_RETENTION = timedelta(hours=24)


class WebSourceAdmissionError(ValueError):
    """Existing source failed the tenant-scoped admission boundary."""


@dataclass(frozen=True, slots=True)
class WebSourceAssetRecord:
    asset_id: str
    principal_id: str
    tenant_id: str
    snapshot: WebSourceSnapshot
    size_bytes: int
    created_at: datetime

    def public_metadata(self) -> dict[str, object]:
        return {
            "asset_id": self.asset_id,
            "archive_sha256": self.snapshot.archive_sha256,
            "tree_sha256": self.snapshot.tree_sha256,
            "framework": self.snapshot.framework,
            "router": self.snapshot.router,
            "routes": list(self.snapshot.routes),
            "size_bytes": self.size_bytes,
            "file_count": len(self.snapshot.files),
        }


class WebSourceAdmissionStore:
    """Private durable ownership registry over immutable Web source snapshots."""

    def __init__(self, database_path: Path, artifact_root: Path) -> None:
        if database_path.is_symlink() or artifact_root.is_symlink():
            raise WebSourceAdmissionError("Web source admission paths must not be symlinks")
        self._database_path = database_path
        self._artifact_root = artifact_root
        self._ingestor = WebSourceArchiveIngestor(artifact_root)
        self._lock = threading.Lock()
        database_path.parent.mkdir(parents=True, exist_ok=True)
        artifact_root.mkdir(parents=True, exist_ok=True)
        if database_path.is_symlink() or artifact_root.is_symlink():
            raise WebSourceAdmissionError("Web source admission paths changed during initialization")
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS web_source_assets (
                    asset_id TEXT PRIMARY KEY,
                    principal_id TEXT NOT NULL,
                    tenant_id TEXT NOT NULL,
                    snapshot_id TEXT NOT NULL,
                    root_path TEXT NOT NULL,
                    archive_sha256 TEXT NOT NULL,
                    tree_sha256 TEXT NOT NULL,
                    framework TEXT NOT NULL,
                    router TEXT NOT NULL,
                    routes_json TEXT NOT NULL,
                    files_json TEXT NOT NULL,
                    size_bytes INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_web_source_owner
                    ON web_source_assets(tenant_id, principal_id, created_at);
                CREATE INDEX IF NOT EXISTS idx_web_source_snapshot
                    ON web_source_assets(snapshot_id);
                CREATE TABLE IF NOT EXISTS request_web_source (
                    request_id TEXT PRIMARY KEY,
                    asset_id TEXT NOT NULL REFERENCES web_source_assets(asset_id),
                    bound_at TEXT NOT NULL
                );
                """
            )
        with self._lock:
            self._prune_expired_unbound(datetime.now(timezone.utc))

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def put(
        self,
        *,
        archive: bytes,
        principal_id: str,
        tenant_id: str,
    ) -> WebSourceAssetRecord:
        _identity("principal_id", principal_id)
        _identity("tenant_id", tenant_id)
        with self._lock:
            self._prune_expired_unbound(datetime.now(timezone.utc))
            count, bytes_used = self._unbound_usage(
                principal_id=principal_id,
                tenant_id=tenant_id,
            )
            if count >= MAX_UNBOUND_WEB_SOURCE_ASSETS:
                raise WebSourceAdmissionError(
                    "too many unsubmitted Web source uploads; submit or discard the current source"
                )

            try:
                snapshot = self._ingestor.ingest_zip(archive)
            except WebSourceIngestionError as error:
                raise WebSourceAdmissionError(str(error)) from error
            size_bytes = sum(item.size_bytes for item in snapshot.files)
            if bytes_used + size_bytes > MAX_UNBOUND_WEB_SOURCE_BYTES:
                self._remove_snapshot_if_unreferenced(snapshot.snapshot_id, snapshot.root_path)
                raise WebSourceAdmissionError(
                    "unsubmitted Web source uploads exceed the tenant safety quota"
                )

            created_at = datetime.now(timezone.utc)
            asset_id = f"wsrc-{secrets.token_hex(12)}"
            files_json = json.dumps(
                [item.to_dict() for item in snapshot.files],
                sort_keys=True,
                separators=(",", ":"),
            )
            routes_json = json.dumps(list(snapshot.routes), separators=(",", ":"))
            try:
                with self._connect() as connection:
                    connection.execute(
                        "INSERT INTO web_source_assets VALUES "
                        "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (
                            asset_id,
                            principal_id,
                            tenant_id,
                            snapshot.snapshot_id,
                            snapshot.root_path,
                            snapshot.archive_sha256,
                            snapshot.tree_sha256,
                            snapshot.framework,
                            snapshot.router,
                            routes_json,
                            files_json,
                            size_bytes,
                            created_at.isoformat(),
                        ),
                    )
            except Exception:
                self._remove_snapshot_if_unreferenced(snapshot.snapshot_id, snapshot.root_path)
                raise

            return WebSourceAssetRecord(
                asset_id=asset_id,
                principal_id=principal_id,
                tenant_id=tenant_id,
                snapshot=snapshot,
                size_bytes=size_bytes,
                created_at=created_at,
            )

    def get_owned(
        self,
        asset_id: str,
        *,
        principal_id: str,
        tenant_id: str,
    ) -> WebSourceAssetRecord:
        _asset_id(asset_id)
        _identity("principal_id", principal_id)
        _identity("tenant_id", tenant_id)
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM web_source_assets WHERE asset_id = ?",
                (asset_id,),
            ).fetchone()
        if row is None:
            raise WebSourceAdmissionError("unknown Web source asset")
        record = _record(row)
        if record.principal_id != principal_id or record.tenant_id != tenant_id:
            raise WebSourceAdmissionError("Web source ownership mismatch")
        _verify_snapshot(record.snapshot)
        return record

    def bind_request(
        self,
        request_id: str,
        asset_id: str,
        *,
        principal_id: str,
        tenant_id: str,
    ) -> WebSourceAssetRecord:
        _identity("request_id", request_id)
        with self._lock:
            record = self.get_owned(
                asset_id,
                principal_id=principal_id,
                tenant_id=tenant_id,
            )
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                existing = connection.execute(
                    "SELECT asset_id FROM request_web_source WHERE request_id = ?",
                    (request_id,),
                ).fetchone()
                if existing is not None:
                    if str(existing["asset_id"]) != asset_id:
                        raise WebSourceAdmissionError(
                            "Web source is immutable after request binding"
                        )
                    return record
                connection.execute(
                    "INSERT INTO request_web_source (request_id, asset_id, bound_at) "
                    "VALUES (?, ?, ?)",
                    (request_id, asset_id, datetime.now(timezone.utc).isoformat()),
                )
            return record

    def for_request(self, request_id: str) -> WebSourceAssetRecord | None:
        _identity("request_id", request_id)
        with self._connect() as connection:
            row = connection.execute(
                "SELECT a.* FROM request_web_source r "
                "JOIN web_source_assets a ON a.asset_id = r.asset_id "
                "WHERE r.request_id = ?",
                (request_id,),
            ).fetchone()
        if row is None:
            return None
        record = _record(row)
        _verify_snapshot(record.snapshot)
        return record

    def discard_unbound(
        self,
        asset_id: str,
        *,
        principal_id: str,
        tenant_id: str,
    ) -> bool:
        with self._lock:
            record = self.get_owned(
                asset_id,
                principal_id=principal_id,
                tenant_id=tenant_id,
            )
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                bound = connection.execute(
                    "SELECT 1 FROM request_web_source WHERE asset_id = ? LIMIT 1",
                    (asset_id,),
                ).fetchone()
                if bound is not None:
                    raise WebSourceAdmissionError(
                        "bound Web source cannot be discarded through the upload boundary"
                    )
                connection.execute(
                    "DELETE FROM web_source_assets WHERE asset_id = ?",
                    (asset_id,),
                )
            self._remove_snapshot_if_unreferenced(
                record.snapshot.snapshot_id,
                record.snapshot.root_path,
            )
            return True

    def _unbound_usage(self, *, principal_id: str, tenant_id: str) -> tuple[int, int]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT COUNT(*), COALESCE(SUM(a.size_bytes), 0) "
                "FROM web_source_assets a "
                "LEFT JOIN request_web_source r ON r.asset_id = a.asset_id "
                "WHERE a.principal_id = ? AND a.tenant_id = ? AND r.asset_id IS NULL",
                (principal_id, tenant_id),
            ).fetchone()
        if row is None:
            return 0, 0
        return int(row[0]), int(row[1])

    def _prune_expired_unbound(self, now: datetime) -> None:
        cutoff = (now - UNBOUND_WEB_SOURCE_RETENTION).isoformat()
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT a.asset_id, a.snapshot_id, a.root_path FROM web_source_assets a "
                "LEFT JOIN request_web_source r ON r.asset_id = a.asset_id "
                "WHERE r.asset_id IS NULL AND a.created_at < ?",
                (cutoff,),
            ).fetchall()
            if not rows:
                return
            connection.execute("BEGIN IMMEDIATE")
            connection.executemany(
                "DELETE FROM web_source_assets WHERE asset_id = ?",
                ((str(row["asset_id"]),) for row in rows),
            )
        for row in rows:
            self._remove_snapshot_if_unreferenced(
                str(row["snapshot_id"]),
                str(row["root_path"]),
            )

    def _remove_snapshot_if_unreferenced(self, snapshot_id: str, root_path: str) -> None:
        with self._connect() as connection:
            referenced = connection.execute(
                "SELECT 1 FROM web_source_assets WHERE snapshot_id = ? LIMIT 1",
                (snapshot_id,),
            ).fetchone()
        if referenced is not None:
            return
        root = Path(root_path).resolve()
        allowed = (self._artifact_root.resolve() / "imported-source-snapshots").resolve()
        if root.parent != allowed or not root.name.startswith("ilaios-web-source-"):
            raise WebSourceAdmissionError("Web source cleanup path escaped its governed root")
        if root.is_symlink():
            raise WebSourceAdmissionError("Web source cleanup refuses a symlink snapshot")
        if root.exists():
            shutil.rmtree(root)


def _record(row: sqlite3.Row) -> WebSourceAssetRecord:
    try:
        routes_value = json.loads(str(row["routes_json"]))
        files_value = json.loads(str(row["files_json"]))
    except json.JSONDecodeError as error:
        raise WebSourceAdmissionError("stored Web source metadata is malformed") from error
    if not isinstance(routes_value, list) or not all(
        isinstance(item, str) for item in routes_value
    ):
        raise WebSourceAdmissionError("stored Web source routes are malformed")
    if not isinstance(files_value, list):
        raise WebSourceAdmissionError("stored Web source file inventory is malformed")
    files: list[WebSourceFile] = []
    for item in files_value:
        if not isinstance(item, dict):
            raise WebSourceAdmissionError("stored Web source file inventory is malformed")
        relative_path = item.get("relative_path")
        sha256 = item.get("sha256")
        size_bytes = item.get("size_bytes")
        if (
            not isinstance(relative_path, str)
            or not isinstance(sha256, str)
            or not isinstance(size_bytes, int)
            or isinstance(size_bytes, bool)
        ):
            raise WebSourceAdmissionError("stored Web source file inventory is malformed")
        files.append(WebSourceFile(relative_path, sha256, size_bytes))
    snapshot = WebSourceSnapshot(
        schema_version="ilaios.web.source-snapshot.v1",
        snapshot_id=str(row["snapshot_id"]),
        root_path=str(row["root_path"]),
        archive_sha256=str(row["archive_sha256"]),
        tree_sha256=str(row["tree_sha256"]),
        framework=str(row["framework"]),
        router=str(row["router"]),
        routes=tuple(routes_value),
        files=tuple(files),
    )
    created_at = datetime.fromisoformat(str(row["created_at"]))
    if created_at.tzinfo is None:
        raise WebSourceAdmissionError("stored Web source timestamp is not timezone-aware")
    return WebSourceAssetRecord(
        asset_id=str(row["asset_id"]),
        principal_id=str(row["principal_id"]),
        tenant_id=str(row["tenant_id"]),
        snapshot=snapshot,
        size_bytes=int(row["size_bytes"]),
        created_at=created_at,
    )


def _verify_snapshot(snapshot: WebSourceSnapshot) -> None:
    root = Path(snapshot.root_path).resolve()
    if root.is_symlink() or not root.is_dir():
        raise WebSourceAdmissionError("Web source snapshot is missing or unsafe")
    expected = {item.relative_path: item for item in snapshot.files}
    if len(expected) != len(snapshot.files):
        raise WebSourceAdmissionError("Web source snapshot inventory contains duplicate paths")
    digest = hashlib.sha256()
    seen: set[str] = set()
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise WebSourceAdmissionError("Web source snapshot contains a symlink")
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        record = expected.get(relative)
        if record is None:
            raise WebSourceAdmissionError("Web source snapshot contains an unrecorded file")
        content = path.read_bytes()
        observed = hashlib.sha256(content).hexdigest()
        if observed != record.sha256 or len(content) != record.size_bytes:
            raise WebSourceAdmissionError("Web source snapshot file integrity mismatch")
        seen.add(relative)
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(observed.encode("ascii"))
        digest.update(b"\0")
        digest.update(str(len(content)).encode("ascii"))
        digest.update(b"\n")
    if seen != set(expected):
        raise WebSourceAdmissionError("Web source snapshot is missing recorded files")
    if digest.hexdigest() != snapshot.tree_sha256:
        raise WebSourceAdmissionError("Web source snapshot tree integrity mismatch")


def _identity(label: str, value: str) -> None:
    if not value or value != value.strip() or len(value) > 160 or any(
        character in value for character in "\r\n\x00"
    ):
        raise WebSourceAdmissionError(f"{label} is invalid")


def _asset_id(value: str) -> None:
    _identity("asset_id", value)
    if not value.startswith("wsrc-"):
        raise WebSourceAdmissionError("Web source asset id is invalid")
