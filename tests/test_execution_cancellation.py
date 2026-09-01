"""Red-team tests for authenticated execution cancellation and cleanup."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from services.control_plane import ControlPlane, ControlPlaneConfig
from services.control_plane.workflows import WorkflowStore, WorkflowStoreConfig
from services.evidence import EvidenceStore
from services.execution_cancellation import (
    cancel_execution,
    cancellation_metrics,
    cleanup_terminal_resources,
)
from services.execution_coordinator import ExecutionCoordinator, ExecutionCoordinatorError
from services.governance import GovernedRuntimeGateway
from services.integrations import DeterministicLocalVideoRuntime, DurableVideoProductRuntime
from services.runtime import DurableGrantPolicy, DurableWorkerScheduler, GovernedRuntime


def _coordinator(
    tmp_path: Path,
) -> tuple[ExecutionCoordinator, DurableWorkerScheduler, DurableVideoProductRuntime]:
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
    coordinator = ExecutionCoordinator(
        tmp_path / "coordinator.sqlite3",
        control,
        governance,
        grants,
        product,
    )
    return coordinator, scheduler, product


def test_owned_admitted_video_can_be_cancelled_idempotently(tmp_path: Path) -> None:
    coordinator, scheduler, _ = _coordinator(tmp_path)
    now = datetime(2026, 8, 16, 1, 0, tzinfo=timezone.utc)
    principal = "oidc|user@example.test"
    tenant = "tenant/example"
    coordinator.prepare(
        "exec-cancel-1",
        "Create a launch video and final MP4",
        token="token",
        principal_id=principal,
        tenant_id=tenant,
        now=now,
    )
    assert len(scheduler.state()["workers"]) == 1

    cancelled = cancel_execution(
        coordinator,
        "exec-cancel-1",
        token="token",
        principal_id=principal,
        tenant_id=tenant,
        reason="user requested cancellation",
        now=now + timedelta(seconds=1),
    )
    assert cancelled["execution_status"] == "CANCELLED"
    assert cancelled["terminal"] is True
    assert cancelled["terminal_reason"] == "cancelled by authenticated owner"
    assert scheduler.state()["leases"] == []
    assert scheduler.state()["workers"] == []

    duplicate = cancel_execution(
        coordinator,
        "exec-cancel-1",
        token="token",
        principal_id=principal,
        tenant_id=tenant,
        reason="user requested cancellation",
        now=now + timedelta(seconds=2),
    )
    assert duplicate["execution_status"] == "CANCELLED"
    assert cancellation_metrics(coordinator)["cancelled"] == 1

    with sqlite3.connect(tmp_path / "product.sqlite3") as connection:
        product_status = connection.execute(
            "SELECT status FROM product_proofs WHERE request_id = ?",
            ("exec-cancel-1",),
        ).fetchone()
        product_closure = connection.execute(
            "SELECT terminal_status FROM product_proof_closure WHERE request_id = ?",
            ("exec-cancel-1",),
        ).fetchone()
    assert product_status == ("cancelled",)
    assert product_closure == ("cancelled",)

    with sqlite3.connect(tmp_path / "state.sqlite3") as connection:
        workflow_status = connection.execute(
            "SELECT status FROM workflows WHERE workflow_id = ?",
            ("proof-exec-cancel-1",),
        ).fetchone()
        job_status = connection.execute(
            "SELECT state FROM jobs WHERE job_id = ?",
            (str(cancelled["job_id"]),),
        ).fetchone()
    assert workflow_status == ("cancelled",)
    assert job_status == ("CANCELLED",)


def test_cross_tenant_cancellation_fails_closed(tmp_path: Path) -> None:
    coordinator, scheduler, _ = _coordinator(tmp_path)
    now = datetime(2026, 8, 16, 1, 0, tzinfo=timezone.utc)
    coordinator.prepare(
        "exec-cancel-tenant",
        "Create a launch video and final MP4",
        token="token",
        principal_id="oidc|owner@example.test",
        tenant_id="tenant/owner",
        now=now,
    )

    with pytest.raises(ExecutionCoordinatorError, match="cross-tenant"):
        cancel_execution(
            coordinator,
            "exec-cancel-tenant",
            token="token",
            principal_id="oidc|owner@example.test",
            tenant_id="tenant/other",
            reason="unauthorized cancellation",
            now=now + timedelta(seconds=1),
        )
    assert coordinator.get("exec-cancel-tenant")["execution_status"] == "ADMITTED"
    assert len(scheduler.state()["workers"]) == 1


def test_verified_acceptance_cannot_be_overwritten_by_cancel(tmp_path: Path) -> None:
    coordinator, scheduler, _ = _coordinator(tmp_path)
    now = datetime(2026, 8, 16, 1, 0, tzinfo=timezone.utc)
    principal = "oidc|user@example.test"
    tenant = "tenant/example"
    coordinator.prepare(
        "exec-cancel-accepted",
        "Create a launch video and final MP4",
        token="token",
        principal_id=principal,
        tenant_id=tenant,
        now=now,
    )
    manifest = coordinator.resume(
        "exec-cancel-accepted",
        token="token",
        now=now + timedelta(seconds=1),
    )
    assert manifest["accepted"] is True

    with pytest.raises(ExecutionCoordinatorError, match="immutable"):
        cancel_execution(
            coordinator,
            "exec-cancel-accepted",
            token="token",
            principal_id=principal,
            tenant_id=tenant,
            reason="too late",
            now=now + timedelta(seconds=2),
        )
    assert coordinator.get("exec-cancel-accepted")["execution_status"] == "ACCEPTED"
    assert cleanup_terminal_resources(coordinator) == 1
    assert scheduler.state()["workers"] == []
    assert cleanup_terminal_resources(coordinator) == 0


def test_terminal_cleanup_skips_worker_that_still_owns_a_lease(tmp_path: Path) -> None:
    coordinator, scheduler, product = _coordinator(tmp_path)
    now = datetime(2026, 8, 16, 1, 0, tzinfo=timezone.utc)
    coordinator.prepare(
        "exec-cleanup-lease",
        "Create a launch video and final MP4",
        token="token",
        principal_id="oidc|user@example.test",
        tenant_id="tenant/example",
        now=now,
    )
    with sqlite3.connect(tmp_path / "product.sqlite3") as connection:
        connection.execute(
            "UPDATE product_proofs SET status = 'failed' WHERE request_id = ?",
            ("exec-cleanup-lease",),
        )
        row = connection.execute(
            "SELECT job_id, worker_id FROM product_proofs WHERE request_id = ?",
            ("exec-cleanup-lease",),
        ).fetchone()
    assert row is not None
    lease = scheduler.schedule(str(row[0]), "video", now=now)

    assert cleanup_terminal_resources(coordinator) == 0
    assert len(scheduler.state()["workers"]) == 1
    assert scheduler.release(lease) is True
    assert cleanup_terminal_resources(coordinator) == 1
    assert scheduler.state()["workers"] == []
    assert product.get_state("exec-cleanup-lease")["status"] == "failed"
