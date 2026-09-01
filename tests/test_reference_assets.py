from __future__ import annotations

import struct
from pathlib import Path

import pytest

from services.reference_assets import (
    MAX_REFERENCE_ASSETS,
    ReferenceAssetError,
    ReferenceAssetRole,
    ReferenceAssetStore,
    inspect_image,
)


def _png(width: int = 64, height: int = 48) -> bytes:
    # The admission parser intentionally reads only trusted container geometry;
    # media decode is independently re-validated before model analysis.
    return (
        b"\x89PNG\r\n\x1a\n"
        + struct.pack(">I", 13)
        + b"IHDR"
        + struct.pack(">II", width, height)
        + b"\x08\x02\x00\x00\x00"
        + b"\x00\x00\x00\x00"
    )


def _store(tmp_path: Path) -> ReferenceAssetStore:
    return ReferenceAssetStore(
        tmp_path / "reference-assets.sqlite3",
        tmp_path / "reference-blobs",
    )


def test_reference_asset_store_binds_owned_assets_in_order(tmp_path: Path) -> None:
    store = _store(tmp_path)
    first = store.put(
        content=_png(32, 24),
        claimed_mime_type="image/png",
        original_filename="../product-front.png",
        role=ReferenceAssetRole.PRODUCT,
        instruction="Keep the silhouette consistent.",
        principal_id="principal-a",
        tenant_id="tenant-a",
    )
    second = store.put(
        content=_png(40, 30) + b"different",
        claimed_mime_type="image/png",
        original_filename="style.png",
        role=ReferenceAssetRole.STYLE,
        instruction=None,
        principal_id="principal-a",
        tenant_id="tenant-a",
    )

    bound = store.bind_request(
        "exec-123",
        (first.asset_id, second.asset_id),
        principal_id="principal-a",
        tenant_id="tenant-a",
    )

    assert [item.asset_id for item in bound] == [first.asset_id, second.asset_id]
    assert [item.asset_id for item in store.for_request("exec-123")] == [
        first.asset_id,
        second.asset_id,
    ]
    assert first.original_filename == "product-front.png"
    assert store.read_bytes(first) == _png(32, 24)


def test_reference_asset_store_rejects_cross_tenant_binding(tmp_path: Path) -> None:
    store = _store(tmp_path)
    asset = store.put(
        content=_png(),
        claimed_mime_type="image/png",
        original_filename="subject.png",
        role=ReferenceAssetRole.SUBJECT,
        instruction=None,
        principal_id="principal-a",
        tenant_id="tenant-a",
    )

    with pytest.raises(ReferenceAssetError, match="ownership mismatch"):
        store.bind_request(
            "exec-124",
            (asset.asset_id,),
            principal_id="principal-a",
            tenant_id="tenant-b",
        )


def test_reference_asset_store_rejects_duplicate_exact_frame_roles(tmp_path: Path) -> None:
    store = _store(tmp_path)
    assets = tuple(
        store.put(
            content=_png(64 + index, 48) + bytes([index]),
            claimed_mime_type="image/png",
            original_filename=f"frame-{index}.png",
            role=ReferenceAssetRole.FIRST_FRAME,
            instruction=None,
            principal_id="principal-a",
            tenant_id="tenant-a",
        )
        for index in range(2)
    )

    with pytest.raises(ReferenceAssetError, match="only one first_frame"):
        store.bind_request(
            "exec-125",
            tuple(asset.asset_id for asset in assets),
            principal_id="principal-a",
            tenant_id="tenant-a",
        )


def test_reference_asset_store_rejects_more_than_twenty(tmp_path: Path) -> None:
    store = _store(tmp_path)
    with pytest.raises(ReferenceAssetError, match=f"at most {MAX_REFERENCE_ASSETS}"):
        store.bind_request(
            "exec-126",
            tuple(f"ref-{index:024d}" for index in range(MAX_REFERENCE_ASSETS + 1)),
            principal_id="principal-a",
            tenant_id="tenant-a",
        )


def test_reference_asset_store_rejects_mime_spoofing_and_large_geometry(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    with pytest.raises(ReferenceAssetError, match="MIME type"):
        store.put(
            content=_png(),
            claimed_mime_type="image/jpeg",
            original_filename="spoof.jpg",
            role=ReferenceAssetRole.OTHER,
            instruction=None,
            principal_id="principal-a",
            tenant_id="tenant-a",
        )

    with pytest.raises(ReferenceAssetError, match="dimensions exceed"):
        inspect_image(_png(9000, 10))


def test_reference_asset_store_detects_blob_tampering(tmp_path: Path) -> None:
    store = _store(tmp_path)
    asset = store.put(
        content=_png(),
        claimed_mime_type="image/png",
        original_filename="safe.png",
        role=ReferenceAssetRole.STYLE,
        instruction=None,
        principal_id="principal-a",
        tenant_id="tenant-a",
    )
    (tmp_path / "reference-blobs" / asset.sha256).write_bytes(b"tampered")

    with pytest.raises(ReferenceAssetError, match="integrity"):
        store.read_bytes(asset)
