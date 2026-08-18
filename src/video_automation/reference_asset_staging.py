"""Tenant-scoped local reference assets and provider egress staging contracts.

The Desktop/control plane may retain private source bytes locally, but external
video providers must never receive local paths or loopback URLs. A provider POST
using user references therefore requires a separate staging authority that
returns a short-lived directly downloadable HTTPS URL bound to the source digest.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Protocol

from .reference_images import (
    ALLOWED_REFERENCE_MEDIA_TYPES,
    MAX_REFERENCE_IMAGE_BYTES,
    MAX_REFERENCE_UPLOAD_BYTES,
    MAX_USER_REFERENCE_IMAGES,
    ReferenceImageRole,
    VideoReferenceImage,
    validate_reference_pool,
)


class ReferenceAssetError(ValueError):
    """Raised when private image ingestion or egress staging is unsafe."""


@dataclass(frozen=True, slots=True)
class PrivateReferenceAsset:
    asset_id: str
    tenant_id: str
    project_id: str
    sha256_digest: str
    media_type: str
    size_bytes: int
    storage_path: Path
    role: ReferenceImageRole

    def __post_init__(self) -> None:
        for name, value in (
            ("asset_id", self.asset_id),
            ("tenant_id", self.tenant_id),
            ("project_id", self.project_id),
        ):
            _text(name, value)
        _digest(self.sha256_digest)
        if self.media_type not in ALLOWED_REFERENCE_MEDIA_TYPES:
            raise ReferenceAssetError("unsupported reference image media type")
        if self.size_bytes <= 0 or self.size_bytes > MAX_REFERENCE_IMAGE_BYTES:
            raise ReferenceAssetError("reference image size is outside allowed bounds")
        if not isinstance(self.role, ReferenceImageRole):
            raise ReferenceAssetError("reference image role is invalid")


@dataclass(frozen=True, slots=True)
class StagedReferenceAsset:
    asset_id: str
    sha256_digest: str
    https_url: str
    expires_at_epoch_s: int

    def __post_init__(self) -> None:
        _text("asset_id", self.asset_id)
        _digest(self.sha256_digest)
        if not self.https_url.startswith("https://"):
            raise ReferenceAssetError("staged reference URL must use HTTPS")
        if self.expires_at_epoch_s <= 0:
            raise ReferenceAssetError("staged reference expiry must be positive")


class ReferenceImageStager(Protocol):
    """External egress boundary; implementations own signed/public HTTPS staging."""

    def stage(
        self,
        asset: PrivateReferenceAsset,
        *,
        now_epoch_s: int,
        minimum_ttl_seconds: int,
    ) -> StagedReferenceAsset: ...


class UnconfiguredReferenceImageStager:
    """Production-safe default: block before provider spend."""

    def stage(
        self,
        asset: PrivateReferenceAsset,
        *,
        now_epoch_s: int,
        minimum_ttl_seconds: int,
    ) -> StagedReferenceAsset:
        raise ReferenceAssetError(
            "reference image staging is unavailable; provider dispatch is blocked"
        )


class LocalReferenceAssetStore:
    """Digest-addressed private source store for validated Desktop uploads."""

    def __init__(self, root: Path) -> None:
        self._root = root
        self._root.mkdir(parents=True, exist_ok=True)

    def put(
        self,
        *,
        tenant_id: str,
        project_id: str,
        content: bytes,
        media_type: str,
        role: ReferenceImageRole,
    ) -> PrivateReferenceAsset:
        _text("tenant_id", tenant_id)
        _text("project_id", project_id)
        if media_type not in ALLOWED_REFERENCE_MEDIA_TYPES:
            raise ReferenceAssetError("unsupported reference image media type")
        if not content or len(content) > MAX_REFERENCE_IMAGE_BYTES:
            raise ReferenceAssetError("reference image size is outside allowed bounds")
        _validate_signature(content, media_type)
        digest = sha256(content).hexdigest()
        scope = sha256(f"{tenant_id}|{project_id}".encode("utf-8")).hexdigest()[:24]
        directory = self._root / scope
        directory.mkdir(parents=True, exist_ok=True)
        suffix = _media_suffix(media_type)
        path = directory / f"{digest}{suffix}"
        if not path.exists():
            temporary = path.with_suffix(path.suffix + ".tmp")
            temporary.write_bytes(content)
            temporary.replace(path)
        return PrivateReferenceAsset(
            asset_id=f"video-ref-{digest[:24]}",
            tenant_id=tenant_id,
            project_id=project_id,
            sha256_digest=digest,
            media_type=media_type,
            size_bytes=len(content),
            storage_path=path,
            role=role,
        )


def stage_reference_pool(
    assets: tuple[PrivateReferenceAsset, ...],
    *,
    stager: ReferenceImageStager,
    now_epoch_s: int,
    minimum_ttl_seconds: int,
) -> tuple[VideoReferenceImage, ...]:
    """Stage a bounded same-scope pool and bind every URL back to its digest."""

    if now_epoch_s <= 0:
        raise ReferenceAssetError("now_epoch_s must be positive")
    if minimum_ttl_seconds <= 0:
        raise ReferenceAssetError("minimum_ttl_seconds must be positive")
    if len(assets) > MAX_USER_REFERENCE_IMAGES:
        raise ReferenceAssetError(
            f"at most {MAX_USER_REFERENCE_IMAGES} reference images are allowed"
        )
    if not assets:
        return ()
    tenants = {asset.tenant_id for asset in assets}
    projects = {asset.project_id for asset in assets}
    if len(tenants) != 1 or len(projects) != 1:
        raise ReferenceAssetError("reference assets must share tenant and project scope")
    if sum(asset.size_bytes for asset in assets) > MAX_REFERENCE_UPLOAD_BYTES:
        raise ReferenceAssetError("reference image pool exceeds total upload bound")

    references: list[VideoReferenceImage] = []
    for asset in assets:
        staged = stager.stage(
            asset,
            now_epoch_s=now_epoch_s,
            minimum_ttl_seconds=minimum_ttl_seconds,
        )
        if staged.asset_id != asset.asset_id:
            raise ReferenceAssetError("stager returned a different asset identity")
        if staged.sha256_digest != asset.sha256_digest:
            raise ReferenceAssetError("stager digest does not match private source asset")
        if staged.expires_at_epoch_s < now_epoch_s + minimum_ttl_seconds:
            raise ReferenceAssetError("staged reference expires before generation window")
        references.append(
            VideoReferenceImage(
                asset_id=asset.asset_id,
                sha256_digest=asset.sha256_digest,
                https_url=staged.https_url,
                role=asset.role,
            )
        )
    return validate_reference_pool(tuple(references))


def _validate_signature(content: bytes, media_type: str) -> None:
    if media_type == "image/jpeg" and not content.startswith(b"\xff\xd8\xff"):
        raise ReferenceAssetError("JPEG content signature is invalid")
    if media_type == "image/png" and not content.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ReferenceAssetError("PNG content signature is invalid")
    if media_type == "image/webp" and not (
        len(content) >= 12
        and content[:4] == b"RIFF"
        and content[8:12] == b"WEBP"
    ):
        raise ReferenceAssetError("WebP content signature is invalid")


def _media_suffix(media_type: str) -> str:
    return {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
    }[media_type]


def _text(name: str, value: str) -> None:
    if not value or value != value.strip():
        raise ReferenceAssetError(f"{name} must be normalized non-blank text")


def _digest(value: str) -> None:
    if len(value) != 64:
        raise ReferenceAssetError("sha256_digest must be a SHA-256 digest")
    try:
        int(value, 16)
    except ValueError as exc:
        raise ReferenceAssetError("sha256_digest must be hexadecimal") from exc
