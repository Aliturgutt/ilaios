"""Canonical Software adapter integration and terminal-truth tests."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import cast

import pytest

from services.control_plane import ControlPlane, ControlPlaneConfig
from services.control_plane.workflows import WorkflowStore, WorkflowStoreConfig
from services.evidence import EvidenceStore
from services.execution_adapters import register_software_runtime
from services.execution_coordinator import ExecutionCoordinator, ExecutionCoordinatorError
from services.governance import GovernedRuntimeGateway
from services.integrations import (
    DeterministicLocalVideoRuntime,
    DurableVideoProductRuntime,
    RecoverableSoftwareProductRuntime,
)
from services.runtime import DurableGrantPolicy, DurableWorkerScheduler, GovernedRuntime
from src.video_automation.models import JobState


def _runtime(
    tmp_path: Path,
) -> tuple[
    ExecutionCoordinator,
    GovernedRuntimeGateway,
    DurableGrantPolicy,
    RecoverableSoftwareProductRuntime,
    ControlPlane,
]:
    state = tmp_path / "state.sqlite3"
    control = ControlPlane(ControlPlaneConfig(state, "local-ci-boundary"))
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
    software = RecoverableSoftwareProductRuntime(
        tmp_path / "software-product.sqlite3",
        control,
        workflows,
        scheduler,
        grants,
        governance,
        evidence,
        tmp_path / "software",
        source_head_sha="a" * 40,
    )
    coordinator = ExecutionCoordinator(
        tmp_path / "coordinator.sqlite3",
        control,
        governance,
        grants,
        video_product,
        evidence,
    )
    register_software_runtime(coordinator, software)
    return coordinator, governance, grants, software, control


def test_task_manager_runs_through_registered_software_adapter(
    tmp_path: Path,
) -> None:
    coordinator, governance, grants, _, _ = _runtime(tmp_path)
    now = datetime(2026, 8, 16, 8, 0, tzinfo=timezone.utc)

    prepared = coordinator.prepare(
        "software-e2e-1",
        "Build me a simple production-quality task manager software application",
        token="local-ci-boundary",
        principal_id="oidc|software-user",
        tenant_id="tenant/example",
        now=now,
    )
    assert prepared["capability_id"] == "ilaios.capability.software-factory"
    assert prepared["adapter_id"] == "software.product-runtime.v1"
    assert prepared["execution_status"] == "ADMITTED"

    manifest = coordinator.resume(
        "software-e2e-1",
        token="local-ci-boundary",
        now=now + timedelta(seconds=1),
    )

    assert manifest["accepted"] is True
    assert manifest["final_disposition"] == "ACCEPT"
    assert manifest["factory"] == "ilaios.capability.software-factory"
    assert manifest["source_head_sha"] == "a" * 40
    assert manifest["external_provider_cost_minor"] == 0
    assert cast(dict[str, object], manifest["security_result"])["passed"] is True
    assert cast(dict[str, object], manifest["test_result"])["passed"] is True
    assert cast(dict[str, object], manifest["build_result"])["passed"] is True
    assert cast(dict[str, object], manifest["runtime_result"])["passed"] is True
    state = coordinator.get("software-e2e-1")
    assert state["execution_status"] == "ACCEPTED"
    assert state["terminal"] is True
    assert state["result_sha256"]
    assert governance.admission_proven("software-e2e-1") is True
    grant_rows = cast(list[dict[str, object]], grants.state()["grants"])
    revoked_rows = cast(list[dict[str, object]], grants.state()["revoked"])
    assert any(row["used_side_effects"] == 1 for row in grant_rows)
    assert len(revoked_rows) == 1
    assert revoked_rows[0]["grant_id"] == grant_rows[0]["grant_id"]


def test_unsupported_software_scope_fails_before_governed_work(tmp_path: Path) -> None:
    coordinator, governance, _, _, _ = _runtime(tmp_path)
    now = datetime(2026, 8, 16, 8, 0, tzinfo=timezone.utc)

    with pytest.raises(
        ExecutionCoordinatorError,
        match="outside the verified finished-product scope",
    ):
        coordinator.prepare(
            "software-unsupported-1",
            "Build accounting software for a multinational company",
            token="local-ci-boundary",
            principal_id="oidc|software-user",
            tenant_id="tenant/example",
            now=now,
        )

    assert coordinator.contains("software-unsupported-1") is False
    assert governance.state()["work"] == []


def test_authenticated_software_cancellation_is_durably_cancelled(
    tmp_path: Path,
) -> None:
    coordinator, _, grants, software, control = _runtime(tmp_path)
    now = datetime(2026, 8, 16, 8, 0, tzinfo=timezone.utc)
    prepared = coordinator.prepare(
        "software-cancel-1",
        "Build a task manager software application",
        token="local-ci-boundary",
        principal_id="oidc|software-user",
        tenant_id="tenant/example",
        now=now,
    )

    assert coordinator.cancel(
        "software-cancel-1",
        token="local-ci-boundary",
        actor_id="oidc|software-user",
        tenant_id="tenant/example",
        now=now + timedelta(seconds=1),
    ) == "CANCELLED"
    assert coordinator.cancel(
        "software-cancel-1",
        token="local-ci-boundary",
        actor_id="oidc|software-user",
        tenant_id="tenant/example",
        now=now + timedelta(seconds=2),
    ) == "CANCELLED"

    coordinator_state = coordinator.get("software-cancel-1")
    product_state = software.get_state("software-cancel-1")
    assert coordinator_state["execution_status"] == "CANCELLED"
    assert coordinator_state["terminal_reason"] == "cancelled by authenticated owner"
    assert product_state["status"] == "cancelled"
    assert product_state["terminal_status"] == "cancelled"
    assert product_state["reason"] == "cancelled by authenticated execution owner"
    assert control.get_job(
        "local-ci-boundary", str(prepared["job_id"])
    ).state is JobState.CANCELLED
    assert cast(list[dict[str, object]], grants.state()["grants"]) == []
