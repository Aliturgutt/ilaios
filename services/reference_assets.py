"""Governed local reference-asset storage shared by Desktop Web and Video Factory.

Reference assets never become part of prompt text. They are content addressed,
identity scoped, size bounded, magic-byte validated, and bound immutably to a
single authenticated execution request before a factory can consume them.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import sqlite3
import threading
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Sequence


class ReferenceAssetError(ValueError):
    """Raised when a reference asset violates the governed ingest contract."""


MAX_REFERENCE_ASSETS = 8
MAX_REFERENCE_ASSET_BYTES = 8 * 1024 * 1024
MAX_REFERENCE_TOTAL_BYTES = 24 * 1024 * 1024
ALLOWED_IMAGE_MEDIA_TYPES = frozenset({"image/png", "image/jpeg", "image/webp"})


@dataclass(frozen=True, slots=True)
class ReferenceAssetRecord:
    asset_id: str
    principal_id: str
    tenant_id: str
    original_name: str
    media_type: str
    sha256: str
    size_bytes: int
    storage_path: str
    created_at: str
    width: int | None = None
    height: int | None = None

    def public_metadata(self) -> dict[str, object]:
        return {
            "asset_id": self.asset_id,
            "original_name": self.original_name,
            "media_type": self.media_type,
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
            "width": self.width,
            "height": self.height,
        }


class ReferenceAssetStore:
    """Durable identity-scoped content-addressed store for user reference images."""

    def __init__(self, database_path: Path, object_root: Path) -> None:
        self._database_path = database_path
        self._object_root = object_root
        database_path.parent.mkdir(parents=True, exist_ok=True)
        object_root.mkdir(parents=True, exist_ok=True)
        self._migrate()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    def _migrate(self) -> None:
        with self._connect() as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS reference_assets ("
                "asset_id TEXT PRIMARY KEY, principal_id TEXT NOT NULL, "
                "tenant_id TEXT NOT NULL, original_name TEXT NOT NULL, "
                "media_type TEXT NOT NULL, sha256 TEXT NOT NULL, "
                "size_bytes INTEGER NOT NULL, storage_path TEXT NOT NULL, "
                "created_at TEXT NOT NULL, width INTEGER, height INTEGER, "
                "UNIQUE(principal_id, tenant_id, sha256))"
            )
            connection.execute(
                "CREATE TABLE IF NOT EXISTS execution_reference_assets ("
                "request_id TEXT NOT NULL, ordinal INTEGER NOT NULL, "
                "asset_id TEXT NOT NULL REFERENCES reference_assets(asset_id), "
                "job_id TEXT, bound_at TEXT NOT NULL, "
                "PRIMARY KEY(request_id, ordinal), UNIQUE(request_id, asset_id))"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_reference_assets_job "
                "ON execution_reference_assets(job_id)"
            )

    def ingest(
        self,
        *,
        principal_id: str,
        tenant_id: str,
        original_name: str,
        media_type: str,
        content: bytes,
        claimed_sha256: str | None = None,
    ) -> ReferenceAssetRecord:
        principal = _identity(principal_id, "principal_id")
        tenant = _identity(tenant_id, "tenant_id")
        name = _safe_filename(original_name)
        normalized_media_type = media_type.strip().lower()
        if normalized_media_type not in ALLOWED_IMAGE_MEDIA_TYPES:
            raise ReferenceAssetError("unsupported reference image media type")
        if not content or len(content) > MAX_REFERENCE_ASSET_BYTES:
            raise ReferenceAssetError("reference image size is outside allowed bounds")
        detected = _detect_image_media_type(content)
        if detected != normalized_media_type:
            raise ReferenceAssetError("reference image content does not match declared media type")
        digest = hashlib.sha256(content).hexdigest()
        if claimed_sha256 is not None and claimed_sha256 != digest:
            raise ReferenceAssetError("reference image digest changed during upload")
        width, height = _image_dimensions(content, detected)
        if width is None or height is None or width <= 0 or height <= 0:
            raise ReferenceAssetError("reference image dimensions could not be validated")
        if width > 16384 or height > 16384 or width * height > 80_000_000:
            raise ReferenceAssetError("reference image dimensions exceed safe bounds")

        asset_id = "ref-" + hashlib.sha256(
            f"{tenant}\0{principal}\0{digest}".encode("utf-8")
        ).hexdigest()[:32]
        object_path = self._object_root / digest[:2] / digest
        object_path.parent.mkdir(parents=True, exist_ok=True)
        if object_path.exists():
            existing = object_path.read_bytes()
            if hashlib.sha256(existing).hexdigest() != digest or existing != content:
                raise ReferenceAssetError("reference asset object store integrity failure")
        else:
            temporary = object_path.with_name(
                f".{object_path.name}.{os.getpid()}.{threading.get_ident()}.tmp"
            )
            temporary.write_bytes(content)
            try:
                os.chmod(temporary, 0o600)
            except OSError:
                pass
            os.replace(temporary, object_path)

        created_at = datetime.now(timezone.utc).isoformat()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "INSERT OR IGNORE INTO reference_assets "
                "(asset_id, principal_id, tenant_id, original_name, media_type, sha256, "
                "size_bytes, storage_path, created_at, width, height) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    asset_id,
                    principal,
                    tenant,
                    name,
                    normalized_media_type,
                    digest,
                    len(content),
                    str(object_path),
                    created_at,
                    width,
                    height,
                ),
            )
            row = connection.execute(
                "SELECT * FROM reference_assets WHERE asset_id=?", (asset_id,)
            ).fetchone()
        if row is None:
            raise ReferenceAssetError("reference image could not be persisted")
        record = _record(row)
        self._verify_record(record)
        return record

    def bind_request(
        self,
        request_id: str,
        asset_ids: Sequence[str],
        *,
        principal_id: str,
        tenant_id: str,
    ) -> tuple[ReferenceAssetRecord, ...]:
        request = _identifier(request_id, "request_id")
        principal = _identity(principal_id, "principal_id")
        tenant = _identity(tenant_id, "tenant_id")
        normalized_ids = tuple(_identifier(value, "asset_id") for value in asset_ids)
        if not normalized_ids:
            return ()
        if len(normalized_ids) > MAX_REFERENCE_ASSETS:
            raise ReferenceAssetError("too many reference images")
        if len(set(normalized_ids)) != len(normalized_ids):
            raise ReferenceAssetError("duplicate reference image identity")

        records = tuple(self.get(asset_id) for asset_id in normalized_ids)
        for record in records:
            if record.principal_id != principal or record.tenant_id != tenant:
                raise ReferenceAssetError("reference image is not owned by this session")
        if sum(record.size_bytes for record in records) > MAX_REFERENCE_TOTAL_BYTES:
            raise ReferenceAssetError("combined reference image size exceeds safe bounds")

        bound_at = datetime.now(timezone.utc).isoformat()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                "SELECT asset_id FROM execution_reference_assets "
                "WHERE request_id=? ORDER BY ordinal", (request,)
            ).fetchall()
            if existing:
                existing_ids = tuple(str(row["asset_id"]) for row in existing)
                if existing_ids != normalized_ids:
                    raise ReferenceAssetError(
                        "execution reference images are immutable after binding"
                    )
                return records
            for ordinal, asset_id in enumerate(normalized_ids):
                connection.execute(
                    "INSERT INTO execution_reference_assets "
                    "(request_id, ordinal, asset_id, job_id, bound_at) "
                    "VALUES (?, ?, ?, NULL, ?)",
                    (request, ordinal, asset_id, bound_at),
                )
        return records

    def attach_job(self, request_id: str, job_id: str) -> None:
        request = _identifier(request_id, "request_id")
        job = _identifier(job_id, "job_id")
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            rows = connection.execute(
                "SELECT DISTINCT job_id FROM execution_reference_assets WHERE request_id=?",
                (request,),
            ).fetchall()
            if not rows:
                return
            existing = {row["job_id"] for row in rows if row["job_id"] is not None}
            if existing and existing != {job}:
                raise ReferenceAssetError("reference image job binding is immutable")
            connection.execute(
                "UPDATE execution_reference_assets SET job_id=? "
                "WHERE request_id=? AND job_id IS NULL",
                (job, request),
            )

    def unbind_request(self, request_id: str) -> None:
        request = _identifier(request_id, "request_id")
        with self._connect() as connection:
            connection.execute(
                "DELETE FROM execution_reference_assets WHERE request_id=? AND job_id IS NULL",
                (request,),
            )

    def get(self, asset_id: str) -> ReferenceAssetRecord:
        asset = _identifier(asset_id, "asset_id")
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM reference_assets WHERE asset_id=?", (asset,)
            ).fetchone()
        if row is None:
            raise ReferenceAssetError("unknown reference image")
        record = _record(row)
        self._verify_record(record)
        return record

    def for_request(self, request_id: str) -> tuple[ReferenceAssetRecord, ...]:
        request = _identifier(request_id, "request_id")
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT a.* FROM execution_reference_assets b "
                "JOIN reference_assets a ON a.asset_id=b.asset_id "
                "WHERE b.request_id=? ORDER BY b.ordinal",
                (request,),
            ).fetchall()
        records = tuple(_record(row) for row in rows)
        for record in records:
            self._verify_record(record)
        return records

    def read_bytes(self, record: ReferenceAssetRecord) -> bytes:
        self._verify_record(record)
        return Path(record.storage_path).read_bytes()

    def data_url(self, record: ReferenceAssetRecord) -> str:
        encoded = base64.b64encode(self.read_bytes(record)).decode("ascii")
        return f"data:{record.media_type};base64,{encoded}"

    def manifest_for_request(self, request_id: str) -> tuple[dict[str, object], ...]:
        return tuple(record.public_metadata() for record in self.for_request(request_id))

    def _verify_record(self, record: ReferenceAssetRecord) -> None:
        path = Path(record.storage_path)
        try:
            body = path.read_bytes()
        except OSError as error:
            raise ReferenceAssetError("reference image object is unavailable") from error
        if len(body) != record.size_bytes:
            raise ReferenceAssetError("reference image object size integrity failure")
        if hashlib.sha256(body).hexdigest() != record.sha256:
            raise ReferenceAssetError("reference image object digest integrity failure")
        if _detect_image_media_type(body) != record.media_type:
            raise ReferenceAssetError("reference image object media integrity failure")


_store: ReferenceAssetStore | None = None
_current_request_id: ContextVar[str | None] = ContextVar(
    "ilaios_reference_asset_request_id", default=None
)


def configure_reference_asset_store(database_path: Path, object_root: Path) -> ReferenceAssetStore:
    global _store
    _store = ReferenceAssetStore(database_path, object_root)
    return _store


def get_reference_asset_store() -> ReferenceAssetStore:
    if _store is None:
        raise ReferenceAssetError("reference asset store is not configured")
    return _store


@contextmanager
def reference_request_context(request_id: str) -> Iterator[None]:
    request = _identifier(request_id, "request_id")
    token = _current_request_id.set(request)
    try:
        yield
    finally:
        _current_request_id.reset(token)


def current_reference_request_id() -> str | None:
    return _current_request_id.get()


def reference_asset_manifest_json(request_id: str) -> str:
    return json.dumps(
        get_reference_asset_store().manifest_for_request(request_id),
        sort_keys=True,
        separators=(",", ":"),
    )


def _record(row: sqlite3.Row) -> ReferenceAssetRecord:
    return ReferenceAssetRecord(
        asset_id=str(row["asset_id"]),
        principal_id=str(row["principal_id"]),
        tenant_id=str(row["tenant_id"]),
        original_name=str(row["original_name"]),
        media_type=str(row["media_type"]),
        sha256=str(row["sha256"]),
        size_bytes=int(row["size_bytes"]),
        storage_path=str(row["storage_path"]),
        created_at=str(row["created_at"]),
        width=int(row["width"]) if row["width"] is not None else None,
        height=int(row["height"]) if row["height"] is not None else None,
    )


def _identifier(value: str, name: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ReferenceAssetError(f"{name} must be non-blank normalized text")
    if len(value) > 256 or any(character in value for character in ("\x00", "\r", "\n")):
        raise ReferenceAssetError(f"{name} is malformed")
    return value


def _identity(value: str, name: str) -> str:
    normalized = _identifier(value, name)
    if len(normalized) > 512:
        raise ReferenceAssetError(f"{name} exceeds safe bounds")
    return normalized


def _safe_filename(value: str) -> str:
    if not isinstance(value, str):
        raise ReferenceAssetError("reference image filename must be text")
    normalized = Path(value.strip()).name
    if not normalized or normalized in {".", ".."} or len(normalized) > 255:
        raise ReferenceAssetError("reference image filename is invalid")
    if any(character in normalized for character in ("\x00", "\r", "\n")):
        raise ReferenceAssetError("reference image filename is invalid")
    return normalized


def _detect_image_media_type(content: bytes) -> str:
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if content.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return "image/webp"
    raise ReferenceAssetError("reference image has an unsupported or invalid signature")


def _image_dimensions(content: bytes, media_type: str) -> tuple[int | None, int | None]:
    if media_type == "image/png":
        if len(content) < 24 or content[12:16] != b"IHDR":
            return None, None
        return int.from_bytes(content[16:20], "big"), int.from_bytes(content[20:24], "big")
    if media_type == "image/jpeg":
        return _jpeg_dimensions(content)
    if media_type == "image/webp":
        return _webp_dimensions(content)
    return None, None


def _jpeg_dimensions(content: bytes) -> tuple[int | None, int | None]:
    offset = 2
    sof_markers = {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}
    while offset + 4 <= len(content):
        if content[offset] != 0xFF:
            offset += 1
            continue
        while offset < len(content) and content[offset] == 0xFF:
            offset += 1
        if offset >= len(content):
            break
        marker = content[offset]
        offset += 1
        if marker in {0xD8, 0xD9}:
            continue
        if offset + 2 > len(content):
            break
        segment_length = int.from_bytes(content[offset : offset + 2], "big")
        if segment_length < 2 or offset + segment_length > len(content):
            break
        if marker in sof_markers and segment_length >= 7:
            height = int.from_bytes(content[offset + 3 : offset + 5], "big")
            width = int.from_bytes(content[offset + 5 : offset + 7], "big")
            return width, height
        offset += segment_length
    return None, None


def _webp_dimensions(content: bytes) -> tuple[int | None, int | None]:
    if len(content) < 30:
        return None, None
    chunk = content[12:16]
    if chunk == b"VP8X":
        width = 1 + int.from_bytes(content[24:27], "little")
        height = 1 + int.from_bytes(content[27:30], "little")
        return width, height
    if chunk == b"VP8 " and content[23:26] == b"\x9d\x01\x2a":
        width = int.from_bytes(content[26:28], "little") & 0x3FFF
        height = int.from_bytes(content[28:30], "little") & 0x3FFF
        return width, height
    if chunk == b"VP8L" and len(content) >= 25 and content[20] == 0x2F:
        b1, b2, b3, b4 = content[21:25]
        width = 1 + b1 + ((b2 & 0x3F) << 8)
        height = 1 + (b2 >> 6) + (b3 << 2) + ((b4 & 0x0F) << 10)
        return width, height
    return None, None
