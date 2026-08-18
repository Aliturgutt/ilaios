"""Tenant-scoped source-video input storage for governed Video revisions.

Source media is authenticated user input, not accepted execution evidence. It is
therefore kept outside the append-only EvidenceStore, like reference images, but
with its own single-source request contract. Bytes are content addressed, MIME
and container facts are verified server-side, ownership is enforced, request
binding is immutable, and unsubmitted uploads are strictly bounded/retained.
This module does not edit media, select providers, or create a second Video runtime.
"""

from __future__ import annotations

import hashlib
import os
import secrets
import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Protocol

from src.video_automation.media_technical_validation import (
    FfprobeMediaTechnicalProbe,
    MediaProbeObservation,
    MediaTechnicalValidationError,
)

MAX_SOURCE_MEDIA_BYTES = 128 * 1024 * 1024
MAX_SOURCE_MEDIA_DURATION_SECONDS = 15 * 60.0
MAX_SOURCE_MEDIA_DIMENSION = 7680
MAX_SOURCE_MEDIA_FILENAME_CHARS = 180
MAX_UNBOUND_SOURCE_MEDIA_ASSETS = 2
MAX_UNBOUND_SOURCE_MEDIA_BYTES = 256 * 1024 * 1024
UNBOUND_SOURCE_MEDIA_RETENTION = timedelta(hours=24)
ALLOWED_SOURCE_VIDEO_CODECS = frozenset({"h264", "hevc", "vp9", "av1"})
SOURCE_MEDIA_MIME_TYPE = "video/mp4"


class SourceMediaError(ValueError):
    """Raised when source video cannot cross the governed input boundary."""


class SourceMediaProbe(Protocol):
    @property
    def probe_id(self) -> str: ...

    def probe(self, path: Path) -> MediaProbeObservation: ...


@dataclass(frozen=True, slots=True)
class SourceMediaRecord:
    asset_id: str
    principal_id: str
    tenant_id: str
    sha256: str
    mime_type: str
    original_filename: str
    size_bytes: int
    duration_seconds: float
    width: int
    height: int
    frames_per_second: float
    video_codec: str
    audio_codec: str | None
    probe_id: str
    created_at: datetime

    def public_metadata(self) -> dict[str, object]:
        return {
            "asset_id": self.asset_id,
            "sha256": self.sha256,
            "mime_type": self.mime_type,
            "original_filename": self.original_filename,
            "size_bytes": self.size_bytes,
            "duration_seconds": self.duration_seconds,
            "width": self.width,
            "height": self.height,
            "frames_per_second": self.frames_per_second,
            "video_codec": self.video_codec,
            "audio_codec": self.audio_codec,
            "probe_id": self.probe_id,
        }


class SourceMediaStore:
    """Private durable source-video store with immutable request binding."""

    def __init__(
        self,
        database_path: Path,
        blob_root: Path,
        *,
        probe: SourceMediaProbe | None = None,
    ) -> None:
        if database_path.is_symlink() or blob_root.is_symlink():
            raise SourceMediaError("source media storage paths must not be symbolic links")
        self._database_path = database_path
        self._blob_root = blob_root
        self._probe = probe or FfprobeMediaTechnicalProbe(timeout_seconds=30.0)
        self._lock = threading.Lock()
        database_path.parent.mkdir(parents=True, exist_ok=True)
        blob_root.mkdir(parents=True, exist_ok=True)
        if database_path.is_symlink() or blob_root.is_symlink() or not blob_root.is_dir():
            raise SourceMediaError("source media storage paths changed during initialization")
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS source_media_assets (
                    asset_id TEXT PRIMARY KEY,
                    principal_id TEXT NOT NULL,
                    tenant_id TEXT NOT NULL,
                    sha256 TEXT NOT NULL,
                    mime_type TEXT NOT NULL,
                    original_filename TEXT NOT NULL,
                    size_bytes INTEGER NOT NULL,
                    duration_seconds REAL NOT NULL,
                    width INTEGER NOT NULL,
                    height INTEGER NOT NULL,
                    frames_per_second REAL NOT NULL,
                    video_codec TEXT NOT NULL,
                    audio_codec TEXT,
                    probe_id TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_source_media_owner
                    ON source_media_assets(tenant_id, principal_id, created_at);
                CREATE TABLE IF NOT EXISTS request_source_media (
                    request_id TEXT PRIMARY KEY,
                    asset_id TEXT NOT NULL REFERENCES source_media_assets(asset_id),
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
        content: bytes,
        claimed_mime_type: str,
        original_filename: str,
        principal_id: str,
        tenant_id: str,
    ) -> SourceMediaRecord:
        _owner("principal_id", principal_id)
        _owner("tenant_id", tenant_id)
        filename = _filename(original_filename)
        if claimed_mime_type.strip().lower() != SOURCE_MEDIA_MIME_TYPE:
            raise SourceMediaError("source video must declare video/mp4")
        if not content:
            raise SourceMediaError("source video must not be empty")
        if len(content) > MAX_SOURCE_MEDIA_BYTES:
            raise SourceMediaError("source video exceeds the 128 MiB limit")
        _require_mp4_signature(content)

        digest = hashlib.sha256(content).hexdigest()
        path = self._blob_root / digest
        with self._lock:
            self._prune_expired_unbound(datetime.now(timezone.utc))
            count, bytes_used = self._unbound_usage(
                principal_id=principal_id,
                tenant_id=tenant_id,
            )
            if count >= MAX_UNBOUND_SOURCE_MEDIA_ASSETS:
                raise SourceMediaError(
                    "too many unsubmitted source videos; submit or discard the current upload"
                )
            if bytes_used + len(content) > MAX_UNBOUND_SOURCE_MEDIA_BYTES:
                raise SourceMediaError(
                    "unsubmitted source videos exceed the 256 MiB safety quota"
                )

            if path.is_symlink():
                raise SourceMediaError("source video blob path is a symbolic link")
            existed = path.exists()
            if existed:
                if not path.is_file():
                    raise SourceMediaError("source video blob path is not a regular file")
                existing = path.read_bytes()
                if hashlib.sha256(existing).hexdigest() != digest or existing != content:
                    raise SourceMediaError("source video digest collision")
            else:
                temporary = path.with_name(
                    f".{path.name}.{os.getpid()}.{threading.get_ident()}.tmp"
                )
                temporary.write_bytes(content)
                try:
                    os.chmod(temporary, 0o600)
                except OSError:
                    pass
                os.replace(temporary, path)

            try:
                observation = self._probe.probe(path)
                _validate_observation(observation)
            except (MediaTechnicalValidationError, SourceMediaError) as error:
                if not existed:
                    path.unlink(missing_ok=True)
                if isinstance(error, SourceMediaError):
                    raise
                raise SourceMediaError("source video technical probe failed") from error
            except Exception as error:  # noqa: BLE001
                if not existed:
                    path.unlink(missing_ok=True)
                raise SourceMediaError("source video technical probe failed") from error

            created_at = datetime.now(timezone.utc)
            asset_id = f"src-{secrets.token_hex(12)}"
            try:
                with self._connect() as connection:
                    connection.execute(
                        "INSERT INTO source_media_assets VALUES "
                        "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (
                            asset_id,
                            principal_id,
                            tenant_id,
                            digest,
                            SOURCE_MEDIA_MIME_TYPE,
                            filename,
                            len(content),
                            observation.duration_seconds,
                            observation.width,
                            observation.height,
                            observation.frames_per_second,
                            observation.video_codec,
                            observation.audio_codec,
                            self._probe.probe_id,
                            created_at.isoformat(),
                        ),
                    )
            except Exception:
                if not existed and not self._digest_is_registered(digest):
                    path.unlink(missing_ok=True)
                raise

        return SourceMediaRecord(
            asset_id=asset_id,
            principal_id=principal_id,
            tenant_id=tenant_id,
            sha256=digest,
            mime_type=SOURCE_MEDIA_MIME_TYPE,
            original_filename=filename,
            size_bytes=len(content),
            duration_seconds=observation.duration_seconds,
            width=observation.width,
            height=observation.height,
            frames_per_second=observation.frames_per_second,
            video_codec=observation.video_codec,
            audio_codec=observation.audio_codec,
            probe_id=self._probe.probe_id,
            created_at=created_at,
        )

    def get_owned(
        self,
        asset_id: str,
        *,
        principal_id: str,
        tenant_id: str,
    ) -> SourceMediaRecord:
        _identity("asset_id", asset_id, prefix="src-")
        _owner("principal_id", principal_id)
        _owner("tenant_id", tenant_id)
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM source_media_assets WHERE asset_id = ?",
                (asset_id,),
            ).fetchone()
        if row is None:
            raise SourceMediaError("unknown source media asset")
        record = _record(row)
        if record.principal_id != principal_id or record.tenant_id != tenant_id:
            raise SourceMediaError("source media ownership mismatch")
        return record

    def bind_request(
        self,
        request_id: str,
        asset_id: str,
        *,
        principal_id: str,
        tenant_id: str,
    ) -> SourceMediaRecord:
        _identity("request_id", request_id)
        with self._lock:
            record = self.get_owned(
                asset_id,
                principal_id=principal_id,
                tenant_id=tenant_id,
            )
            self.require_registered_path(record.asset_id)
            bound_at = datetime.now(timezone.utc).isoformat()
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                existing = connection.execute(
                    "SELECT asset_id FROM request_source_media WHERE request_id = ?",
                    (request_id,),
                ).fetchone()
                if existing is not None:
                    if str(existing["asset_id"]) != asset_id:
                        raise SourceMediaError(
                            "source media is immutable after request binding"
                        )
                    return record
                connection.execute(
                    "INSERT INTO request_source_media (request_id, asset_id, bound_at) "
                    "VALUES (?, ?, ?)",
                    (request_id, asset_id, bound_at),
                )
            return record

    def discard_unbound(
        self,
        asset_id: str,
        *,
        principal_id: str,
        tenant_id: str,
    ) -> bool:
        """Discard caller-owned source input only when no request has bound it."""

        with self._lock:
            record = self.get_owned(
                asset_id,
                principal_id=principal_id,
                tenant_id=tenant_id,
            )
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                bound = connection.execute(
                    "SELECT 1 FROM request_source_media WHERE asset_id = ? LIMIT 1",
                    (asset_id,),
                ).fetchone()
                if bound is not None:
                    raise SourceMediaError(
                        "bound source media cannot be discarded through the upload boundary"
                    )
                connection.execute(
                    "DELETE FROM source_media_assets WHERE asset_id = ?",
                    (asset_id,),
                )
            self._remove_blob_if_unreferenced(record.sha256)
            return True

    def for_request(self, request_id: str) -> SourceMediaRecord | None:
        _identity("request_id", request_id)
        with self._connect() as connection:
            row = connection.execute(
                "SELECT a.* FROM request_source_media r "
                "JOIN source_media_assets a ON a.asset_id = r.asset_id "
                "WHERE r.request_id = ?",
                (request_id,),
            ).fetchone()
        return None if row is None else _record(row)

    def require_registered_path(self, asset_id: str) -> Path:
        _identity("asset_id", asset_id, prefix="src-")
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM source_media_assets WHERE asset_id = ?",
                (asset_id,),
            ).fetchone()
        if row is None:
            raise SourceMediaError("unknown source media asset")
        record = _record(row)
        path = self._blob_root / record.sha256
        if path.is_symlink() or not path.is_file():
            raise SourceMediaError("source video bytes are unavailable")
        content = path.read_bytes()
        if len(content) != record.size_bytes:
            raise SourceMediaError("source video size changed after admission")
        if hashlib.sha256(content).hexdigest() != record.sha256:
            raise SourceMediaError("source video integrity check failed")
        _require_mp4_signature(content)
        return path.resolve()

    def _unbound_usage(self, *, principal_id: str, tenant_id: str) -> tuple[int, int]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT COUNT(*), COALESCE(SUM(a.size_bytes), 0) "
                "FROM source_media_assets a "
                "LEFT JOIN request_source_media r ON r.asset_id = a.asset_id "
                "WHERE a.principal_id = ? AND a.tenant_id = ? AND r.asset_id IS NULL",
                (principal_id, tenant_id),
            ).fetchone()
        if row is None:
            return 0, 0
        return int(row[0]), int(row[1])

    def _prune_expired_unbound(self, now: datetime) -> None:
        cutoff = (now - UNBOUND_SOURCE_MEDIA_RETENTION).isoformat()
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT a.asset_id, a.sha256 FROM source_media_assets a "
                "LEFT JOIN request_source_media r ON r.asset_id = a.asset_id "
                "WHERE r.asset_id IS NULL AND a.created_at < ?",
                (cutoff,),
            ).fetchall()
            if not rows:
                return
            connection.execute("BEGIN IMMEDIATE")
            connection.executemany(
                "DELETE FROM source_media_assets WHERE asset_id = ?",
                ((str(row["asset_id"]),) for row in rows),
            )
        for row in rows:
            self._remove_blob_if_unreferenced(str(row["sha256"]))

    def _remove_blob_if_unreferenced(self, digest: str) -> None:
        if self._digest_is_registered(digest):
            return
        path = self._blob_root / digest
        if path.is_symlink():
            raise SourceMediaError("source video blob path is a symbolic link")
        try:
            path.unlink(missing_ok=True)
        except OSError as error:
            raise SourceMediaError("source video bytes could not be discarded") from error

    def _digest_is_registered(self, digest: str) -> bool:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT 1 FROM source_media_assets WHERE sha256 = ? LIMIT 1",
                (digest,),
            ).fetchone()
        return row is not None


def _validate_observation(observation: MediaProbeObservation) -> None:
    containers = {item.strip().lower() for item in observation.container.split(",")}
    if "mp4" not in containers:
        raise SourceMediaError("source video container is not MP4")
    if observation.video_stream_count != 1:
        raise SourceMediaError("source video must contain exactly one video stream")
    if observation.audio_stream_count > 1:
        raise SourceMediaError("source video may contain at most one audio stream")
    if observation.video_codec not in ALLOWED_SOURCE_VIDEO_CODECS:
        raise SourceMediaError("source video codec is unsupported")
    if not 0 < observation.duration_seconds <= MAX_SOURCE_MEDIA_DURATION_SECONDS:
        raise SourceMediaError("source video duration is outside the allowed range")
    if not 0 < observation.width <= MAX_SOURCE_MEDIA_DIMENSION:
        raise SourceMediaError("source video width is outside the allowed range")
    if not 0 < observation.height <= MAX_SOURCE_MEDIA_DIMENSION:
        raise SourceMediaError("source video height is outside the allowed range")
    if not 0 < observation.frames_per_second <= 120:
        raise SourceMediaError("source video frame rate is outside the allowed range")


def _require_mp4_signature(content: bytes) -> None:
    # ISO BMFF brands live in the ftyp box near the beginning of valid MP4 files.
    # This is only an early rejection gate; ffprobe remains authoritative for
    # container/stream facts before metadata is admitted.
    if len(content) < 12 or content[4:8] != b"ftyp":
        raise SourceMediaError("source video bytes do not contain an MP4 ftyp signature")


def _record(row: sqlite3.Row) -> SourceMediaRecord:
    return SourceMediaRecord(
        asset_id=str(row["asset_id"]),
        principal_id=str(row["principal_id"]),
        tenant_id=str(row["tenant_id"]),
        sha256=str(row["sha256"]),
        mime_type=str(row["mime_type"]),
        original_filename=str(row["original_filename"]),
        size_bytes=int(row["size_bytes"]),
        duration_seconds=float(row["duration_seconds"]),
        width=int(row["width"]),
        height=int(row["height"]),
        frames_per_second=float(row["frames_per_second"]),
        video_codec=str(row["video_codec"]),
        audio_codec=(None if row["audio_codec"] is None else str(row["audio_codec"])),
        probe_id=str(row["probe_id"]),
        created_at=datetime.fromisoformat(str(row["created_at"])),
    )


def _filename(value: str) -> str:
    if not isinstance(value, str):
        raise SourceMediaError("source video filename must be text")
    normalized = Path(value).name.strip()
    if not normalized or len(normalized) > MAX_SOURCE_MEDIA_FILENAME_CHARS:
        raise SourceMediaError("source video filename is invalid")
    if any(ord(character) < 32 for character in normalized):
        raise SourceMediaError("source video filename contains control characters")
    if Path(normalized).suffix.lower() != ".mp4":
        raise SourceMediaError("source video filename must use .mp4")
    return normalized


def _owner(name: str, value: str) -> None:
    if not value or value != value.strip() or len(value) > 256:
        raise SourceMediaError(f"{name} must be non-blank, trimmed, and bounded")


def _identity(name: str, value: str, *, prefix: str | None = None) -> None:
    if not value or value != value.strip() or len(value) > 128:
        raise SourceMediaError(f"invalid {name}")
    if prefix is not None and not value.startswith(prefix):
        raise SourceMediaError(f"invalid {name}")
    allowed = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
    if any(character not in allowed for character in value):
        raise SourceMediaError(f"invalid {name}")


__all__ = [
    "ALLOWED_SOURCE_VIDEO_CODECS",
    "MAX_SOURCE_MEDIA_BYTES",
    "MAX_SOURCE_MEDIA_DURATION_SECONDS",
    "MAX_UNBOUND_SOURCE_MEDIA_ASSETS",
    "MAX_UNBOUND_SOURCE_MEDIA_BYTES",
    "SOURCE_MEDIA_MIME_TYPE",
    "SourceMediaError",
    "SourceMediaRecord",
    "SourceMediaStore",
    "UNBOUND_SOURCE_MEDIA_RETENTION",
]
