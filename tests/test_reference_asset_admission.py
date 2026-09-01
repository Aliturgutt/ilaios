from __future__ import annotations

import sqlite3
import struct
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

import services.reference_asset_admission as admission_module
from services.reference_asset_admission import ReferenceAssetAdmissionStore
from services.reference_assets import (
    ReferenceAssetError,
    ReferenceAssetRecord,
    ReferenceAssetRole,
)


def _png(width: int = 64, height: int = 48, *, suffix: bytes = b"") -> bytes:
    return (
        b"\x89PNG\r\n\x1a\n"
        + struct.pack(">I", 13)
        + b"IHDR"
        + struct.pack(">II", width, height)
        + b"\x08\x02\x00\x00\x00"
        + b"\x00\x00\x00\x00"
        + suffix
    )


def _store(tmp_path: Path) -> ReferenceAssetAdmissionStore:
    return ReferenceAssetAdmissionStore(
        tmp_path / "reference-assets.sqlite3",
        tmp_path / "reference-assets" / "blobs",
    )


def _put(
    store: ReferenceAssetAdmissionStore,
    index: int,
    *,
    principal_id: str = "principal-a",
    tenant_id: str = "tenant-a",
) -> ReferenceAssetRecord:
    return store.put(
        content=_png(64 + index, 48, suffix=index.to_bytes(2, "big")),
        claimed_mime_type="image/png",
        original_filename=f"reference-{index}.png",
        role=ReferenceAssetRole.STYLE,
        instruction=None,
        principal_id=principal_id,
        tenant_id=tenant_id,
    )


def test_unbound_reference_count_quota_is_tenant_scoped(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(admission_module, "MAX_UNBOUND_REFERENCE_ASSETS", 2)
    store = _store(tmp_path)
    _put(store, 1)
    _put(store, 2)

    with pytest.raises(ReferenceAssetError, match="too many unbound"):
        _put(store, 3)

    # A different tenant cannot be starved by another tenant's pre-intent uploads.
    other = _put(store, 4, tenant_id="tenant-b")
    assert other.tenant_id == "tenant-b"


def test_bound_assets_stop_consuming_unbound_quota(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(admission_module, "MAX_UNBOUND_REFERENCE_ASSETS", 2)
    store = _store(tmp_path)
    first = _put(store, 1)
    second = _put(store, 2)
    store.bind_request(
        "exec-1",
        (first.asset_id, second.asset_id),
        principal_id="principal-a",
        tenant_id="tenant-a",
    )

    third = _put(store, 3)
    assert third.asset_id.startswith("ref-")


def test_expired_unbound_assets_are_pruned_before_new_upload(tmp_path: Path) -> None:
    store = _store(tmp_path)
    stale = _put(store, 1)
    database_path = tmp_path / "reference-assets.sqlite3"
    stale_time = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "UPDATE reference_assets SET created_at = ? WHERE asset_id = ?",
            (stale_time, stale.asset_id),
        )

    fresh = _put(store, 2)
    assert fresh.asset_id.startswith("ref-")
    with pytest.raises(ReferenceAssetError, match="unknown reference asset"):
        store.get_owned(
            stale.asset_id,
            principal_id="principal-a",
            tenant_id="tenant-a",
        )
    assert not (tmp_path / "reference-assets" / "blobs" / stale.sha256).exists()


def test_discard_unbound_is_owner_scoped_and_removes_orphan_blob(tmp_path: Path) -> None:
    store = _store(tmp_path)
    asset = _put(store, 1)
    blob = tmp_path / "reference-assets" / "blobs" / asset.sha256
    assert blob.is_file()

    with pytest.raises(ReferenceAssetError, match="ownership mismatch"):
        store.discard_unbound(
            (asset.asset_id,),
            principal_id="principal-a",
            tenant_id="tenant-b",
        )

    assert store.discard_unbound(
        (asset.asset_id,),
        principal_id="principal-a",
        tenant_id="tenant-a",
    ) == 1
    assert not blob.exists()


def test_bound_reference_assets_cannot_be_discarded(tmp_path: Path) -> None:
    store = _store(tmp_path)
    asset = _put(store, 1)
    store.bind_request(
        "exec-2",
        (asset.asset_id,),
        principal_id="principal-a",
        tenant_id="tenant-a",
    )

    with pytest.raises(ReferenceAssetError, match="bound reference assets"):
        store.discard_unbound(
            (asset.asset_id,),
            principal_id="principal-a",
            tenant_id="tenant-a",
        )


def test_shared_blob_survives_discard_of_one_unbound_record(tmp_path: Path) -> None:
    store = _store(tmp_path)
    content = _png(64, 48, suffix=b"shared")
    first = store.put(
        content=content,
        claimed_mime_type="image/png",
        original_filename="shared-a.png",
        role=ReferenceAssetRole.STYLE,
        instruction=None,
        principal_id="principal-a",
        tenant_id="tenant-a",
    )
    second = store.put(
        content=content,
        claimed_mime_type="image/png",
        original_filename="shared-b.png",
        role=ReferenceAssetRole.PRODUCT,
        instruction=None,
        principal_id="principal-b",
        tenant_id="tenant-b",
    )
    blob = tmp_path / "reference-assets" / "blobs" / first.sha256

    store.discard_unbound(
        (first.asset_id,),
        principal_id="principal-a",
        tenant_id="tenant-a",
    )

    assert blob.is_file()
    assert store.read_bytes(second) == content


def test_successful_request_release_removes_raw_blob_but_keeps_metadata(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    asset = _put(store, 1)
    store.bind_request(
        "exec-release",
        (asset.asset_id,),
        principal_id="principal-a",
        tenant_id="tenant-a",
    )
    blob = tmp_path / "reference-assets" / "blobs" / asset.sha256
    assert blob.is_file()

    assert store.release_request_blobs("exec-release") == 1

    assert not blob.exists()
    records = store.for_request("exec-release")
    assert len(records) == 1
    assert records[0].sha256 == asset.sha256


def test_shared_blob_is_kept_until_every_bound_request_releases(tmp_path: Path) -> None:
    store = _store(tmp_path)
    asset = _put(store, 1)
    store.bind_request(
        "exec-a",
        (asset.asset_id,),
        principal_id="principal-a",
        tenant_id="tenant-a",
    )
    store.bind_request(
        "exec-b",
        (asset.asset_id,),
        principal_id="principal-a",
        tenant_id="tenant-a",
    )
    blob = tmp_path / "reference-assets" / "blobs" / asset.sha256

    assert store.release_request_blobs("exec-a") == 0
    assert blob.is_file()
    assert store.release_request_blobs("exec-b") == 1
    assert not blob.exists()


def test_released_asset_id_cannot_seed_a_new_request_without_raw_bytes(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    asset = _put(store, 1)
    store.bind_request(
        "exec-old",
        (asset.asset_id,),
        principal_id="principal-a",
        tenant_id="tenant-a",
    )
    store.release_request_blobs("exec-old")

    with pytest.raises(ReferenceAssetError, match="raw bytes are no longer available"):
        store.bind_request(
            "exec-new",
            (asset.asset_id,),
            principal_id="principal-a",
            tenant_id="tenant-a",
        )
