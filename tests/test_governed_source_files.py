from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from services.governed_source_files import GovernedSourceFileError, GovernedSourceFileStore


def test_source_bytes_survive_restart_with_exact_hash(tmp_path: Path) -> None:
    root = tmp_path / "source-files"
    content = b"%PDF-1.7\ncompany source bytes"
    first = GovernedSourceFileStore(root)
    record = first.store(
        tenant_id="tenant-a",
        project_id="company-profile",
        source_id="company-file-profile",
        version=1,
        filename="profile.pdf",
        mime_type="application/pdf",
        content=content,
    )
    assert record.sha256 == hashlib.sha256(content).hexdigest()

    restarted = GovernedSourceFileStore(root)
    assert restarted.read_bytes(
        tenant_id="tenant-a",
        project_id="company-profile",
        source_id="company-file-profile",
        version=1,
    ) == content


def test_source_versions_and_tenant_scope_are_isolated(tmp_path: Path) -> None:
    store = GovernedSourceFileStore(tmp_path / "source-files")
    first = store.store(
        tenant_id="tenant-a",
        project_id="company-profile",
        source_id="company-file-pricing",
        version=1,
        filename="pricing.pdf",
        mime_type="application/pdf",
        content=b"%PDF-1.7\nprice one",
    )
    second = store.store(
        tenant_id="tenant-a",
        project_id="company-profile",
        source_id="company-file-pricing",
        version=2,
        filename="pricing.pdf",
        mime_type="application/pdf",
        content=b"%PDF-1.7\nprice two",
    )
    store.store(
        tenant_id="tenant-b",
        project_id="company-profile",
        source_id="company-file-pricing",
        version=1,
        filename="pricing.pdf",
        mime_type="application/pdf",
        content=b"%PDF-1.7\nother tenant",
    )

    versions = store.list_versions(
        tenant_id="tenant-a",
        project_id="company-profile",
        source_id="company-file-pricing",
    )
    assert [record.version for record in versions] == [2, 1]
    assert first.sha256 != second.sha256
    assert store.read_bytes(
        tenant_id="tenant-b",
        project_id="company-profile",
        source_id="company-file-pricing",
        version=1,
    ) == b"%PDF-1.7\nother tenant"


def test_revoke_and_delete_fail_closed_and_keep_tombstone(tmp_path: Path) -> None:
    store = GovernedSourceFileStore(tmp_path / "source-files")
    store.store(
        tenant_id="tenant-a",
        project_id="company-profile",
        source_id="company-file-policy",
        version=1,
        filename="policy.pdf",
        mime_type="application/pdf",
        content=b"%PDF-1.7\npolicy",
    )
    store.revoke(
        tenant_id="tenant-a",
        project_id="company-profile",
        source_id="company-file-policy",
        version=1,
    )
    with pytest.raises(GovernedSourceFileError, match="not active"):
        store.read_bytes(
            tenant_id="tenant-a",
            project_id="company-profile",
            source_id="company-file-policy",
            version=1,
        )

    store.delete(
        tenant_id="tenant-a",
        project_id="company-profile",
        source_id="company-file-policy",
        version=1,
    )
    tombstone = store.get(
        tenant_id="tenant-a",
        project_id="company-profile",
        source_id="company-file-policy",
        version=1,
        include_inactive=True,
    )
    assert tombstone.state == "deleted"
    with pytest.raises(GovernedSourceFileError, match="not active"):
        store.read_bytes(
            tenant_id="tenant-a",
            project_id="company-profile",
            source_id="company-file-policy",
            version=1,
        )


def test_conflicting_same_version_is_rejected(tmp_path: Path) -> None:
    store = GovernedSourceFileStore(tmp_path / "source-files")
    store.store(
        tenant_id="tenant-a",
        project_id="company-profile",
        source_id="company-file-profile",
        version=1,
        filename="profile.pdf",
        mime_type="application/pdf",
        content=b"%PDF-1.7\nfirst",
    )
    with pytest.raises(GovernedSourceFileError, match="different bytes"):
        store.store(
            tenant_id="tenant-a",
            project_id="company-profile",
            source_id="company-file-profile",
            version=1,
            filename="profile.pdf",
            mime_type="application/pdf",
            content=b"%PDF-1.7\nsecond",
        )
