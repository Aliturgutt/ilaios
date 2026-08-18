"""Admission and retention controls for private reference-image uploads.

The durable ReferenceAssetStore owns immutable records and request binding. This
adapter hardens the upload boundary against storage exhaustion, garbage-collects
abandoned uploads, and releases raw image bytes after successful conditioning
while retaining immutable request/digest metadata.
"""

from __future__ import annotations

import hashlib
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .reference_assets import (
    ReferenceAssetError,
    ReferenceAssetRecord,
    ReferenceAssetRole,
    ReferenceAssetStore,
)

MAX_UNBOUND_REFERENCE_ASSETS = 40
MAX_UNBOUND_REFERENCE_BYTES = 200 * 1024 * 1024
UNBOUND_REFERENCE_RETENTION = timedelta(hours=24)


class ReferenceAssetAdmissionStore(ReferenceAssetStore):
    """Reference store with bounded uploads and request-aware raw-byte retention."""

    def __init__(self, database_path: Path, blob_root: Path) -> None:
        if database_path.is_symlink() or blob_root.is_symlink():
            raise ReferenceAssetError("reference storage paths must not be symbolic links")
        super().__init__(database_path, blob_root)
        if database_path.is_symlink() or blob_root.is_symlink() or not blob_root.is_dir():
            raise ReferenceAssetError("reference storage paths changed during initialization")
        self._admission_lock = threading.Lock()
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS released_reference_requests (
                    request_id TEXT PRIMARY KEY,
                    released_at TEXT NOT NULL
                )
                """
            )
        with self._admission_lock:
            self._prune_expired_unbound(datetime.now(timezone.utc))

    def put(
        self,
        *,
        content: bytes,
        claimed_mime_type: str,
        original_filename: str,
        role: ReferenceAssetRole,
        instruction: str | None,
        principal_id: str,
        tenant_id: str,
    ) -> ReferenceAssetRecord:
        with self._admission_lock:
            self._prune_expired_unbound(datetime.now(timezone.utc))
            count, size_bytes = self._unbound_usage(
                principal_id=principal_id,
                tenant_id=tenant_id,
            )
            if count >= MAX_UNBOUND_REFERENCE_ASSETS:
                raise ReferenceAssetError(
                    "too many unbound reference images; submit or discard the current batch"
                )
            if size_bytes + len(content) > MAX_UNBOUND_REFERENCE_BYTES:
                raise ReferenceAssetError(
                    "unbound reference images exceed the 200 MiB safety quota"
                )

            digest = hashlib.sha256(content).hexdigest()
            blob_path = self._blob_root / digest
            if blob_path.is_symlink():
                raise ReferenceAssetError("reference blob path is a symbolic link")
            existed = blob_path.exists()
            if existed and not blob_path.is_file():
                raise ReferenceAssetError("reference blob path is not a regular file")
            try:
                return super().put(
                    content=content,
                    claimed_mime_type=claimed_mime_type,
                    original_filename=original_filename,
                    role=role,
                    instruction=instruction,
                    principal_id=principal_id,
                    tenant_id=tenant_id,
                )
            except Exception:
                # If the blob was created but the durable metadata insert failed,
                # remove the newly orphaned file. Existing shared blobs are retained.
                if not existed and not blob_path.is_symlink():
                    try:
                        blob_path.unlink(missing_ok=True)
                    except OSError:
                        pass
                raise

    def bind_request(
        self,
        request_id: str,
        asset_ids: tuple[str, ...],
        *,
        principal_id: str,
        tenant_id: str,
    ) -> tuple[ReferenceAssetRecord, ...]:
        # Binding and release share one lock so a raw blob cannot disappear between
        # availability validation and immutable request binding.
        with self._admission_lock:
            records = tuple(
                self.get_owned(
                    asset_id,
                    principal_id=principal_id,
                    tenant_id=tenant_id,
                )
                for asset_id in asset_ids
            )
            for record in records:
                path = self._blob_root / record.sha256
                if path.is_symlink() or not path.is_file():
                    raise ReferenceAssetError(
                        "reference image raw bytes are no longer available for a new request"
                    )
            return super().bind_request(
                request_id,
                asset_ids,
                principal_id=principal_id,
                tenant_id=tenant_id,
            )

    def discard_unbound(
        self,
        asset_ids: tuple[str, ...],
        *,
        principal_id: str,
        tenant_id: str,
    ) -> int:
        """Delete only caller-owned assets that have not been bound to a request."""
        if len(asset_ids) > MAX_UNBOUND_REFERENCE_ASSETS:
            raise ReferenceAssetError("too many reference assets requested for discard")
        if len(set(asset_ids)) != len(asset_ids):
            raise ReferenceAssetError("duplicate reference asset ids are not allowed")
        if not asset_ids:
            return 0

        with self._admission_lock:
            records = tuple(
                self.get_owned(
                    asset_id,
                    principal_id=principal_id,
                    tenant_id=tenant_id,
                )
                for asset_id in asset_ids
            )
            placeholders = ",".join("?" for _ in asset_ids)
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                bound = connection.execute(
                    "SELECT asset_id FROM request_reference_assets "
                    f"WHERE asset_id IN ({placeholders}) LIMIT 1",
                    asset_ids,
                ).fetchone()
                if bound is not None:
                    raise ReferenceAssetError(
                        "bound reference assets cannot be discarded through the upload boundary"
                    )
                connection.execute(
                    f"DELETE FROM reference_assets WHERE asset_id IN ({placeholders})",
                    asset_ids,
                )
            self._remove_unreferenced_blobs(
                tuple(record.sha256 for record in records)
            )
        return len(records)

    def release_request_blobs(self, request_id: str) -> int:
        """Release raw bytes for one successfully conditioned request.

        The request-to-asset binding and digest metadata remain durable. A blob is
        deleted only when no unbound asset and no unreleased request still depends
        on any record carrying that digest.
        """
        if (
            not request_id
            or request_id != request_id.strip()
            or len(request_id) > 128
            or any(
                character
                not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
                for character in request_id
            )
        ):
            raise ReferenceAssetError("invalid request_id")

        with self._admission_lock:
            with self._connect() as connection:
                rows = connection.execute(
                    "SELECT DISTINCT a.sha256 FROM request_reference_assets r "
                    "JOIN reference_assets a ON a.asset_id = r.asset_id "
                    "WHERE r.request_id = ?",
                    (request_id,),
                ).fetchall()
                if not rows:
                    return 0
                now = datetime.now(timezone.utc).isoformat()
                connection.execute("BEGIN IMMEDIATE")
                connection.execute(
                    "INSERT INTO released_reference_requests (request_id, released_at) "
                    "VALUES (?, ?) ON CONFLICT(request_id) DO NOTHING",
                    (request_id, now),
                )
            removed = 0
            for row in rows:
                digest = str(row["sha256"])
                if self._digest_has_active_consumer(digest):
                    continue
                path = self._blob_root / digest
                if path.is_symlink():
                    raise ReferenceAssetError("released reference blob path is a symbolic link")
                existed = path.is_file()
                try:
                    path.unlink(missing_ok=True)
                except OSError as error:
                    raise ReferenceAssetError(
                        "released reference image bytes could not be removed"
                    ) from error
                if existed:
                    removed += 1
            return removed

    def _digest_has_active_consumer(self, digest: str) -> bool:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT 1 FROM reference_assets a "
                "LEFT JOIN request_reference_assets r ON r.asset_id = a.asset_id "
                "LEFT JOIN released_reference_requests x ON x.request_id = r.request_id "
                "WHERE a.sha256 = ? "
                "AND (r.asset_id IS NULL OR x.request_id IS NULL) LIMIT 1",
                (digest,),
            ).fetchone()
        return row is not None

    def _unbound_usage(self, *, principal_id: str, tenant_id: str) -> tuple[int, int]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT COUNT(*), COALESCE(SUM(a.size_bytes), 0) "
                "FROM reference_assets a "
                "LEFT JOIN request_reference_assets r ON r.asset_id = a.asset_id "
                "WHERE a.principal_id = ? AND a.tenant_id = ? AND r.asset_id IS NULL",
                (principal_id, tenant_id),
            ).fetchone()
        if row is None:
            return 0, 0
        return int(row[0]), int(row[1])

    def _prune_expired_unbound(self, now: datetime) -> None:
        cutoff = (now - UNBOUND_REFERENCE_RETENTION).isoformat()
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT a.asset_id, a.sha256 FROM reference_assets a "
                "LEFT JOIN request_reference_assets r ON r.asset_id = a.asset_id "
                "WHERE r.asset_id IS NULL AND a.created_at < ?",
                (cutoff,),
            ).fetchall()
            if not rows:
                return
            connection.execute("BEGIN IMMEDIATE")
            connection.executemany(
                "DELETE FROM reference_assets WHERE asset_id = ?",
                ((str(row["asset_id"]),) for row in rows),
            )
        self._remove_unreferenced_blobs(tuple(str(row["sha256"]) for row in rows))

    def _remove_unreferenced_blobs(self, digests: tuple[str, ...]) -> None:
        for digest in set(digests):
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                referenced = connection.execute(
                    "SELECT 1 FROM reference_assets WHERE sha256 = ? LIMIT 1",
                    (digest,),
                ).fetchone()
                if referenced is not None:
                    continue
                path = self._blob_root / digest
                if path.is_symlink():
                    raise ReferenceAssetError("orphan reference blob path is a symbolic link")
                try:
                    path.unlink(missing_ok=True)
                except OSError as error:
                    raise ReferenceAssetError(
                        "abandoned reference image bytes could not be removed"
                    ) from error
