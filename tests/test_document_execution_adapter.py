"""Creative/Document coordinator E2E for governed PDF, DOCX, XLSX, CSV, and PPTX outputs."""

from __future__ import annotations

import csv
import io
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from services.artifact_outputs import ArtifactOutputError, GovernedArtifactOutputStore
from services.control_plane import ControlPlane, ControlPlaneConfig
from services.control_plane.workflows import WorkflowStore, WorkflowStoreConfig
from services.document_execution_adapter import register_document_runtime
from services.evidence import EvidenceStore
from services.execution_coordinator import ExecutionCoordinator, ExecutionState
from services.governance import GovernedRuntimeGateway
from services.integrations import DeterministicLocalVideoRuntime, DurableVideoProductRuntime
from services.integrations.document_product_runtime import DocumentProductRuntime
from services.runtime import DurableGrantPolicy, DurableWorkerScheduler, GovernedRuntime


_DOCUMENT = "ilaios.capability.creative-document"


def _stack(
    tmp_path: Path,
) -> tuple[ExecutionCoordinator, GovernedArtifactOutputStore]:
    state = tmp_path / "state.sqlite3"
    control = ControlPlane(ControlPlaneConfig(state, "token"))
    workflows = WorkflowStore(WorkflowStoreConfig(state))
    scheduler = DurableWorkerScheduler(state, lease_duration=timedelta(seconds=30))
    grants = DurableGrantPolicy(state)
    governance = GovernedRuntimeGateway(
        tmp_path / "governance.sqlite3",
        GovernedRuntime(state),
        hard_cap_minor=100,
    )
    evidence = EvidenceStore(tmp_path / "evidence")
    video = DeterministicLocalVideoRuntime(
        tmp_path / "video",
        grants,
        governance,
        evidence,
    )
    video_product = DurableVideoProductRuntime(
        tmp_path / "video-product.sqlite3",
        control,
        workflows,
        scheduler,
        grants,
        governance,
        video,
    )
    coordinator = ExecutionCoordinator(
        tmp_path / "coordinator.sqlite3",
        control,
        governance,
        grants,
        video_product,
        evidence,
    )
    outputs = GovernedArtifactOutputStore(
        tmp_path / "outputs",
        tmp_path / "outputs.sqlite3",
    )
    register_document_runtime(
        coordinator,
        database_path=tmp_path / "document-adapter.sqlite3",
        control_plane=control,
        governance=governance,
        runtime=DocumentProductRuntime(outputs),
    )
    return coordinator, outputs


def test_document_outputs_flow_through_coordinator_and_remain_tenant_scoped(
    tmp_path: Path,
) -> None:
    coordinator, outputs = _stack(tmp_path)
    now = datetime(2026, 9, 3, 9, 0, tzinfo=timezone.utc)
    request_id = "document-e2e-1"
    tenant_id = "tenant/company-a"
    principal_id = "oidc|document@example.test"
    objective = "Write a report for the company knowledge closure with verified evidence."

    prepared = coordinator.prepare(
        request_id,
        objective,
        token="token",
        principal_id=principal_id,
        tenant_id=tenant_id,
        now=now,
    )
    assert prepared["execution_status"] == ExecutionState.ADMITTED.value
    assert prepared["capability_id"] == _DOCUMENT
    assert prepared["adapter_id"] == "document.product-runtime.pdf-docx-xlsx-csv-pptx.v1"

    manifest = coordinator.resume(
        request_id,
        token="token",
        now=now + timedelta(seconds=1),
        principal_id=principal_id,
        tenant_id=tenant_id,
    )
    assert manifest["accepted"] is True
    assert manifest["final_disposition"] == "ACCEPT"
    assert manifest["evidence_scope"] == "GOVERNED_PDF_DOCX_XLSX_CSV_PPTX_FILES_OUTPUTS"
    assert manifest["tenant_id"] == tenant_id
    assert manifest["project_id"] == f"execution/{request_id}"
    artifacts = manifest["artifacts"]
    assert isinstance(artifacts, list)
    assert len(artifacts) == 5
    by_type = {str(item["artifact_type"]): item for item in artifacts}
    assert set(by_type) == {
        "document.pdf",
        "document.docx",
        "document.xlsx",
        "document.csv",
        "document.pptx",
    }

    pdf = outputs.read(
        artifact_id=f"{request_id}.pdf",
        version_id="v1",
        tenant_id=tenant_id,
        project_id=f"execution/{request_id}",
    )
    assert pdf.startswith(b"%PDF-1.4")

    docx = outputs.read(
        artifact_id=f"{request_id}.docx",
        version_id="v1",
        tenant_id=tenant_id,
        project_id=f"execution/{request_id}",
    )
    docx_path = tmp_path / "reopened.docx"
    docx_path.write_bytes(docx)
    with zipfile.ZipFile(docx_path) as archive:
        document_xml = archive.read("word/document.xml")
    assert b"company knowledge closure" in document_xml

    xlsx = outputs.read(
        artifact_id=f"{request_id}.xlsx",
        version_id="v1",
        tenant_id=tenant_id,
        project_id=f"execution/{request_id}",
    )
    with zipfile.ZipFile(io.BytesIO(xlsx)) as archive:
        sheet_xml = archive.read("xl/worksheets/sheet1.xml")
    assert b"company knowledge closure" in sheet_xml

    csv_output = outputs.read(
        artifact_id=f"{request_id}.csv",
        version_id="v1",
        tenant_id=tenant_id,
        project_id=f"execution/{request_id}",
    )
    rows = list(csv.reader(io.StringIO(csv_output.decode("utf-8"))))
    assert rows
    assert "company knowledge closure" in rows[-1][0]

    pptx = outputs.read(
        artifact_id=f"{request_id}.pptx",
        version_id="v1",
        tenant_id=tenant_id,
        project_id=f"execution/{request_id}",
    )
    with zipfile.ZipFile(io.BytesIO(pptx)) as archive:
        slide_xml = archive.read("ppt/slides/slide1.xml")
    assert b"company knowledge closure" in slide_xml

    for suffix in ("pdf", "docx", "xlsx", "csv", "pptx"):
        with pytest.raises(ArtifactOutputError, match="artifact scope mismatch"):
            outputs.read(
                artifact_id=f"{request_id}.{suffix}",
                version_id="v1",
                tenant_id="tenant/company-b",
                project_id=f"execution/{request_id}",
            )

    accepted = coordinator.get(
        request_id,
        principal_id=principal_id,
        tenant_id=tenant_id,
    )
    assert accepted["execution_status"] == ExecutionState.ACCEPTED.value
    assert accepted["result_sha256"]
