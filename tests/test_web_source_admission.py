from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

import pytest

from services.web_source_admission import (
    WebSourceAdmissionError,
    WebSourceAdmissionStore,
)


def _archive(label: str = "Home") -> bytes:
    files = {
        "package.json": json.dumps(
            {
                "name": "existing-site",
                "dependencies": {"next": "16.2.11", "react": "19.2.0"},
            },
            sort_keys=True,
        ).encode(),
        "app/page.tsx": (
            f"export default function Page(){{return <main>{label}</main>}}"
        ).encode(),
    }
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for relative, body in files.items():
            bundle.writestr(relative, body)
    return buffer.getvalue()


def test_source_admission_records_owner_and_binds_request_immutably(tmp_path: Path) -> None:
    store = WebSourceAdmissionStore(tmp_path / "state.sqlite3", tmp_path / "artifacts")
    record = store.put(
        archive=_archive(),
        principal_id="principal-a",
        tenant_id="tenant-a",
    )

    assert record.asset_id.startswith("wsrc-")
    assert record.public_metadata()["framework"] == "nextjs-react"
    assert record.public_metadata()["routes"] == ["/"]
    owned = store.get_owned(
        record.asset_id,
        principal_id="principal-a",
        tenant_id="tenant-a",
    )
    assert owned.snapshot.tree_sha256 == record.snapshot.tree_sha256

    bound = store.bind_request(
        "request-a",
        record.asset_id,
        principal_id="principal-a",
        tenant_id="tenant-a",
    )
    assert bound.asset_id == record.asset_id
    assert store.for_request("request-a") == bound
    assert (
        store.bind_request(
            "request-a",
            record.asset_id,
            principal_id="principal-a",
            tenant_id="tenant-a",
        ).asset_id
        == record.asset_id
    )


def test_source_admission_rejects_cross_tenant_access(tmp_path: Path) -> None:
    store = WebSourceAdmissionStore(tmp_path / "state.sqlite3", tmp_path / "artifacts")
    record = store.put(
        archive=_archive(),
        principal_id="principal-a",
        tenant_id="tenant-a",
    )

    with pytest.raises(WebSourceAdmissionError, match="ownership mismatch"):
        store.get_owned(
            record.asset_id,
            principal_id="principal-b",
            tenant_id="tenant-b",
        )


def test_source_admission_discard_removes_only_unbound_source(tmp_path: Path) -> None:
    store = WebSourceAdmissionStore(tmp_path / "state.sqlite3", tmp_path / "artifacts")
    record = store.put(
        archive=_archive(),
        principal_id="principal-a",
        tenant_id="tenant-a",
    )
    root = Path(record.snapshot.root_path)
    assert root.is_dir()

    assert store.discard_unbound(
        record.asset_id,
        principal_id="principal-a",
        tenant_id="tenant-a",
    )
    assert not root.exists()


def test_source_admission_keeps_shared_snapshot_until_last_asset_is_discarded(
    tmp_path: Path,
) -> None:
    store = WebSourceAdmissionStore(tmp_path / "state.sqlite3", tmp_path / "artifacts")
    first = store.put(
        archive=_archive(),
        principal_id="principal-a",
        tenant_id="tenant-a",
    )
    second = store.put(
        archive=_archive(),
        principal_id="principal-b",
        tenant_id="tenant-b",
    )
    assert first.snapshot.root_path == second.snapshot.root_path
    root = Path(first.snapshot.root_path)

    store.discard_unbound(
        first.asset_id,
        principal_id="principal-a",
        tenant_id="tenant-a",
    )
    assert root.is_dir()
    store.discard_unbound(
        second.asset_id,
        principal_id="principal-b",
        tenant_id="tenant-b",
    )
    assert not root.exists()


def test_bound_source_cannot_be_discarded_or_rebound(tmp_path: Path) -> None:
    store = WebSourceAdmissionStore(tmp_path / "state.sqlite3", tmp_path / "artifacts")
    first = store.put(
        archive=_archive("A"),
        principal_id="principal-a",
        tenant_id="tenant-a",
    )
    second = store.put(
        archive=_archive("B"),
        principal_id="principal-a",
        tenant_id="tenant-a",
    )
    store.bind_request(
        "request-a",
        first.asset_id,
        principal_id="principal-a",
        tenant_id="tenant-a",
    )

    with pytest.raises(WebSourceAdmissionError, match="bound Web source"):
        store.discard_unbound(
            first.asset_id,
            principal_id="principal-a",
            tenant_id="tenant-a",
        )
    with pytest.raises(WebSourceAdmissionError, match="immutable after request binding"):
        store.bind_request(
            "request-a",
            second.asset_id,
            principal_id="principal-a",
            tenant_id="tenant-a",
        )


def test_admitted_snapshot_tamper_is_detected(tmp_path: Path) -> None:
    store = WebSourceAdmissionStore(tmp_path / "state.sqlite3", tmp_path / "artifacts")
    record = store.put(
        archive=_archive(),
        principal_id="principal-a",
        tenant_id="tenant-a",
    )
    (Path(record.snapshot.root_path) / "app/page.tsx").write_text(
        "tampered", encoding="utf-8"
    )

    with pytest.raises(WebSourceAdmissionError, match="integrity mismatch"):
        store.get_owned(
            record.asset_id,
            principal_id="principal-a",
            tenant_id="tenant-a",
        )


def test_admission_quota_limits_unsubmitted_sources(tmp_path: Path) -> None:
    store = WebSourceAdmissionStore(tmp_path / "state.sqlite3", tmp_path / "artifacts")
    store.put(archive=_archive("A"), principal_id="p", tenant_id="t")
    store.put(archive=_archive("B"), principal_id="p", tenant_id="t")

    with pytest.raises(WebSourceAdmissionError, match="too many unsubmitted"):
        store.put(archive=_archive("C"), principal_id="p", tenant_id="t")
