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
    assert video.adapter_id == "video.product-runtime.v1"

    web = classify_execution_route("Build a premium website for a furniture company")
    assert web.capability_id == "ilaios.capability.web-factory"
    assert web.adapter_id is None

    with pytest.raises(ExecutionCoordinatorError, match="could not be selected"):
        classify_execution_route("Make something excellent")
    with pytest.raises(ExecutionCoordinatorError, match="multiple capabilities"):
        classify_execution_route("Build a website and a launch video")


def test_unverified_finished_product_adapter_fails_closed(tmp_path: Path) -> None:
    coordinator, governance, _, _ = _coordinator(tmp_path)
    now = datetime(2026, 8, 14, 12, 0, tzinfo=timezone.utc)

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


def test_execution_decision_requires_independent_same_tenant_approver(
    tmp_path: Path,
) -> None:
    coordinator, _, _, _ = _coordinator(tmp_path)
    now = datetime(2026, 8, 14, 12, 0, tzinfo=timezone.utc)
    requester = "oidc|requester@example.test"
    tenant = "tenant/global-example"
    coordinator.prepare(
        "exec-approval-1",
        "Create a launch video and final MP4",
        token="token",
        principal_id=requester,
        tenant_id=tenant,
        now=now,
    )

    with pytest.raises(ExecutionCoordinatorError, match="independent human approver"):
        coordinator.decide(
            "exec-approval-1",
            approver_id=requester,
            tenant_id=tenant,
            decision="approved",
            now=now + timedelta(minutes=1),
        )
    with pytest.raises(ExecutionCoordinatorError, match="cross-tenant"):
        coordinator.decide(
            "exec-approval-1",
            approver_id="oidc|approver@example.test",
            tenant_id="tenant/other",
            decision="approved",
            now=now + timedelta(minutes=1),
        )

    assert coordinator.decide(
        "exec-approval-1",
        approver_id="oidc|approver@example.test",
        tenant_id=tenant,
        decision="approved",
        now=now + timedelta(minutes=1),
    ) == "APPROVED"


def test_denial_is_terminal_in_coordinator_and_governance(tmp_path: Path) -> None:
    coordinator, governance, _, _ = _coordinator(tmp_path)
    now = datetime(2026, 8, 14, 12, 0, tzinfo=timezone.utc)
    coordinator.prepare(
        "exec-denied-1",
        "Create a product video and final MP4",
        token="token",
        principal_id="oidc|requester@example.test",
        tenant_id="tenant/global-example",
        now=now,
    )

    status = coordinator.decide(
        "exec-denied-1",
        approver_id="oidc|approver@example.test",
        tenant_id="tenant/global-example",
        decision="denied",
        now=now + timedelta(minutes=1),
    )

    assert status == "DENIED"
    assert coordinator.get("exec-denied-1")["execution_status"] == "DENIED"
    assert governance.state()["work"] == [
        {
            "request_id": "exec-denied-1",
            "requester_id": "oidc|requester@example.test",
            "status": "denied",
        }
    ]
    with pytest.raises(ExecutionCoordinatorError, match="not resumable"):
        coordinator.resume(
            "exec-denied-1",
            token="token",
            now=now + timedelta(minutes=2),
        )


def test_video_execution_waits_for_approval_then_uses_fresh_lease_and_grant(
    tmp_path: Path,
) -> None:
    coordinator, governance, scheduler, grants = _coordinator(tmp_path)
    prepared_at = datetime(2026, 8, 14, 12, 0, tzinfo=timezone.utc)
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

    assert prepared["execution_status"] == "PENDING_APPROVAL"
    assert prepared["capability_id"] == "ilaios.capability.video-media-factory"
    assert scheduler.state()["leases"] == []
    work = governance.state()["work"]
    assert work == [
        {
            "request_id": "exec-video-1",
            "requester_id": principal_id,
            "status": "pending",
        }
    ]
    with pytest.raises(ExecutionCoordinatorError, match="approval"):
        coordinator.resume(
            "exec-video-1",
            token="token",
            now=prepared_at + timedelta(minutes=5),
        )

    assert coordinator.decide(
        "exec-video-1",
        approver_id="oidc|independent-product-owner",
        tenant_id=tenant_id,
        decision="approved",
        now=prepared_at + timedelta(minutes=5),
    ) == "APPROVED"
    manifest = coordinator.resume(
        "exec-video-1",
        token="token",
        now=prepared_at + timedelta(minutes=5),
    )

    assert manifest["accepted"] is True
    assert manifest["approval_proven"] is True
    assert manifest["worker_lease_proven"] is True
    assert manifest["grant_proven"] is True
    assert manifest["artifact_digest"] == manifest["delivery_sha256"]
    state = coordinator.get("exec-video-1")
    assert state["execution_status"] == "ACCEPTED"
    assert state["principal_id"] == principal_id
    assert state["tenant_id"] == tenant_id
    assert scheduler.state()["leases"]
    grant_state = grants.state()
    grant_rows = cast(list[dict[str, object]], grant_state["grants"])
    assert grant_rows[0]["used_side_effects"] == 1
