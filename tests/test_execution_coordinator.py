"""Execution coordinator tests for the canonical one-prompt product path."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import cast

import pytest

from services.control_plane import ControlPlane, ControlPlaneConfig
from services.control_plane.workflows import WorkflowStore, WorkflowStoreConfig
from services.evidence import EvidenceStore
from services.execution_coordinator import (
    ExecutionCoordinator,
    ExecutionCoordinatorError,
    classify_execution_route,
)
from services.governance import GovernedRuntimeGateway
from services.integrations import DeterministicLocalVideoRuntime, DurableVideoProductRuntime
from services.runtime import DurableGrantPolicy, DurableWorkerScheduler, GovernedRuntime


def _coordinator(
    tmp_path: Path,
) -> tuple[
    ExecutionCoordinator,
    GovernedRuntimeGateway,
    DurableWorkerScheduler,
    DurableGrantPolicy,
]:
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
    video = DeterministicLocalVideoRuntime(
        tmp_path / "video",
        grants,
        governance,
        EvidenceStore(tmp_path / "evidence"),
    )
    product = DurableVideoProductRuntime(
        tmp_path / "product.sqlite3",
        control,
        workflows,
        scheduler,
        grants,
        governance,
        video,
    )
    return (
        ExecutionCoordinator(
            tmp_path / "coordinator.sqlite3",
            control,
            governance,
            grants,
            product,
        ),
        governance,
        scheduler,
        grants,
    )


def test_route_selection_is_conservative_and_canonical() -> None:
    video = classify_execution_route("Create a 60 second launch video and final MP4")
    assert video.capability_id == "ilaios.capability.video-media-factory"
    assert video.adapter_id is None

    web = classify_execution_route("Build a premium website for a furniture company")
    assert web.capability_id == "ilaios.capability.web-factory"
    assert web.adapter_id is None

    with pytest.raises(ExecutionCoordinatorError, match="could not be selected"):
        classify_execution_route("Make something excellent")
    with pytest.raises(ExecutionCoordinatorError, match="multiple capabilities"):
        classify_execution_route("Build a website and a launch video")


def test_unverified_finished_product_adapter_fails_closed(tmp_path: Path) -> None:
    coordinator, governance, _, _ = _coordinator(tmp_path)
    now = datetime(2026, 8, 15, 8, 0, tzinfo=timezone.utc)

    prepared = coordinator.prepare(
        "exec-web-1",
        "Build a premium website for my furniture company",
        token="token",
        principal_id="oidc|user@example.test",
        tenant_id="tenant/example",
        now=now,
    )

    assert prepared["capability_id"] == "ilaios.capability.web-factory"
    assert prepared["adapter_id"] is None
    assert prepared["execution_status"] == "BLOCKED_ADAPTER_UNAVAILABLE"
    assert governance.state()["work"] == []
    with pytest.raises(ExecutionCoordinatorError, match="not resumable"):
        coordinator.resume("exec-web-1", token="token", now=now)


def test_medium_video_is_admitted_without_human_approval_or_early_lease(
    tmp_path: Path,
) -> None:
    coordinator, governance, scheduler, _ = _coordinator(tmp_path)
    prepared_at = datetime(2026, 8, 15, 8, 0, tzinfo=timezone.utc)
    principal_id = "oidc|subject:user@example.test"
    tenant_id = "tenant/global-example"

    prepared = coordinator.prepare(
        "exec-video-1",
        "Create a short launch video and deliver the final MP4",
        token="token",
        principal_id=principal_id,
        tenant_id=tenant_id,
        now=prepared_at,
    )

    assert prepared["execution_status"] == "ADMITTED"
    assert prepared["capability_id"] == "ilaios.capability.video-media-factory"
    assert prepared["adapter_id"] == "video.product-runtime.v1"
    assert scheduler.state()["leases"] == []
    assert governance.approval_proven("exec-video-1") is False
    assert governance.admission_snapshot("exec-video-1") == {
        "risk": "medium",
        "admission_decision": "ALLOW",
        "human_approval_required": False,
        "approval_proven": False,
        "admission_proven": True,
    }
    with pytest.raises(ExecutionCoordinatorError, match="not awaiting approval"):
        coordinator.decide(
            "exec-video-1",
            approver_id="oidc|approver@example.test",
            tenant_id=tenant_id,
            decision="approved",
            now=prepared_at + timedelta(seconds=1),
        )


def test_medium_video_executes_to_verified_acceptance_with_fresh_grant_and_lease(
    tmp_path: Path,
) -> None:
    coordinator, governance, scheduler, grants = _coordinator(tmp_path)
    prepared_at = datetime(2026, 8, 15, 8, 0, tzinfo=timezone.utc)
    principal_id = "oidc|subject:user@example.test"
    tenant_id = "tenant/global-example"

    coordinator.prepare(
        "exec-video-2",
        "Create a short launch video and deliver the final MP4",
        token="token",
        principal_id=principal_id,
        tenant_id=tenant_id,
        now=prepared_at,
    )
    manifest = coordinator.resume(
        "exec-video-2",
        token="token",
        now=prepared_at + timedelta(seconds=1),
    )

    assert manifest["accepted"] is True
    assert manifest["risk"] == "medium"
    assert manifest["admission_decision"] == "ALLOW"
    assert manifest["admission_proven"] is True
    assert manifest["human_approval_required"] is False
    assert manifest["approval_proven"] is False
    assert manifest["worker_lease_proven"] is True
    assert manifest["grant_proven"] is True
    assert manifest["artifact_digest"] == manifest["delivery_sha256"]
    state = coordinator.get("exec-video-2")
    assert state["execution_status"] == "ACCEPTED"
    assert state["principal_id"] == principal_id
    assert state["tenant_id"] == tenant_id
    assert governance.admission_proven("exec-video-2") is True
    assert scheduler.state()["leases"]
    grant_state = grants.state()
    grant_rows = cast(list[dict[str, object]], grant_state["grants"])
    assert grant_rows[0]["used_side_effects"] == 1


def test_execution_is_single_use_after_acceptance(tmp_path: Path) -> None:
    coordinator, _, _, _ = _coordinator(tmp_path)
    now = datetime(2026, 8, 15, 8, 0, tzinfo=timezone.utc)
    coordinator.prepare(
        "exec-video-3",
        "Create a launch video and final MP4",
        token="token",
        principal_id="oidc|user@example.test",
        tenant_id="tenant/example",
        now=now,
    )
    first = coordinator.resume(
        "exec-video-3", token="token", now=now + timedelta(seconds=1)
    )
    second = coordinator.resume(
        "exec-video-3", token="token", now=now + timedelta(seconds=2)
    )
    assert second == first
