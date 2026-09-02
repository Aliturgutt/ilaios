from __future__ import annotations

import io
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import pytest

from services.artifact_outputs import ArtifactOutputError, GovernedArtifactOutputStore
from services.integrations.document_product_runtime import DocumentProductRuntime


def test_creative_document_outputs_are_openable_persistent_and_scoped(tmp_path: Path) -> None:
    outputs = GovernedArtifactOutputStore(tmp_path / "objects", tmp_path / "artifacts.sqlite")
    runtime = DocumentProductRuntime(outputs)
    manifest = runtime.create(
        artifact_id="artifact_board-report",
        version_id="v1",
        tenant_id="tenant-a",
        project_id="project-a",
        job_id="job-a",
        title="Board Report",
        body="Revenue increased.\nNext action: validate retention.",
    )

    assert manifest["capability_id"] == "ilaios.capability.creative-document"
    assert manifest["status"] == "ACCEPTED"
    artifacts = manifest["artifacts"]
    assert isinstance(artifacts, list)
    assert len(artifacts) == 2

    restarted = GovernedArtifactOutputStore(tmp_path / "objects", tmp_path / "artifacts.sqlite")
    pdf = restarted.read(
        artifact_id="artifact_board-report.pdf",
        version_id="v1",
        tenant_id="tenant-a",
        project_id="project-a",
    )
    assert pdf.startswith(b"%PDF-1.4")
    assert b"xref\n" in pdf and pdf.rstrip().endswith(b"%%EOF")

    docx = restarted.read(
        artifact_id="artifact_board-report.docx",
        version_id="v1",
        tenant_id="tenant-a",
        project_id="project-a",
    )
    with zipfile.ZipFile(io.BytesIO(docx)) as archive:
        assert {"[Content_Types].xml", "_rels/.rels", "word/document.xml"} <= set(archive.namelist())
        document = archive.read("word/document.xml")
        ET.fromstring(document)
        assert b"Board Report" in document

    with pytest.raises(ArtifactOutputError, match="scope mismatch"):
        restarted.read(
            artifact_id="artifact_board-report.docx",
            version_id="v1",
            tenant_id="tenant-b",
            project_id="project-a",
        )


def test_artifact_versions_are_immutable(tmp_path: Path) -> None:
    outputs = GovernedArtifactOutputStore(tmp_path / "objects", tmp_path / "artifacts.sqlite")
    common = dict(
        artifact_id="artifact-a.pdf",
        version_id="v1",
        tenant_id="tenant-a",
        project_id="project-a",
        job_id="job-a",
        artifact_type="document.pdf",
        mime_type="application/pdf",
    )
    outputs.put(**common, content=b"first")
    with pytest.raises(ArtifactOutputError, match="immutable"):
        outputs.put(**common, content=b"second")
