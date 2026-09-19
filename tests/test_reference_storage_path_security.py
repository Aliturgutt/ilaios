from __future__ import annotations

import hashlib
import struct
from pathlib import Path

import pytest

from services.reference_asset_admission import ReferenceAssetAdmissionStore
from services.reference_assets import ReferenceAssetError, ReferenceAssetRole


def _png() -> bytes:
    return (
        b"\x89PNG\r\n\x1a\n"
        + struct.pack(">I", 13)
        + b"IHDR"
        + struct.pack(">II", 64, 48)
        + b"\x08\x02\x00\x00\x00"
        + b"\x00\x00\x00\x00"
    )


def test_reference_store_rejects_symlinked_blob_root(tmp_path: Path) -> None:
    real_root = tmp_path / "real-blobs"
    real_root.mkdir()
    linked_root = tmp_path / "reference-blobs"
    try:
        linked_root.symlink_to(real_root, target_is_directory=True)
    except OSError:
        pytest.skip("symbolic links are unavailable on this test platform")

    with pytest.raises(ReferenceAssetError, match="symbolic links"):
        ReferenceAssetAdmissionStore(
            tmp_path / "reference-assets.sqlite3",
            linked_root,
        )


def test_reference_store_rejects_symlinked_digest_path(tmp_path: Path) -> None:
    blob_root = tmp_path / "reference-blobs"
    store = ReferenceAssetAdmissionStore(
        tmp_path / "reference-assets.sqlite3",
        blob_root,
    )
    content = _png()
    digest = hashlib.sha256(content).hexdigest()
    target = tmp_path / "outside-target"
    target.write_bytes(b"must-not-be-overwritten")
    digest_path = blob_root / digest
    try:
        digest_path.symlink_to(target)
    except OSError:
        pytest.skip("symbolic links are unavailable on this test platform")

    with pytest.raises(ReferenceAssetError, match="symbolic link"):
        store.put(
            content=content,
            claimed_mime_type="image/png",
            original_filename="reference.png",
            role=ReferenceAssetRole.STYLE,
            instruction=None,
            principal_id="principal-a",
            tenant_id="tenant-a",
        )

    assert target.read_bytes() == b"must-not-be-overwritten"
