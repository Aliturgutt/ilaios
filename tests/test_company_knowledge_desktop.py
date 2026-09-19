from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pytest

from services.company_knowledge_desktop import TenantCompanyKnowledgeRegistry
from services.company_knowledge_ingestion import CompanyKnowledgeIngestionError

_DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def _docx(text: str) -> bytes:
    document_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        '<w:body><w:p><w:r><w:t>' + text + '</w:t></w:r></w:p></w:body></w:document>'
    )
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("word/document.xml", document_xml)
    return output.getvalue()


def _ingest(
    registry: TenantCompanyKnowledgeRegistry,
    *,
    tenant_id: str,
    filename: str,
    text: str,
) -> dict[str, object]:
    content = _docx(text)
    import hashlib

    return registry.ingest(
        tenant_id=tenant_id,
        filename=filename,
        mime_type=_DOCX_MIME,
        content=content,
        content_sha256=hashlib.sha256(content).hexdigest(),
    )


def test_company_document_survives_registry_and_runtime_restart(tmp_path: Path) -> None:
    root = tmp_path / "company-knowledge"
    first_registry = TenantCompanyKnowledgeRegistry(root)
    source = _ingest(
        first_registry,
        tenant_id="tenant-a",
        filename="company-profile.docx",
        text="Acme Robotics manufactures warehouse picking robots in Bursa",
    )
    assert source["latest_version"] == 1

    restarted_registry = TenantCompanyKnowledgeRegistry(root)
    runtime = restarted_registry.runtime_for("tenant-a")
    result = runtime.retrieve(
        retrieval_id="after-restart",
        query="warehouse picking robots Bursa",
        purpose="company-context",
        top_k=5,
        candidate_limit=10,
        max_context_chars=2000,
    )
    units = result["units"]
    assert isinstance(units, list)
    assert len(units) == 1
    assert units[0]["source_id"] == source["source_id"]
    assert "warehouse picking robots" in str(units[0]["text"])
    assert runtime.verify()["event_chain"] == "verified"


def test_same_company_filename_creates_canonical_new_source_version(tmp_path: Path) -> None:
    registry = TenantCompanyKnowledgeRegistry(tmp_path / "company-knowledge")
    first = _ingest(
        registry,
        tenant_id="tenant-a",
        filename="pricing.docx",
        text="Standard plan costs one hundred lira",
    )
    second = _ingest(
        registry,
        tenant_id="tenant-a",
        filename="pricing.docx",
        text="Standard plan costs two hundred lira",
    )
    assert first["source_id"] == second["source_id"]
    assert first["latest_version"] == 1
    assert second["latest_version"] == 2

    result = registry.runtime_for("tenant-a").retrieve(
        retrieval_id="latest-pricing",
        query="standard plan two hundred lira",
        purpose="company-context",
        top_k=5,
        candidate_limit=10,
        max_context_chars=2000,
    )
    units = result["units"]
    assert isinstance(units, list)
    assert units
    assert "two hundred lira" in str(units[0]["text"])
    assert "one hundred lira" not in str(units[0]["text"])


def test_tenants_with_same_filename_are_isolated_by_server_owned_runtime_scope(
    tmp_path: Path,
) -> None:
    registry = TenantCompanyKnowledgeRegistry(tmp_path / "company-knowledge")
    _ingest(
        registry,
        tenant_id="tenant-a",
        filename="profile.docx",
        text="Tenant Alpha makes ceramic tiles",
    )
    _ingest(
        registry,
        tenant_id="tenant-b",
        filename="profile.docx",
        text="Tenant Beta makes medical sensors",
    )

    alpha = registry.runtime_for("tenant-a").retrieve(
        retrieval_id="alpha",
        query="ceramic tiles",
        purpose="company-context",
        top_k=5,
        candidate_limit=10,
        max_context_chars=2000,
    )
    beta = registry.runtime_for("tenant-b").retrieve(
        retrieval_id="beta",
        query="medical sensors",
        purpose="company-context",
        top_k=5,
        candidate_limit=10,
        max_context_chars=2000,
    )
    alpha_units = alpha["units"]
    beta_units = beta["units"]
    assert isinstance(alpha_units, list) and isinstance(beta_units, list)
    assert "Tenant Alpha" in str(alpha_units[0]["text"])
    assert "Tenant Beta" not in str(alpha_units[0]["text"])
    assert "Tenant Beta" in str(beta_units[0]["text"])
    assert registry.runtime_for("tenant-a").tenant_id == "tenant-a"
    assert registry.runtime_for("tenant-b").tenant_id == "tenant-b"


def test_registry_rejects_non_document_mime_without_creating_runtime(tmp_path: Path) -> None:
    registry = TenantCompanyKnowledgeRegistry(tmp_path / "company-knowledge")
    with pytest.raises(CompanyKnowledgeIngestionError, match="unsupported"):
        registry.ingest(
            tenant_id="tenant-a",
            filename="page.html",
            mime_type="text/html",
            content=b"<html>not a company document</html>",
            content_sha256="0" * 64,
        )
