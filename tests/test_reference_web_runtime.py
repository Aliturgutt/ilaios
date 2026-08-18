from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import cast

from services.control_plane import ControlPlane, ControlPlaneConfig
from services.control_plane.workflows import WorkflowStore, WorkflowStoreConfig
from services.evidence import EvidenceStore
from services.execution_adapters import register_web_runtime
from services.execution_coordinator import ExecutionCoordinator, ExecutionState
from services.governance import GovernedRuntimeGateway
from services.integrations import DeterministicLocalVideoRuntime, DurableVideoProductRuntime
from services.integrations.reference_web_product_runtime import (
    ReferenceAwareRecoverableWebProductRuntime,
)
from services.reference_assets import configure_reference_asset_store
from services.runtime import DurableGrantPolicy, DurableWorkerScheduler, GovernedRuntime


def _png(width: int = 320, height: int = 180) -> bytes:
    return (
        b"\x89PNG\r\n\x1a\n"
        + (13).to_bytes(4, "big")
        + b"IHDR"
        + width.to_bytes(4, "big")
        + height.to_bytes(4, "big")
        + b"\x08\x06\x00\x00\x00"
        + b"\x00" * 32
    )


def test_reference_image_is_bound_through_web_factory_acceptance(tmp_path: Path) -> None:
    state = tmp_path / "state.sqlite3"
    control = ControlPlane(ControlPlaneConfig(state, "token"))
    workflows = WorkflowStore(WorkflowStoreConfig(state))
    scheduler = DurableWorkerScheduler(state, lease_duration=timedelta(seconds=30))
    grants = DurableGrantPolicy(state)
    evidence = EvidenceStore(tmp_path / "evidence")
    governance = GovernedRuntimeGateway(
        tmp_path / "governance.sqlite3",
        GovernedRuntime(state),
        hard_cap_minor=100,
    )
    video = DeterministicLocalVideoRuntime(
        tmp_path / "video", grants, governance, evidence
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
    web = ReferenceAwareRecoverableWebProductRuntime(
        tmp_path / "web-product.sqlite3",
        control,
        grants,
        governance,
        tmp_path / "web",
    )
    coordinator = ExecutionCoordinator(
        tmp_path / "coordinator.sqlite3",
        control,
        governance,
        grants,
        video_product,
        evidence,
    )
    register_web_runtime(coordinator, web)

    store = configure_reference_asset_store(
        tmp_path / "reference-assets.sqlite3",
        tmp_path / "reference-assets",
    )
    principal_id = "oidc|reference-web@example.test"
    tenant_id = "tenant/reference-web"
    request_id = "web-reference-e2e"
    record = store.ingest(
        principal_id=principal_id,
        tenant_id=tenant_id,
        original_name="product-reference.png",
        media_type="image/png",
        content=_png(),
    )
    store.bind_request(
        request_id,
        [record.asset_id],
        principal_id=principal_id,
        tenant_id=tenant_id,
    )

    now = datetime(2026, 8, 18, 10, 0, tzinfo=timezone.utc)
    prepared = coordinator.prepare(
        request_id,
        "Build a premium responsive website for a product company with a contact form",
        token="token",
        principal_id=principal_id,
        tenant_id=tenant_id,
        now=now,
    )
    assert prepared["execution_status"] == ExecutionState.ADMITTED.value
    job_id = cast(str, prepared["job_id"])
    store.attach_job(request_id, job_id)

    manifest = coordinator.resume(
        request_id,
        token="token",
        now=now + timedelta(seconds=1),
        principal_id=principal_id,
        tenant_id=tenant_id,
    )

    assert manifest["accepted"] is True
    assert manifest["reference_asset_usage"] == "asset-led-design-and-source"
    assert manifest["reference_asset_rendered"] is True
    references = cast(list[dict[str, object]], manifest["reference_assets"])
    assert references[0]["asset_id"] == record.asset_id
    assert references[0]["sha256"] == record.sha256
    render_paths = cast(list[str], manifest["reference_asset_render_paths"])
    assert len(render_paths) == 1
    assert render_paths[0].startswith("/reference-assets/reference-01-")
    design = cast(dict[str, object], manifest["design_strategy"])
    assert design["imagery_behavior"] == "asset-led"

    source_root = Path(cast(str, manifest["source_project_path"]))
    reference_files = list((source_root / "public/reference-assets").glob("reference-*.png"))
    assert len(reference_files) == 1
    assert reference_files[0].read_bytes() == _png()
    page_shell = (source_root / "components/PageShell.tsx").read_text(encoding="utf-8")
    assert "reference-gallery" in page_shell
    assert "<img" in page_shell
    assert render_paths[0] in page_shell
    source_manifest = json.loads(
        (source_root / "public/reference-assets/manifest.json").read_text(encoding="utf-8")
    )
    assert source_manifest["usage"] == "asset-led-design-and-source"
    assert source_manifest["rendered"] is True
    assert source_manifest["render_paths"] == render_paths
    assert source_manifest["assets"][0]["sha256"] == record.sha256
