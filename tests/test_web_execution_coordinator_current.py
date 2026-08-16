"""Current-master evidence for the governed Web finished-product adapter."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import cast

import pytest

from services.control_plane import ControlPlane, ControlPlaneConfig
from services.control_plane.workflows import WorkflowStore, WorkflowStoreConfig
from services.evidence import EvidenceStore
from services.execution_adapters import register_web_runtime
from services.execution_coordinator import ExecutionCoordinator, ExecutionState
from services.governance import GovernedRuntimeGateway
from services.integrations import DeterministicLocalVideoRuntime, DurableVideoProductRuntime
from services.integrations.web_product_runtime import (
    DurableWebProductRuntime,
    WebProductFinalizationPending,
    WebProductRuntimeError,
)
from services.runtime import DurableGrantPolicy, DurableWorkerScheduler, GovernedRuntime
from src.video_automation.models import JobState


def _coordinator(
    tmp_path: Path,
) -> tuple[ExecutionCoordinator, DurableWebProductRuntime, ControlPlane]:
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
    return coordinator, web, control


def test_web_is_registry_driven_and_accepts_verified_finished_product(tmp_path: Path) -> None:
    coordinator, _, control = _coordinator(tmp_path)
    now = datetime(2026, 8, 16, 1, 30, tzinfo=timezone.utc)
    prepared = coordinator.prepare(
        "web-current-1",
        "Build a premium bilingual Turkish/English website for a corporate law firm",
        token="token",
        principal_id="oidc|web@example.test",
        tenant_id="tenant/web",
        now=now,
    )
    assert prepared["execution_status"] == ExecutionState.ADMITTED.value
    assert prepared["adapter_id"] == "web.product-runtime.v1"
    plan = cast(dict[str, object], prepared["plan"])
    assert plan["capabilities"] == ["ilaios.capability.web-factory"]

    manifest = coordinator.resume(
        "web-current-1",
        token="token",
        now=now + timedelta(seconds=1),
        principal_id="oidc|web@example.test",
        tenant_id="tenant/web",
    )
    assert manifest["accepted"] is True
    assert manifest["adapter_id"] == "web.product-runtime.v1"
    assert manifest["deployment_state"] == "NOT_DEPLOYED"
    qa = cast(dict[str, object], manifest["qa"])
    assert qa["passed"] is True
    assert manifest["source_project_digest"]
    state = coordinator.get(
        "web-current-1",
        principal_id="oidc|web@example.test",
        tenant_id="tenant/web",
    )
    assert state["execution_status"] == ExecutionState.ACCEPTED.value
    assert state["result_sha256"]
    assert control.get_job("token", str(state["job_id"])).state is JobState.COMPLETED


def test_web_finalizing_crash_recovers_without_false_completion(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    coordinator, web, control = _coordinator(tmp_path)
    now = datetime(2026, 8, 16, 1, 30, tzinfo=timezone.utc)
    prepared = coordinator.prepare(
        "web-current-crash",
        "Build a premium website for a furniture company",
        token="token",
        principal_id="oidc|web@example.test",
        tenant_id="tenant/web",
        now=now,
    )
    job_id = str(prepared["job_id"])
    real_recover = web.recover_finalizing

    def crash_boundary(
        request_id: str, *, token: str, now: datetime
    ) -> dict[str, object]:
        del request_id, token, now
        raise WebProductRuntimeError("simulated crash after finalizing persist")

    monkeypatch.setattr(web, "recover_finalizing", crash_boundary)
    with pytest.raises(WebProductFinalizationPending):
        coordinator.resume(
            "web-current-crash",
            token="token",
            now=now + timedelta(seconds=1),
            principal_id="oidc|web@example.test",
            tenant_id="tenant/web",
        )
    assert coordinator.get("web-current-crash")["execution_status"] == ExecutionState.EXECUTING.value
    assert control.get_job("token", job_id).state is JobState.VALIDATING
    assert web.get_state("web-current-crash")["status"] == "finalizing"

    monkeypatch.setattr(web, "recover_finalizing", real_recover)
    manifest = coordinator.resume(
        "web-current-crash",
        token="token",
        now=now + timedelta(seconds=2),
        principal_id="oidc|web@example.test",
        tenant_id="tenant/web",
    )
    assert manifest["accepted"] is True
    assert manifest["job_state_proven"] is True
    assert web.get_state("web-current-crash")["terminal_status"] == "accepted"
    assert control.get_job("token", job_id).state is JobState.COMPLETED


def test_web_high_risk_intent_reaches_human_approval_state(tmp_path: Path) -> None:
    coordinator, _, _ = _coordinator(tmp_path)
    now = datetime(2026, 8, 16, 1, 30, tzinfo=timezone.utc)
    prepared = coordinator.prepare(
        "web-current-high-risk",
        "Build a website using private data and deploy to production",
        token="token",
        principal_id="oidc|owner@example.test",
        tenant_id="tenant/web",
        now=now,
    )
    assert prepared["execution_status"] == ExecutionState.BLOCKED.value
    assert prepared["blocker_code"] == "UNVERIFIED_EXTERNAL_SIDE_EFFECT"
