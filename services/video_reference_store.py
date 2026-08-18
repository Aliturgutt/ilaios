"""Durable authenticated Video Factory reference-image draft bindings.

Desktop uploads are private, digest-addressed assets. A draft is owned by one
principal/tenant and can be bound exactly once to one execution request. The
provider runtime resolves only request-bound assets and stages them through the
explicit egress authority immediately before generation.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from src.video_automation.reference_asset_staging import (
    LocalReferenceAssetStore,
    PrivateReferenceAsset,
    ReferenceAssetError,
    ReferenceImageStager,
    stage_reference_pool,
)
from src.video_automation.reference_images import (
    MAX_REFERENCE_UPLOAD_BYTES,
    MAX_USER_REFERENCE_IMAGES,
    ReferenceImageRole,
    VideoReferenceImage,
)


class VideoReferenceStoreError(ValueError):
    """Raised when an authenticated reference draft violates ownership/bounds."""


@dataclass(frozen=True, slots=True)
class StoredVideoReference:
    draft_id: str
    asset_id: str
    sha256_digest: str
    media_type: str
    size_bytes: int
    role: ReferenceImageRole

    def to_json(self) -> dict[str, object]:
        return {
            "draft_id": self.draft_id,
            "asset_id": self.asset_id,
            "sha256": self.sha256_digest,
            "media_type": self.media_type,
            "size_bytes": self.size_bytes,
            "role": self.role.value,
        }


class DesktopVideoReferenceStore:
    """Persist private reference drafts and execution bindings fail-closed."""

    def __init__(
        self,
        database_path: Path,
        asset_root: Path,
        *,
        stager: ReferenceImageStager,
    ) -> None:
        self._database_path = database_path
        self._assets = LocalReferenceAssetStore(asset_root)
        self._stager = stager
        database_path.parent.mkdir(parents=True, exist_ok=True)
        self._migrate()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def _migrate(self) -> None:
        with self._connect() as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS video_reference_drafts ("
                "draft_id TEXT PRIMARY KEY, principal_id TEXT NOT NULL, "
                "tenant_id TEXT NOT NULL, request_id TEXT UNIQUE)"
            )
            connection.execute(
                "CREATE TABLE IF NOT EXISTS video_reference_assets ("
                "draft_id TEXT NOT NULL, asset_id TEXT NOT NULL, "
                "sha256_digest TEXT NOT NULL, media_type TEXT NOT NULL, "
                "size_bytes INTEGER NOT NULL, storage_path TEXT NOT NULL, "
                "role TEXT NOT NULL, sequence INTEGER NOT NULL, "
                "PRIMARY KEY(draft_id, asset_id), UNIQUE(draft_id, sha256_digest), "
                "UNIQUE(draft_id, sequence))"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_video_reference_request "
                "ON video_reference_drafts(request_id)"
            )

    def add_upload(
        self,
        *,
        draft_id: str,
        principal_id: str,
        tenant_id: str,
        content: bytes,
        media_type: str,
        role: ReferenceImageRole,
    ) -> StoredVideoReference:
        _identifier("draft_id", draft_id)
        _identity("principal_id", principal_id)
        _identity("tenant_id", tenant_id)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            draft = connection.execute(
                "SELECT principal_id, tenant_id, request_id FROM video_reference_drafts "
                "WHERE draft_id = ?",
                (draft_id,),
            ).fetchone()
            if draft is None:
                connection.execute(
                    "INSERT INTO video_reference_drafts "
                    "(draft_id, principal_id, tenant_id, request_id) VALUES (?, ?, ?, NULL)",
                    (draft_id, principal_id, tenant_id),
                )
            else:
                if (
                    str(draft["principal_id"]) != principal_id
                    or str(draft["tenant_id"]) != tenant_id
                ):
                    raise VideoReferenceStoreError(
                        "reference draft belongs to another authenticated identity"
                    )
                if draft["request_id"] is not None:
                    raise VideoReferenceStoreError(
                        "reference draft is already bound to an execution"
                    )
            rows = connection.execute(
                "SELECT size_bytes FROM video_reference_assets WHERE draft_id = ?",
                (draft_id,),
            ).fetchall()
            if len(rows) >= MAX_USER_REFERENCE_IMAGES:
                raise VideoReferenceStoreError(
                    f"at most {MAX_USER_REFERENCE_IMAGES} reference images are allowed"
                )
            if sum(int(row["size_bytes"]) for row in rows) + len(content) > MAX_REFERENCE_UPLOAD_BYTES:
                raise VideoReferenceStoreError("reference image pool exceeds total upload bound")

            try:
                asset = self._assets.put(
                    tenant_id=tenant_id,
                    project_id=draft_id,
                    content=content,
                    media_type=media_type,
                    role=role,
                )
            except ReferenceAssetError as exc:
                raise VideoReferenceStoreError(str(exc)) from exc
            duplicate = connection.execute(
                "SELECT asset_id, sha256_digest, media_type, size_bytes, role "
                "FROM video_reference_assets WHERE draft_id = ? AND sha256_digest = ?",
                (draft_id, asset.sha256_digest),
            ).fetchone()
            if duplicate is not None:
                return _stored_from_row(draft_id, duplicate)
            sequence = len(rows) + 1
            connection.execute(
                "INSERT INTO video_reference_assets "
                "(draft_id, asset_id, sha256_digest, media_type, size_bytes, "
                "storage_path, role, sequence) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    draft_id,
                    asset.asset_id,
                    asset.sha256_digest,
                    asset.media_type,
                    asset.size_bytes,
                    str(asset.storage_path),
                    asset.role.value,
                    sequence,
                ),
            )
            return StoredVideoReference(
                draft_id=draft_id,
                asset_id=asset.asset_id,
                sha256_digest=asset.sha256_digest,
                media_type=asset.media_type,
                size_bytes=asset.size_bytes,
                role=asset.role,
            )

    def bind_draft(
        self,
        *,
        draft_id: str,
        request_id: str,
        principal_id: str,
        tenant_id: str,
    ) -> int:
        _identifier("draft_id", draft_id)
        _identifier("request_id", request_id)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            draft = connection.execute(
                "SELECT principal_id, tenant_id, request_id FROM video_reference_drafts "
                "WHERE draft_id = ?",
                (draft_id,),
            ).fetchone()
            if draft is None:
                raise VideoReferenceStoreError("unknown reference draft")
            if (
                str(draft["principal_id"]) != principal_id
                or str(draft["tenant_id"]) != tenant_id
            ):
                raise VideoReferenceStoreError(
                    "reference draft belongs to another authenticated identity"
                )
            existing_request = draft["request_id"]
            if existing_request is not None and str(existing_request) != request_id:
                raise VideoReferenceStoreError(
                    "reference draft is already bound to another execution"
                )
            count = int(
                connection.execute(
                    "SELECT COUNT(*) FROM video_reference_assets WHERE draft_id = ?",
                    (draft_id,),
                ).fetchone()[0]
            )
            if count < 1:
                raise VideoReferenceStoreError("reference draft contains no images")
            collision = connection.execute(
                "SELECT draft_id FROM video_reference_drafts WHERE request_id = ? "
                "AND draft_id != ?",
                (request_id, draft_id),
            ).fetchone()
            if collision is not None:
                raise VideoReferenceStoreError(
                    "execution request already has a different reference draft"
                )
            connection.execute(
                "UPDATE video_reference_drafts SET request_id = ? WHERE draft_id = ?",
                (request_id, draft_id),
            )
            return count

    def resolve_for_request(
        self,
        request_id: str,
        *,
        now_epoch_s: int,
        minimum_ttl_seconds: int = 20 * 60,
    ) -> tuple[VideoReferenceImage, ...]:
        _identifier("request_id", request_id)
        with self._connect() as connection:
            draft = connection.execute(
                "SELECT draft_id, principal_id, tenant_id FROM video_reference_drafts "
                "WHERE request_id = ?",
                (request_id,),
            ).fetchone()
            if draft is None:
                return ()
            rows = connection.execute(
                "SELECT * FROM video_reference_assets WHERE draft_id = ? "
                "ORDER BY sequence",
                (str(draft["draft_id"]),),
            ).fetchall()
        assets = tuple(
            PrivateReferenceAsset(
                asset_id=str(row["asset_id"]),
                tenant_id=str(draft["tenant_id"]),
                project_id=str(draft["draft_id"]),
                sha256_digest=str(row["sha256_digest"]),
                media_type=str(row["media_type"]),
                size_bytes=int(row["size_bytes"]),
                storage_path=Path(str(row["storage_path"])),
                role=ReferenceImageRole(str(row["role"])),
            )
            for row in rows
        )
        for asset in assets:
            if not asset.storage_path.is_file():
                raise VideoReferenceStoreError("private reference asset is missing")
            content = asset.storage_path.read_bytes()
            if len(content) != asset.size_bytes:
                raise VideoReferenceStoreError("private reference asset size changed")
            from hashlib import sha256

            if sha256(content).hexdigest() != asset.sha256_digest:
                raise VideoReferenceStoreError("private reference asset digest changed")
        try:
            return stage_reference_pool(
                assets,
                stager=self._stager,
                now_epoch_s=now_epoch_s,
                minimum_ttl_seconds=minimum_ttl_seconds,
            )
        except ReferenceAssetError as exc:
            raise VideoReferenceStoreError(str(exc)) from exc

    def draft_count(
        self, *, draft_id: str, principal_id: str, tenant_id: str
    ) -> int:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT principal_id, tenant_id FROM video_reference_drafts WHERE draft_id = ?",
                (draft_id,),
            ).fetchone()
            if row is None:
                return 0
            if str(row["principal_id"]) != principal_id or str(row["tenant_id"]) != tenant_id:
                raise VideoReferenceStoreError(
                    "reference draft belongs to another authenticated identity"
                )
            return int(
                connection.execute(
                    "SELECT COUNT(*) FROM video_reference_assets WHERE draft_id = ?",
                    (draft_id,),
                ).fetchone()[0]
            )


def _stored_from_row(draft_id: str, row: sqlite3.Row) -> StoredVideoReference:
    return StoredVideoReference(
        draft_id=draft_id,
        asset_id=str(row["asset_id"]),
        sha256_digest=str(row["sha256_digest"]),
        media_type=str(row["media_type"]),
        size_bytes=int(row["size_bytes"]),
        role=ReferenceImageRole(str(row["role"])),
    )


def _identifier(name: str, value: str) -> None:
    if not value or value != value.strip() or len(value) > 128:
        raise VideoReferenceStoreError(f"{name} must be normalized bounded text")
    allowed = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
    if any(character not in allowed for character in value):
        raise VideoReferenceStoreError(f"{name} contains unsafe characters")


def _identity(name: str, value: str) -> None:
    if not value or value != value.strip() or len(value) > 512:
        raise VideoReferenceStoreError(f"{name} must be normalized bounded text")
