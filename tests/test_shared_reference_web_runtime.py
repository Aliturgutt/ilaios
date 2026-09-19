"""E2E evidence for shared governed reference assets in Web Factory."""

from __future__ import annotations

import struct
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import cast

from services.control_plane import ControlPlane, ControlPlaneConfig
from services.control_plane.workflows import WorkflowStore, WorkflowStoreConfig
from services.evidence import EvidenceStore
from services.execution_adapters import register_web_runtime
from services.execution_coordinator import ExecutionCoordinator, ExecutionState
from services.governance import GovernedRuntimeGateway
from services.integrations import (
    DeterministicLocalVideoRuntime,
    DurableVideoProductRuntime,
    RecoverableWebProductRuntime,
)
from services.reference_asset_admission import ReferenceAssetAdmissionStore
from services.reference_assets import ReferenceAssetRole
from services.runtime import DurableGrantPolicy, DurableWorkerScheduler, GovernedRuntime


def _png(width: int = 64, height: int = 48) -> bytes:
    return (
        b"\x89PNG\r\n\x1a\n"
        + struct.pack(">I", 13)
        + b"IHDR"
        + struct.pack(">II", width, height)
        + b"\x08\x02\x00\x00\x00"
        + b"\x00\x00\x00\x00"
    )


def _runtime(
    tmp_path: Path,
) -> tuple[
    ExecutionCoordinator,
    ReferenceAssetAdmissionStore,
]:
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
    web = RecoverableWebProductRuntime(
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
    references = ReferenceAssetAdmissionStore(
        tmp_path / "reference-assets.sqlite3",
        tmp_path / "reference-assets" / "blobs",
    )
    return coordinator, references


def test_web_reference_is_rendered_and_bound_through_final_assurance(
    tmp_path: Path,
) -> None:
    coordinator, references = _runtime(tmp_path)
    principal_id = "oidc|shared-reference@example.test"
    tenant_id = "tenant/shared-reference"
    request_id = "web-shared-reference-1"
    content = _png(320, 180)
    asset = references.put(
        content=content,
        claimed_mime_type="image/png",
        original_filename="product-reference.png",
        role=ReferenceAssetRole.PRODUCT,
        instruction="Keep the product silhouette and logo placement consistent.",
        principal_id=principal_id,
        tenant_id=tenant_id,
    )

    now = datetime(2026, 8, 18, 15, 30, tzinfo=timezone.utc)
    prepared = coordinator.prepare(
        request_id,
        "Build a premium website for a furniture company with a contact form",
        token="token",
        principal_id=principal_id,
        tenant_id=tenant_id,
        now=now,
    )
    assert prepared["execution_status"] == ExecutionState.ADMITTED.value
    references.bind_request(
        request_id,
        (asset.asset_id,),
        principal_id=principal_id,
        tenant_id=tenant_id,
    )

    manifest = coordinator.resume(
        request_id,
        token="token",
        now=now + timedelta(seconds=1),
        principal_id=principal_id,
        tenant_id=tenant_id,
    )

    assert manifest["accepted"] is True
    assert manifest["reference_asset_usage"] == "asset-led-design-and-rendered-source"
    assert manifest["reference_asset_render_component"] == "components/PageShell.tsx"
    bound = cast(list[dict[str, object]], manifest["reference_assets"])
    assert bound[0]["asset_id"] == asset.asset_id
    assert bound[0]["sha256"] == asset.sha256
    design = cast(dict[str, object], manifest["design_strategy"])
    assert design["imagery_behavior"] == "asset-led"
    qa = cast(dict[str, object], manifest["qa"])
    assert qa["reference_assets_bound"] is True
    assert qa["reference_asset_rendered_source"] is True

    source_root = Path(cast(str, manifest["source_project_path"]))
    emitted = cast(list[dict[str, object]], manifest["reference_asset_source_files"])
    relative_path = cast(str, emitted[0]["source_path"])
    assert (source_root / relative_path).read_bytes() == content
    page_shell = (source_root / "components/PageShell.tsx").read_text(encoding="utf-8")
    assert "/reference-assets/reference-01-" in page_shell
    assert asset.sha256 in page_shell
    assert "referenceAssets.map" in page_shell


def test_web_reference_binding_rejects_wrong_execution_owner(tmp_path: Path) -> None:
    coordinator, references = _runtime(tmp_path)
    asset = references.put(
        content=_png(),
        claimed_mime_type="image/png",
        original_filename="private.png",
        role=ReferenceAssetRole.STYLE,
        instruction=None,
        principal_id="principal-a",
        tenant_id="tenant-a",
    )
    now = datetime(2026, 8, 18, 15, 30, tzinfo=timezone.utc)
    prepared = coordinator.prepare(
        "web-owner-mismatch",
        "Build a premium website for a furniture company",
        token="token",
        principal_id="principal-b",
        tenant_id="tenant-b",
        now=now,
    )
    assert prepared["execution_status"] == ExecutionState.ADMITTED.value

    # The shared store remains the authority: a reference from another tenant
    # cannot be rebound into this Web execution.
    try:
        references.bind_request(
            "web-owner-mismatch",
            (asset.asset_id,),
            principal_id="principal-b",
            tenant_id="tenant-b",
        )
    except ValueError:
        pass
    else:
        raise AssertionError("cross-tenant Web reference binding must fail closed")
