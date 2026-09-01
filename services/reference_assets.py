"""Tenant-scoped reference-image storage for governed factory inputs.

Reference assets are user inputs, not accepted execution evidence. They therefore
live in a dedicated private content-addressed store instead of the append-only
EvidenceStore. The store validates bytes server-side, owns tenant/principal
binding, and exposes only immutable records to runtimes.
"""

from __future__ import annotations

import hashlib
import secrets
import sqlite3
import struct
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

MAX_REFERENCE_ASSETS = 20
MAX_REFERENCE_ASSET_BYTES = 10 * 1024 * 1024
MAX_REFERENCE_TOTAL_BYTES = 100 * 1024 * 1024
MAX_REFERENCE_DIMENSION = 8192
MAX_REFERENCE_PIXELS = 40_000_000
MAX_REFERENCE_INSTRUCTION_CHARS = 500
MAX_REFERENCE_FILENAME_CHARS = 180


class ReferenceAssetError(ValueError):
    """Raised when a reference asset cannot cross the governed input boundary."""


class ReferenceAssetRole(str, Enum):
    STYLE = "style"
    SUBJECT = "subject"
    PRODUCT = "product"
    ENVIRONMENT = "environment"
    LOGO = "logo"
    STORYBOARD = "storyboard"
    FIRST_FRAME = "first_frame"
    LAST_FRAME = "last_frame"
    OTHER = "other"


@dataclass(frozen=True, slots=True)
class ReferenceAssetRecord:
    asset_id: str
    principal_id: str
    tenant_id: str
    sha256: str
    mime_type: str
    original_filename: str
    width: int
    height: int
    size_bytes: int
    role: ReferenceAssetRole
    instruction: str | None
    created_at: datetime


class ReferenceAssetStore:
    """Private durable asset store with strict ownership and request binding."""

    def __init__(self, database_path: Path, blob_root: Path) -> None:
        self._database_path = database_path
        self._blob_root = blob_root
        database_path.parent.mkdir(parents=True, exist_ok=True)
        blob_root.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS reference_assets (
                    asset_id TEXT PRIMARY KEY,
                    principal_id TEXT NOT NULL,
                    tenant_id TEXT NOT NULL,
                    sha256 TEXT NOT NULL,
                    mime_type TEXT NOT NULL,
                    original_filename TEXT NOT NULL,
                    width INTEGER NOT NULL,
                    height INTEGER NOT NULL,
                    size_bytes INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    instruction TEXT,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_reference_assets_owner
                    ON reference_assets(tenant_id, principal_id, created_at);
                CREATE TABLE IF NOT EXISTS request_reference_assets (
                    request_id TEXT NOT NULL,
                    asset_id TEXT NOT NULL REFERENCES reference_assets(asset_id),
                    ordinal INTEGER NOT NULL,
                    PRIMARY KEY (request_id, asset_id),
                    UNIQUE (request_id, ordinal)
                );
                """
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

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
        _owner("principal_id", principal_id)
        _owner("tenant_id", tenant_id)
        filename = _filename(original_filename)
        normalized_instruction = _instruction(instruction)
        if not isinstance(role, ReferenceAssetRole):
            raise ReferenceAssetError("reference asset role is invalid")
        if not content:
            raise ReferenceAssetError("reference image must not be empty")
        if len(content) > MAX_REFERENCE_ASSET_BYTES:
            raise ReferenceAssetError("reference image exceeds the 10 MiB limit")

        mime_type, width, height = inspect_image(content)
        if claimed_mime_type != mime_type:
            raise ReferenceAssetError("reference image MIME type does not match its bytes")
        digest = hashlib.sha256(content).hexdigest()
        blob_path = self._blob_root / digest
        if blob_path.exists() and blob_path.read_bytes() != content:
            raise ReferenceAssetError("reference image digest collision")
        if not blob_path.exists():
            blob_path.write_bytes(content)

        created_at = datetime.now(timezone.utc)
        asset_id = f"ref-{secrets.token_hex(12)}"
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO reference_assets VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    asset_id,
                    principal_id,
                    tenant_id,
                    digest,
                    mime_type,
                    filename,
                    width,
                    height,
                    len(content),
                    role.value,
                    normalized_instruction,
                    created_at.isoformat(),
                ),
            )
        return ReferenceAssetRecord(
            asset_id,
            principal_id,
            tenant_id,
            digest,
            mime_type,
            filename,
            width,
            height,
            len(content),
            role,
            normalized_instruction,
            created_at,
        )

    def bind_request(
        self,
        request_id: str,
        asset_ids: tuple[str, ...],
        *,
        principal_id: str,
        tenant_id: str,
    ) -> tuple[ReferenceAssetRecord, ...]:
        _identity("request_id", request_id)
        _owner("principal_id", principal_id)
        _owner("tenant_id", tenant_id)
        if len(asset_ids) > MAX_REFERENCE_ASSETS:
            raise ReferenceAssetError(
                f"at most {MAX_REFERENCE_ASSETS} reference images are allowed per request"
            )
        if len(set(asset_ids)) != len(asset_ids):
            raise ReferenceAssetError("duplicate reference asset ids are not allowed")

        records = tuple(
            self.get_owned(asset_id, principal_id=principal_id, tenant_id=tenant_id)
            for asset_id in asset_ids
        )
        total = sum(record.size_bytes for record in records)
        if total > MAX_REFERENCE_TOTAL_BYTES:
            raise ReferenceAssetError("reference images exceed the 100 MiB request limit")
        for exclusive_role in (
            ReferenceAssetRole.FIRST_FRAME,
            ReferenceAssetRole.LAST_FRAME,
        ):
            if sum(record.role is exclusive_role for record in records) > 1:
                raise ReferenceAssetError(
                    f"only one {exclusive_role.value} reference image is allowed"
                )

        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                "SELECT COUNT(*) FROM request_reference_assets WHERE request_id = ?",
                (request_id,),
            ).fetchone()[0]
            if existing:
                raise ReferenceAssetError("reference assets are already bound to this request")
            connection.executemany(
                "INSERT INTO request_reference_assets (request_id, asset_id, ordinal) "
                "VALUES (?, ?, ?)",
                (
                    (request_id, record.asset_id, ordinal)
                    for ordinal, record in enumerate(records)
                ),
            )
        return records

    def for_request(self, request_id: str) -> tuple[ReferenceAssetRecord, ...]:
        _identity("request_id", request_id)
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT a.* FROM request_reference_assets r "
                "JOIN reference_assets a ON a.asset_id = r.asset_id "
                "WHERE r.request_id = ? ORDER BY r.ordinal",
                (request_id,),
            ).fetchall()
        return tuple(_record(row) for row in rows)

    def get_owned(
        self,
        asset_id: str,
        *,
        principal_id: str,
        tenant_id: str,
    ) -> ReferenceAssetRecord:
        _identity("asset_id", asset_id, prefix="ref-")
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM reference_assets WHERE asset_id = ?",
                (asset_id,),
            ).fetchone()
        if row is None:
            raise ReferenceAssetError("unknown reference asset")
        record = _record(row)
        if record.principal_id != principal_id or record.tenant_id != tenant_id:
            raise ReferenceAssetError("reference asset ownership mismatch")
        return record

    def read_bytes(self, record: ReferenceAssetRecord) -> bytes:
        path = self._blob_root / record.sha256
        if not path.is_file():
            raise ReferenceAssetError("reference image bytes are missing")
        content = path.read_bytes()
        if hashlib.sha256(content).hexdigest() != record.sha256:
            raise ReferenceAssetError("reference image integrity check failed")
        if len(content) != record.size_bytes:
            raise ReferenceAssetError("reference image size changed after admission")
        mime_type, width, height = inspect_image(content)
        if (
            mime_type != record.mime_type
            or width != record.width
            or height != record.height
        ):
            raise ReferenceAssetError("reference image metadata changed after admission")
        return content


def inspect_image(content: bytes) -> tuple[str, int, int]:
    """Return trusted MIME/geometry from PNG, JPEG, or non-animated WebP bytes."""
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        mime_type, width, height = _inspect_png(content)
    elif content.startswith(b"\xff\xd8"):
        mime_type, width, height = _inspect_jpeg(content)
    elif len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        mime_type, width, height = _inspect_webp(content)
    else:
        raise ReferenceAssetError("only JPEG, PNG, and WebP reference images are supported")
    _geometry(width, height)
    return mime_type, width, height


def _inspect_png(content: bytes) -> tuple[str, int, int]:
    if len(content) < 33 or content[12:16] != b"IHDR":
        raise ReferenceAssetError("PNG reference image header is malformed")
    width, height = struct.unpack(">II", content[16:24])
    return "image/png", width, height


def _inspect_jpeg(content: bytes) -> tuple[str, int, int]:
    offset = 2
    sof_markers = {
        0xC0,
        0xC1,
        0xC2,
        0xC3,
        0xC5,
        0xC6,
        0xC7,
        0xC9,
        0xCA,
        0xCB,
        0xCD,
        0xCE,
        0xCF,
    }
    while offset + 4 <= len(content):
        while offset < len(content) and content[offset] == 0xFF:
            offset += 1
        if offset >= len(content):
            break
        marker = content[offset]
        offset += 1
        if marker in {0xD8, 0xD9}:
            continue
        if marker == 0xDA:
            break
        if offset + 2 > len(content):
            break
        segment_length = struct.unpack(">H", content[offset : offset + 2])[0]
        if segment_length < 2 or offset + segment_length > len(content):
            raise ReferenceAssetError("JPEG reference image header is malformed")
        if marker in sof_markers:
            if segment_length < 7:
                raise ReferenceAssetError("JPEG reference image dimensions are malformed")
            height, width = struct.unpack(">HH", content[offset + 3 : offset + 7])
            return "image/jpeg", width, height
        offset += segment_length
    raise ReferenceAssetError("JPEG reference image dimensions are unavailable")


def _inspect_webp(content: bytes) -> tuple[str, int, int]:
    if b"ANIM" in content:
        raise ReferenceAssetError("animated WebP reference images are not supported")
    if len(content) < 30:
        raise ReferenceAssetError("WebP reference image header is malformed")
    chunk = content[12:16]
    if chunk == b"VP8X":
        if len(content) < 30:
            raise ReferenceAssetError("WebP VP8X header is malformed")
        width = 1 + int.from_bytes(content[24:27], "little")
        height = 1 + int.from_bytes(content[27:30], "little")
        return "image/webp", width, height
    if chunk == b"VP8L":
        if len(content) < 25 or content[20] != 0x2F:
            raise ReferenceAssetError("WebP VP8L header is malformed")
        bits = int.from_bytes(content[21:25], "little")
        width = (bits & 0x3FFF) + 1
        height = ((bits >> 14) & 0x3FFF) + 1
        return "image/webp", width, height
    if chunk == b"VP8 ":
        signature = b"\x9d\x01\x2a"
        position = content.find(signature, 20, min(len(content), 64))
        if position < 0 or position + 7 > len(content):
            raise ReferenceAssetError("WebP VP8 header is malformed")
        width = int.from_bytes(content[position + 3 : position + 5], "little") & 0x3FFF
        height = int.from_bytes(content[position + 5 : position + 7], "little") & 0x3FFF
        return "image/webp", width, height
    raise ReferenceAssetError("unsupported WebP reference image encoding")


def _geometry(width: int, height: int) -> None:
    if width <= 0 or height <= 0:
        raise ReferenceAssetError("reference image dimensions must be positive")
    if width > MAX_REFERENCE_DIMENSION or height > MAX_REFERENCE_DIMENSION:
        raise ReferenceAssetError("reference image dimensions exceed 8192 pixels")
    if width * height > MAX_REFERENCE_PIXELS:
        raise ReferenceAssetError("reference image exceeds the 40 megapixel limit")


def _record(row: sqlite3.Row) -> ReferenceAssetRecord:
    try:
        role = ReferenceAssetRole(str(row["role"]))
    except ValueError as error:
        raise ReferenceAssetError("stored reference asset role is invalid") from error
    return ReferenceAssetRecord(
        str(row["asset_id"]),
        str(row["principal_id"]),
        str(row["tenant_id"]),
        str(row["sha256"]),
        str(row["mime_type"]),
        str(row["original_filename"]),
        int(row["width"]),
        int(row["height"]),
        int(row["size_bytes"]),
        role,
        None if row["instruction"] is None else str(row["instruction"]),
        datetime.fromisoformat(str(row["created_at"])),
    )


def _filename(value: str) -> str:
    if not isinstance(value, str):
        raise ReferenceAssetError("reference image filename must be text")
    normalized = Path(value).name.strip()
    if not normalized or len(normalized) > MAX_REFERENCE_FILENAME_CHARS:
        raise ReferenceAssetError("reference image filename is invalid")
    if any(ord(character) < 32 for character in normalized):
        raise ReferenceAssetError("reference image filename contains control characters")
    return normalized


def _instruction(value: str | None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ReferenceAssetError("reference image instruction must be text")
    normalized = value.strip()
    if not normalized:
        return None
    if len(normalized) > MAX_REFERENCE_INSTRUCTION_CHARS:
        raise ReferenceAssetError("reference image instruction exceeds 500 characters")
    return normalized


def _owner(name: str, value: str) -> None:
    if not value or value != value.strip() or len(value) > 256:
        raise ReferenceAssetError(f"{name} must be non-blank, trimmed, and bounded")


def _identity(name: str, value: str, *, prefix: str | None = None) -> None:
    if not value or value != value.strip() or len(value) > 128:
        raise ReferenceAssetError(f"invalid {name}")
    if prefix is not None and not value.startswith(prefix):
        raise ReferenceAssetError(f"invalid {name}")
    if any(
        character not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
        for character in value
    ):
        raise ReferenceAssetError(f"invalid {name}")
