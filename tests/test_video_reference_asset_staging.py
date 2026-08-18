from __future__ import annotations

from pathlib import Path

import pytest

from src.video_automation.reference_asset_staging import (
    LocalReferenceAssetStore,
    ReferenceAssetError,
    StagedReferenceAsset,
    UnconfiguredReferenceImageStager,
    stage_reference_pool,
)
from src.video_automation.reference_images import ReferenceImageRole


class _Stager:
    def __init__(self, *, digest_override: str | None = None, ttl: int = 600) -> None:
        self.digest_override = digest_override
        self.ttl = ttl

    def stage(self, asset, *, now_epoch_s: int, minimum_ttl_seconds: int):
        return StagedReferenceAsset(
            asset_id=asset.asset_id,
            sha256_digest=self.digest_override or asset.sha256_digest,
            https_url=f"https://video-assets.example/{asset.sha256_digest}.jpg",
            expires_at_epoch_s=now_epoch_s + self.ttl,
        )


def _jpeg() -> bytes:
    return b"\xff\xd8\xff\xe0" + b"reference-image" * 16


def test_private_asset_store_is_digest_addressed_and_scope_bound(tmp_path: Path) -> None:
    store = LocalReferenceAssetStore(tmp_path)
    first = store.put(
        tenant_id="tenant-a",
        project_id="project-a",
        content=_jpeg(),
        media_type="image/jpeg",
        role=ReferenceImageRole.SUBJECT_PRIMARY,
    )
    second = store.put(
        tenant_id="tenant-a",
        project_id="project-a",
        content=_jpeg(),
        media_type="image/jpeg",
        role=ReferenceImageRole.SUBJECT_PRIMARY,
    )
    assert first.asset_id == second.asset_id
    assert first.sha256_digest == second.sha256_digest
    assert first.storage_path == second.storage_path
    assert first.storage_path.read_bytes() == _jpeg()


def test_content_type_extension_spoof_is_rejected(tmp_path: Path) -> None:
    store = LocalReferenceAssetStore(tmp_path)
    with pytest.raises(ReferenceAssetError, match="JPEG content signature"):
        store.put(
            tenant_id="tenant-a",
            project_id="project-a",
            content=b"not-a-jpeg",
            media_type="image/jpeg",
            role=ReferenceImageRole.STYLE,
        )


def test_unconfigured_stager_blocks_before_external_dispatch(tmp_path: Path) -> None:
    asset = LocalReferenceAssetStore(tmp_path).put(
        tenant_id="tenant-a",
        project_id="project-a",
        content=_jpeg(),
        media_type="image/jpeg",
        role=ReferenceImageRole.SUBJECT_PRIMARY,
    )
    with pytest.raises(ReferenceAssetError, match="staging is unavailable"):
        stage_reference_pool(
            (asset,),
            stager=UnconfiguredReferenceImageStager(),
            now_epoch_s=1_800_000_000,
            minimum_ttl_seconds=300,
        )


def test_stager_digest_substitution_is_rejected(tmp_path: Path) -> None:
    asset = LocalReferenceAssetStore(tmp_path).put(
        tenant_id="tenant-a",
        project_id="project-a",
        content=_jpeg(),
        media_type="image/jpeg",
        role=ReferenceImageRole.SUBJECT_PRIMARY,
    )
    with pytest.raises(ReferenceAssetError, match="digest does not match"):
        stage_reference_pool(
            (asset,),
            stager=_Stager(digest_override="0" * 64),
            now_epoch_s=1_800_000_000,
            minimum_ttl_seconds=300,
        )


def test_staged_reference_ttl_must_cover_generation_window(tmp_path: Path) -> None:
    asset = LocalReferenceAssetStore(tmp_path).put(
        tenant_id="tenant-a",
        project_id="project-a",
        content=_jpeg(),
        media_type="image/jpeg",
        role=ReferenceImageRole.SUBJECT_PRIMARY,
    )
    with pytest.raises(ReferenceAssetError, match="expires before generation window"):
        stage_reference_pool(
            (asset,),
            stager=_Stager(ttl=60),
            now_epoch_s=1_800_000_000,
            minimum_ttl_seconds=300,
        )


def test_valid_staging_produces_provider_safe_reference(tmp_path: Path) -> None:
    asset = LocalReferenceAssetStore(tmp_path).put(
        tenant_id="tenant-a",
        project_id="project-a",
        content=_jpeg(),
        media_type="image/jpeg",
        role=ReferenceImageRole.DETAIL,
    )
    references = stage_reference_pool(
        (asset,),
        stager=_Stager(ttl=600),
        now_epoch_s=1_800_000_000,
        minimum_ttl_seconds=300,
    )
    assert len(references) == 1
    assert references[0].asset_id == asset.asset_id
    assert references[0].role is ReferenceImageRole.DETAIL
    assert references[0].https_url.startswith("https://")
