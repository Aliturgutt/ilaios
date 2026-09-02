from __future__ import annotations

import hashlib
import io
import zipfile
from pathlib import Path

from services.company_knowledge_desktop import TenantCompanyKnowledgeRegistry

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


def _ingest(registry: TenantCompanyKnowledgeRegistry, *, tenant_id: str, filename: str, text: str):
    content = _docx(text)
    source = registry.ingest(
        tenant_id=tenant_id,
        filename=filename,
        mime_type=_DOCX_MIME,
        content=content,
        content_sha256=hashlib.sha256(content).hexdigest(),
    )
    return source, content


def test_company_upload_retains_exact_raw_bytes_across_restart(tmp_path: Path) -> None:
    root = tmp_path / "company-knowledge"
    first = TenantCompanyKnowledgeRegistry(root)
    source, content = _ingest(
        first,
        tenant_id="tenant-a",
        filename="company-profile.docx",
        text="Acme Robotics manufactures warehouse robots",
    )
    version = int(source["latest_version"])

    restarted = TenantCompanyKnowledgeRegistry(root)
    retained = restarted.source_files.read_bytes(
        tenant_id="tenant-a",
        project_id="company-profile",
        source_id=str(source["source_id"]),
        version=version,
    )
    assert retained == content
    assert hashlib.sha256(retained).hexdigest() == hashlib.sha256(content).hexdigest()


def test_company_raw_versions_follow_canonical_knowledge_versions(tmp_path: Path) -> None:
    registry = TenantCompanyKnowledgeRegistry(tmp_path / "company-knowledge")
    first, first_bytes = _ingest(
        registry,
        tenant_id="tenant-a",
        filename="pricing.docx",
        text="Standard plan costs one hundred lira",
    )
    second, second_bytes = _ingest(
        registry,
        tenant_id="tenant-a",
        filename="pricing.docx",
        text="Standard plan costs two hundred lira",
    )
    assert first["source_id"] == second["source_id"]
    assert first["latest_version"] == 1
    assert second["latest_version"] == 2

    records = registry.source_files.list_versions(
        tenant_id="tenant-a",
        project_id="company-profile",
        source_id=str(first["source_id"]),
    )
    assert [record.version for record in records] == [2, 1]
    assert registry.source_files.read_bytes(
        tenant_id="tenant-a",
        project_id="company-profile",
        source_id=str(first["source_id"]),
        version=1,
    ) == first_bytes
    assert registry.source_files.read_bytes(
        tenant_id="tenant-a",
        project_id="company-profile",
        source_id=str(first["source_id"]),
        version=2,
    ) == second_bytes


def test_same_filename_raw_bytes_are_tenant_isolated(tmp_path: Path) -> None:
    registry = TenantCompanyKnowledgeRegistry(tmp_path / "company-knowledge")
    alpha, alpha_bytes = _ingest(
        registry,
        tenant_id="tenant-a",
        filename="profile.docx",
        text="Tenant Alpha makes ceramic tiles",
    )
    beta, beta_bytes = _ingest(
        registry,
        tenant_id="tenant-b",
        filename="profile.docx",
        text="Tenant Beta makes medical sensors",
    )
    assert alpha["source_id"] == beta["source_id"]
    assert registry.source_files.read_bytes(
        tenant_id="tenant-a",
        project_id="company-profile",
        source_id=str(alpha["source_id"]),
        version=1,
    ) == alpha_bytes
    assert registry.source_files.read_bytes(
        tenant_id="tenant-b",
        project_id="company-profile",
        source_id=str(beta["source_id"]),
        version=1,
    ) == beta_bytes
