"""Red-team coverage for canonical bounded multi-capability execution."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import cast

import pytest

from services.control_plane import ControlPlane, ControlPlaneConfig
from services.control_plane.workflows import WorkflowStore, WorkflowStoreConfig
from services.evidence import EvidenceStore
from services.execution_adapters import register_web_runtime
from services.execution_coordinator import (
    ExecutionAdapter,
    ExecutionCoordinator,
    ExecutionCoordinatorError,
    ExecutionState,
    classify_execution_plan,
)
from services.governance import GovernedRuntimeGateway
from services.integrations import DeterministicLocalVideoRuntime, DurableVideoProductRuntime
from services.integrations.web_product_runtime import DurableWebProductRuntime
from services.runtime import DurableGrantPolicy, DurableWorkerScheduler, GovernedRuntime
from src.video_automation.models import JobState


def _coordinator(
    tmp_path: Path,
) -> tuple[
    ExecutionCoordinator,
    ControlPlane,
    DurableWebProductRuntime,
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
    web = DurableWebProductRuntime(
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
    return coordinator, control, web, grants


def _objective() -> str:
    return (
        "Build a premium website for a furniture company and create a short launch "
        "video with the final MP4"
    )


def test_verified_web_and_video_form_executable_canonical_plan(tmp_path: Path) -> None:
    coordinator, _, _, _ = _coordinator(tmp_path)
    del coordinator
    plan = classify_execution_plan(_objective())
    assert set(plan.capability_ids) == {
        "ilaios.capability.video-media-factory",
        "ilaios.capability.web-factory",
    }
    assert {route.adapter_id for route in plan.routes} == {
        "video.product-runtime.v1",
        "web.product-runtime.v1",
    }


def test_multi_verified_steps_accept_once_with_content_addressed_evidence(
    tmp_path: Path,
) -> None:
    coordinator, control, _, grants = _coordinator(tmp_path)
    now = datetime(2026, 8, 16, 8, 0, tzinfo=timezone.utc)
    principal = "oidc|multi@example.test"
    tenant = "tenant/multi"

    prepared = coordinator.prepare(
        "multi-web-video-1",
        _objective(),
        token="token",
        principal_id=principal,
        tenant_id=tenant,
        now=now,
    )
    assert prepared["execution_status"] == ExecutionState.ADMITTED.value
    assert prepared["capability_id"] == "ilaios.capability.multi"
    steps = cast(list[dict[str, object]], prepared["steps"])
    assert len(steps) == 2
    assert all(step["status"] == "ADMITTED" for step in steps)

    first = coordinator.resume(
        "multi-web-video-1",
        token="token",
        now=now + timedelta(seconds=1),
        principal_id=principal,
        tenant_id=tenant,
    )
    second = coordinator.resume(
        "multi-web-video-1",
        token="token",
        now=now + timedelta(seconds=2),
        principal_id=principal,
        tenant_id=tenant,
    )
    assert second == first
    assert first["accepted"] is True
    assert first["all_steps_accepted"] is True
    assert first["deployment_state"] == "NOT_DEPLOYED"
    manifest_steps = cast(list[dict[str, object]], first["steps"])
    assert len(manifest_steps) == 2
    assert all(len(cast(str, step["result_sha256"])) == 64 for step in manifest_steps)

    state = coordinator.get(
        "multi-web-video-1", principal_id=principal, tenant_id=tenant
    )
    assert state["execution_status"] == ExecutionState.ACCEPTED.value
    assert state["terminal"] is True
    assert len(cast(str, state["result_sha256"])) == 64
    assert control.get_job("token", cast(str, state["job_id"])).state is JobState.COMPLETED
    step_state = cast(list[dict[str, object]], state["steps"])
    assert all(step["status"] == "ACCEPTED" for step in step_state)
    grant_rows = cast(list[dict[str, object]], grants.state()["grants"])
    revoked_rows = cast(list[dict[str, object]], grants.state()["revoked"])
    assert len(grant_rows) == 2
    assert len(revoked_rows) == 2


def test_verified_plus_unverified_factory_blocks_before_step_execution(tmp_path: Path) -> None:
    coordinator, _, _, grants = _coordinator(tmp_path)
    now = datetime(2026, 8, 16, 8, 0, tzinfo=timezone.utc)
    prepared = coordinator.prepare(
        "multi-blocked-1",
        "Build a website and a software repository for the product",
        token="token",
        principal_id="oidc|multi@example.test",
        tenant_id="tenant/multi",
        now=now,
    )
    assert prepared["execution_status"] == ExecutionState.BLOCKED.value
    assert prepared["blocker_code"] == "SOFTWARE_FACTORY_REVIEW_ONLY"
    assert prepared["terminal"] is False
    assert grants.state()["grants"] == []


def test_multi_resume_recovers_after_process_stops_between_accepted_steps(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    coordinator, _, _, _ = _coordinator(tmp_path)
    now = datetime(2026, 8, 16, 8, 0, tzinfo=timezone.utc)
    principal = "oidc|multi@example.test"
    tenant = "tenant/multi"
    coordinator.prepare(
        "multi-restart-1",
        _objective(),
        token="token",
        principal_id=principal,
        tenant_id=tenant,
        now=now,
    )
    real_resolver = coordinator._verified_step_adapter  # noqa: SLF001
    interrupted = False

    def simulate_process_stop(step: sqlite3.Row) -> ExecutionAdapter:
        nonlocal interrupted
        if not interrupted and int(str(step["step_index"])) == 1:
            interrupted = True
            raise ExecutionCoordinatorError("simulated process stop between steps")
        return real_resolver(step)

    monkeypatch.setattr(coordinator, "_verified_step_adapter", simulate_process_stop)
    with pytest.raises(ExecutionCoordinatorError, match="simulated process stop"):
        coordinator.resume(
            "multi-restart-1",
            token="token",
            now=now + timedelta(seconds=1),
            principal_id=principal,
            tenant_id=tenant,
        )
    interim = coordinator.get(
        "multi-restart-1", principal_id=principal, tenant_id=tenant
    )
    interim_steps = cast(list[dict[str, object]], interim["steps"])
    assert interim["execution_status"] == ExecutionState.EXECUTING.value
    assert interim_steps[0]["status"] == "ACCEPTED"
    assert interim_steps[1]["status"] == "ADMITTED"

    monkeypatch.setattr(coordinator, "_verified_step_adapter", real_resolver)
    manifest = coordinator.resume(
        "multi-restart-1",
        token="token",
        now=now + timedelta(seconds=2),
        principal_id=principal,
        tenant_id=tenant,
    )
    assert manifest["accepted"] is True
    final = coordinator.get(
        "multi-restart-1", principal_id=principal, tenant_id=tenant
    )
    assert final["execution_status"] == ExecutionState.ACCEPTED.value


def test_multi_cancel_is_owner_scoped_idempotent_and_terminal(tmp_path: Path) -> None:
    coordinator, control, _, _ = _coordinator(tmp_path)
    now = datetime(2026, 8, 16, 8, 0, tzinfo=timezone.utc)
    principal = "oidc|multi@example.test"
    tenant = "tenant/multi"
    prepared = coordinator.prepare(
        "multi-cancel-1",
        _objective(),
        token="token",
        principal_id=principal,
        tenant_id=tenant,
        now=now,
    )
    with pytest.raises(ExecutionCoordinatorError, match="principal"):
        coordinator.cancel(
            "multi-cancel-1",
            token="token",
            actor_id="oidc|other@example.test",
            tenant_id=tenant,
            now=now + timedelta(seconds=1),
        )
    with pytest.raises(ExecutionCoordinatorError, match="cross-tenant"):
        coordinator.cancel(
            "multi-cancel-1",
            token="token",
            actor_id=principal,
            tenant_id="tenant/other",
            now=now + timedelta(seconds=1),
        )

    first = coordinator.cancel(
        "multi-cancel-1",
        token="token",
        actor_id=principal,
        tenant_id=tenant,
        now=now + timedelta(seconds=1),
    )
    second = coordinator.cancel(
        "multi-cancel-1",
        token="token",
        actor_id=principal,
        tenant_id=tenant,
        now=now + timedelta(seconds=2),
    )
    assert first == second == ExecutionState.CANCELLED.value
    state = coordinator.get(
        "multi-cancel-1", principal_id=principal, tenant_id=tenant
    )
    assert state["terminal"] is True
    assert state["execution_status"] == ExecutionState.CANCELLED.value
    assert all(
        step["status"] == "CANCELLED"
        for step in cast(list[dict[str, object]], state["steps"])
    )
    assert control.get_job("token", cast(str, prepared["job_id"])).state is JobState.CANCELLED
