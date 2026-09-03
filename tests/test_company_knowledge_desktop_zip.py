from __future__ import annotations

import hashlib
import io
import zipfile
from pathlib import Path

import pytest

from services.company_knowledge_desktop import TenantCompanyKnowledgeRegistry
from services.company_knowledge_ingestion import CompanyKnowledgeIngestionError

_ZIP_MIME = "application/zip"


def _zip(entries: dict[str, str]) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, text in entries.items():
            archive.writestr(name, text)
    return output.getvalue()


def test_desktop_registry_accepts_safe_zip_and_retains_raw_bytes_across_restart(
    tmp_path: Path,
) -> None:
    root = tmp_path / "company-knowledge"
    content = _zip(
        {
            "profile.txt": "Acme Robotics builds warehouse robots in Bursa",
            "pricing.csv": "plan,price\nstandard,200",
        }
    )
    first = TenantCompanyKnowledgeRegistry(root)
    source = first.ingest(
        tenant_id="tenant-a",
        filename="company-files.zip",
        mime_type=_ZIP_MIME,
        content=content,
        content_sha256=hashlib.sha256(content).hexdigest(),
    )
    assert source["latest_version"] == 1

    restarted = TenantCompanyKnowledgeRegistry(root)
    result = restarted.runtime_for("tenant-a").retrieve(
        retrieval_id="zip-after-restart",
        query="warehouse robots Bursa",
        purpose="company-context",
        top_k=5,
        candidate_limit=10,
        max_context_chars=2000,
    )
    units = result["units"]
    assert isinstance(units, list) and units
    assert "warehouse robots" in str(units[0]["text"])

    retained = restarted.source_files.read_bytes(
        tenant_id="tenant-a",
        project_id="company-profile",
        source_id=str(source["source_id"]),
        version=1,
    )
    assert retained == content
    assert hashlib.sha256(retained).hexdigest() == hashlib.sha256(content).hexdigest()

    with pytest.raises(Exception):
        restarted.source_files.read_bytes(
            tenant_id="tenant-b",
            project_id="company-profile",
            source_id=str(source["source_id"]),
            version=1,
        )


def test_desktop_registry_rejects_unsafe_zip_through_canonical_extractor(
    tmp_path: Path,
) -> None:
    content = _zip({"../escape.txt": "must not be accepted"})
    registry = TenantCompanyKnowledgeRegistry(tmp_path / "company-knowledge")
    with pytest.raises(CompanyKnowledgeIngestionError):
        registry.ingest(
            tenant_id="tenant-a",
            filename="unsafe.zip",
            mime_type=_ZIP_MIME,
            content=content,
            content_sha256=hashlib.sha256(content).hexdigest(),
        )
