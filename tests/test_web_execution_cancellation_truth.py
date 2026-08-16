"""Web adapter owner-cancellation evidence must remain cancelled, not interrupted."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from services.control_plane import ControlPlane, ControlPlaneConfig
from services.control_plane.workflows import WorkflowStore, WorkflowStoreConfig
from services.evidence import EvidenceStore
from services.execution_adapters import register_web_runtime
from services.execution_coordinator import ExecutionCoordinator
from services.governance import GovernedRuntimeGateway
from services.integrations import (
    DeterministicLocalVideoRuntime,
    DurableVideoProductRuntime,
    RecoverableWebProductRuntime,
)
from services.runtime import DurableGrantPolicy, DurableWorkerScheduler, GovernedRuntime
from src.video_automation.models import JobState


def test_authenticated_web_cancellation_is_durably_cancelled(tmp_path: Path) -> None:
    state = tmp_path / "state.sqlite3"
    token = "local-ci-boundary"
    control = ControlPlane(ControlPlaneConfig(state, token))
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
    now = datetime(2026, 8, 16, 8, 0, tzinfo=timezone.utc)
    prepared = coordinator.prepare(
        "web-cancel-1",
        "Build a production-quality website for ILAIOS",
        token=token,
        principal_id="oidc|web-user",
        tenant_id="tenant/example",
        now=now,
    )

    assert coordinator.cancel(
        "web-cancel-1",
        token=token,
        actor_id="oidc|web-user",
        tenant_id="tenant/example",
        now=now + timedelta(seconds=1),
    ) == "CANCELLED"

    product_state = web.get_state("web-cancel-1")
    coordinator_state = coordinator.get("web-cancel-1")
    assert product_state["status"] == "cancelled"
    assert product_state["terminal_status"] == "cancelled"
    assert product_state["reason"] == "cancelled by authenticated execution owner"
    assert coordinator_state["execution_status"] == "CANCELLED"
    assert control.get_job(token, str(prepared["job_id"])).state is JobState.CANCELLED
