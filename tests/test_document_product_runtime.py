from __future__ import annotations

import csv
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
    assert len(artifacts) == 4
    assert {str(item["artifact_type"]) for item in artifacts} == {
        "document.pdf",
        "document.docx",
        "document.xlsx",
        "document.csv",
    }

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

    xlsx = restarted.read(
        artifact_id="artifact_board-report.xlsx",
        version_id="v1",
        tenant_id="tenant-a",
        project_id="project-a",
    )
    with zipfile.ZipFile(io.BytesIO(xlsx)) as archive:
        assert {
            "[Content_Types].xml",
            "_rels/.rels",
            "xl/workbook.xml",
            "xl/_rels/workbook.xml.rels",
            "xl/worksheets/sheet1.xml",
        } <= set(archive.namelist())
        worksheet = archive.read("xl/worksheets/sheet1.xml")
        ET.fromstring(worksheet)
        assert b"Board Report" in worksheet
        assert b"Revenue increased." in worksheet

    csv_output = restarted.read(
        artifact_id="artifact_board-report.csv",
        version_id="v1",
        tenant_id="tenant-a",
        project_id="project-a",
    )
    rows = list(csv.reader(io.StringIO(csv_output.decode("utf-8"))))
    assert rows == [
        ["Board Report"],
        ["Revenue increased."],
        ["Next action: validate retention."],
    ]

    with pytest.raises(ArtifactOutputError, match="scope mismatch"):
        restarted.read(
            artifact_id="artifact_board-report.xlsx",
            version_id="v1",
            tenant_id="tenant-b",
            project_id="project-a",
        )


def test_csv_output_neutralizes_formula_prefixes(tmp_path: Path) -> None:
    outputs = GovernedArtifactOutputStore(tmp_path / "objects", tmp_path / "artifacts.sqlite")
    runtime = DocumentProductRuntime(outputs)
    runtime.create(
        artifact_id="artifact-formula-guard",
        version_id="v1",
        tenant_id="tenant-a",
        project_id="project-a",
        job_id="job-a",
        title="=SUM(A1:A2)",
        body="+cmd\n-safe\n@external",
    )
    csv_output = outputs.read(
        artifact_id="artifact-formula-guard.csv",
        version_id="v1",
        tenant_id="tenant-a",
        project_id="project-a",
    )
    rows = list(csv.reader(io.StringIO(csv_output.decode("utf-8"))))
    assert rows == [["'=SUM(A1:A2)"], ["'+cmd"], ["'-safe"], ["'@external"]]


def test_artifact_versions_are_immutable(tmp_path: Path) -> None:
    outputs = GovernedArtifactOutputStore(tmp_path / "objects", tmp_path / "artifacts.sqlite")
    outputs.put(
        artifact_id="artifact-a.pdf",
        version_id="v1",
        tenant_id="tenant-a",
        project_id="project-a",
        job_id="job-a",
        artifact_type="document.pdf",
        mime_type="application/pdf",
        content=b"first",
    )
    with pytest.raises(ArtifactOutputError, match="immutable"):
        outputs.put(
            artifact_id="artifact-a.pdf",
            version_id="v1",
            tenant_id="tenant-a",
            project_id="project-a",
            job_id="job-a",
            artifact_type="document.pdf",
            mime_type="application/pdf",
            content=b"second",
        )
