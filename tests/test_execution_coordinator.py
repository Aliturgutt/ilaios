"""Execution coordinator tests for the canonical one-prompt product path."""

from __future__ import annotations

import sqlite3
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
from services.integrations.product_runtime import (
    ProductFinalizationPending,
    ProductRuntimeError,
)
from services.runtime import (
    DurableGrantPolicy,
    DurableWorkerScheduler,
    GovernedRuntime,
    GrantError,
)


def _coordinator(
    tmp_path: Path,
) -> tuple[
    ExecutionCoordinator,
    GovernedRuntimeGateway,
    DurableWorkerScheduler,
    DurableGrantPolicy,
    DurableVideoProductRuntime,
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
        product,
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
    coordinator, governance, _, _, _ = _coordinator(tmp_path)
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
    assert prepared["execution_status"] == "BLOCKED"
    assert prepared["blocker_code"] == "GENERAL_PURPOSE_WEB_ADAPTER_UNAVAILABLE"
    assert governance.state()["work"] == []
    with pytest.raises(ExecutionCoordinatorError, match="not resumable"):
        coordinator.resume("exec-web-1", token="token", now=now)


def test_medium_video_is_admitted_without_human_approval_or_early_lease(
    tmp_path: Path,
) -> None:
    coordinator, governance, scheduler, _, _ = _coordinator(tmp_path)
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
    coordinator, governance, scheduler, grants, _ = _coordinator(tmp_path)
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
    assert manifest["requester_id"] == principal_id
    assert manifest["tenant_id"] == tenant_id
    assert manifest["identity_proven"] is True
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
    assert state["terminal"] is True
    assert state["terminal_reason"] == "finished product and acceptance evidence verified"
    assert isinstance(state["result_sha256"], str)
    assert len(state["result_sha256"]) == 64
    assert governance.admission_proven("exec-video-2") is True
    assert scheduler.state()["leases"] == []
    assert not (tmp_path / "video" / "exec-video-2").exists()
    grant_state = grants.state()
    grant_rows = cast(list[dict[str, object]], grant_state["grants"])
    assert grant_rows[0]["used_side_effects"] == 1
    revoked = cast(list[dict[str, object]], grant_state["revoked"])
    assert revoked[0]["grant_id"] == grant_rows[0]["grant_id"]


def test_execution_is_single_use_after_acceptance(tmp_path: Path) -> None:
    coordinator, _, _, _, _ = _coordinator(tmp_path)
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


def test_failure_closes_product_execution_and_releases_resources(tmp_path: Path) -> None:
    coordinator, _, scheduler, grants, _ = _coordinator(tmp_path)
    now = datetime(2026, 8, 15, 8, 0, tzinfo=timezone.utc)
    coordinator.prepare(
        "exec-video-fail",
        "Create a launch video and final MP4",
        token="token",
        principal_id="oidc|user@example.test",
        tenant_id="tenant/example",
        now=now,
    )
    grants.kill("worker-video", now=now)

    with pytest.raises(GrantError, match="stopped"):
        coordinator.resume(
            "exec-video-fail", token="token", now=now + timedelta(seconds=1)
        )

    state = coordinator.get("exec-video-fail")
    assert state["execution_status"] == "FAILED_TERMINAL"
    assert state["terminal"] is True
    assert state["terminal_reason"] == "The governed execution adapter failed."
    error = cast(dict[str, object], state["error"])
    assert error["error_class"] == "GrantError"
    assert scheduler.state()["leases"] == []
    assert not (tmp_path / "video" / "exec-video-fail").exists()
    grant_state = grants.state()
    revoked = cast(list[dict[str, object]], grant_state["revoked"])
    assert len(revoked) == 1


def test_finalizing_product_recovers_after_cross_store_crash(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    coordinator, _, scheduler, grants, product = _coordinator(tmp_path)
    prepared_at = datetime(2026, 8, 15, 8, 0, tzinfo=timezone.utc)
    request_id = "exec-video-finalize-recovery"
    coordinator.prepare(
        request_id,
        "Create a launch video and final MP4",
        token="token",
        principal_id="oidc|user@example.test",
        tenant_id="tenant/example",
        now=prepared_at,
    )
    real_recover = product.recover_finalizing

    def crash_boundary(
        request_id_arg: str, *, token: str, now: datetime
    ) -> dict[str, object]:
        assert request_id_arg == request_id
        raise ProductRuntimeError("simulated crash before cross-store completion")

    monkeypatch.setattr(product, "recover_finalizing", crash_boundary)
    with pytest.raises(ProductFinalizationPending, match="durably finalizing"):
        coordinator.resume(
            request_id,
            token="token",
            now=prepared_at + timedelta(seconds=1),
        )

    state = coordinator.get(request_id)
    assert state["execution_status"] == "EXECUTING"
    assert state["terminal"] is False
    assert scheduler.state()["leases"] == []
    with sqlite3.connect(tmp_path / "product.sqlite3") as connection:
        product_status = connection.execute(
            "SELECT status FROM product_proofs WHERE request_id = ?",
            (request_id,),
        ).fetchone()
        product_closure = connection.execute(
            "SELECT terminal_status FROM product_proof_closure WHERE request_id = ?",
            (request_id,),
        ).fetchone()
    assert product_status == ("finalizing",)
    assert product_closure is None
    revoked_after_crash = cast(list[dict[str, object]], grants.state()["revoked"])
    assert len(revoked_after_crash) == 1

    monkeypatch.setattr(product, "recover_finalizing", real_recover)
    manifest = coordinator.resume(
        request_id,
        token="token",
        now=prepared_at + timedelta(seconds=2),
    )
    assert manifest["accepted"] is True
    assert manifest["job_state_proven"] is True
    assert manifest["finalization_status"] == "accepted"
    final_state = coordinator.get(request_id)
    assert final_state["execution_status"] == "ACCEPTED"
    assert final_state["terminal"] is True
    assert scheduler.state()["leases"] == []
    with sqlite3.connect(tmp_path / "product.sqlite3") as connection:
        product_status = connection.execute(
            "SELECT status FROM product_proofs WHERE request_id = ?",
            (request_id,),
        ).fetchone()
        product_closure = connection.execute(
            "SELECT terminal_status FROM product_proof_closure WHERE request_id = ?",
            (request_id,),
        ).fetchone()
    assert product_status == ("accepted",)
    assert product_closure == ("accepted",)


def test_stale_executing_request_closes_as_interrupted(tmp_path: Path) -> None:
    coordinator, _, scheduler, grants, _ = _coordinator(tmp_path)
    prepared_at = datetime(2026, 8, 15, 8, 0, tzinfo=timezone.utc)
    coordinator.prepare(
        "exec-video-stale",
        "Create a launch video and final MP4",
        token="token",
        principal_id="oidc|user@example.test",
        tenant_id="tenant/example",
        now=prepared_at,
    )
    with sqlite3.connect(tmp_path / "coordinator.sqlite3") as connection:
        connection.execute(
            "UPDATE execution_requests SET status = 'EXECUTING', updated_at = ? "
            "WHERE request_id = ?",
            (prepared_at.isoformat(), "exec-video-stale"),
        )

    reconciled = coordinator.recover_stale(
        token="token", now=prepared_at + timedelta(minutes=16)
    )
    assert reconciled == (
        {"request_id": "exec-video-stale", "status": "INTERRUPTED"},
    )
    state = coordinator.get("exec-video-stale")
    assert state["execution_status"] == "INTERRUPTED"
    assert state["terminal"] is True
    assert state["terminal_reason"] == (
        "stale execution interrupted and subordinate resources closed"
    )
    assert scheduler.state()["leases"] == []
    with sqlite3.connect(tmp_path / "product.sqlite3") as connection:
        product_status = connection.execute(
            "SELECT status FROM product_proofs WHERE request_id = ?",
            ("exec-video-stale",),
        ).fetchone()
        product_closure = connection.execute(
            "SELECT terminal_status FROM product_proof_closure WHERE request_id = ?",
            ("exec-video-stale",),
        ).fetchone()
    assert product_status == ("interrupted",)
    assert product_closure == ("interrupted",)
    with sqlite3.connect(tmp_path / "state.sqlite3") as connection:
        workflow_status = connection.execute(
            "SELECT status FROM workflows WHERE workflow_id = ?",
            ("proof-exec-video-stale",),
        ).fetchone()
    assert workflow_status == ("cancelled",)
    revoked = cast(list[dict[str, object]], grants.state()["revoked"])
    assert len(revoked) == 1


def test_fresh_executing_request_is_not_falsely_closed(tmp_path: Path) -> None:
    coordinator, _, _, _, _ = _coordinator(tmp_path)
    now = datetime(2026, 8, 15, 8, 0, tzinfo=timezone.utc)
    coordinator.prepare(
        "exec-video-active",
        "Create a launch video and final MP4",
        token="token",
        principal_id="oidc|user@example.test",
        tenant_id="tenant/example",
        now=now,
    )
    with sqlite3.connect(tmp_path / "coordinator.sqlite3") as connection:
        connection.execute(
            "UPDATE execution_requests SET status = 'EXECUTING', updated_at = ? "
            "WHERE request_id = ?",
            (now.isoformat(), "exec-video-active"),
        )

    with pytest.raises(ExecutionCoordinatorError, match="already executing"):
        coordinator.resume(
            "exec-video-active", token="token", now=now + timedelta(minutes=1)
        )
    state = coordinator.get("exec-video-active")
    assert state["execution_status"] == "EXECUTING"
    assert state["terminal"] is False
