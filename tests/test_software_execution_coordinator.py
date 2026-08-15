"""Finished-product Software execution tests on the canonical Coordinator."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import cast

from services.control_plane import ControlPlane, ControlPlaneConfig
from services.control_plane.workflows import WorkflowStore, WorkflowStoreConfig
from services.evidence import EvidenceStore
from services.execution_coordinator import ExecutionCoordinator
from services.governance import GovernedRuntimeGateway
from services.integrations import (
    DeterministicLocalVideoRuntime,
    DurableVideoProductRuntime,
    RecoverableSoftwareProductRuntime,
)
from services.runtime import DurableGrantPolicy, DurableWorkerScheduler, GovernedRuntime


def _runtime(
    tmp_path: Path,
) -> tuple[ExecutionCoordinator, GovernedRuntimeGateway, DurableGrantPolicy]:
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
        software,
    )
    return coordinator, governance, grants


def test_task_manager_runs_through_canonical_coordinator_to_finished_zip(
    tmp_path: Path,
) -> None:
    coordinator, governance, grants = _runtime(tmp_path)
    now = datetime(2026, 8, 16, 8, 0, tzinfo=timezone.utc)

    prepared = coordinator.prepare(
        "software-e2e-1",
        "Build me a simple production-quality task management application",
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
    grant_state = grants.state()
    grant_rows = cast(list[dict[str, object]], grant_state["grants"])
    revoked_rows = cast(list[dict[str, object]], grant_state["revoked"])
    assert any(row["used_side_effects"] == 1 for row in grant_rows)
    assert len(revoked_rows) == 1
    assert revoked_rows[0]["grant_id"] == grant_rows[0]["grant_id"]


def test_unsupported_software_request_remains_fail_closed(tmp_path: Path) -> None:
    coordinator, governance, _ = _runtime(tmp_path)
    now = datetime(2026, 8, 16, 8, 0, tzinfo=timezone.utc)

    prepared = coordinator.prepare(
        "software-unsupported-1",
        "Build accounting software for a multinational company",
        token="local-ci-boundary",
        principal_id="oidc|software-user",
        tenant_id="tenant/example",
        now=now,
    )

    assert prepared["capability_id"] == "ilaios.capability.software-factory"
    assert prepared["adapter_id"] is None
    assert prepared["execution_status"] == "BLOCKED_ADAPTER_UNAVAILABLE"
    assert governance.state()["work"] == []


def test_stale_software_execution_closes_durably_after_restart(tmp_path: Path) -> None:
    coordinator, _, grants = _runtime(tmp_path)
    prepared_at = datetime(2026, 8, 16, 8, 0, tzinfo=timezone.utc)
    coordinator.prepare(
        "software-stale-1",
        "Build a task manager application",
        token="local-ci-boundary",
        principal_id="oidc|software-user",
        tenant_id="tenant/example",
        now=prepared_at,
    )
    database = tmp_path / "coordinator.sqlite3"
    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE execution_requests SET status='EXECUTING', updated_at=? "
            "WHERE request_id=?",
            (prepared_at.isoformat(), "software-stale-1"),
        )

    reconciled = coordinator.recover_stale(
        token="local-ci-boundary",
        now=prepared_at + timedelta(minutes=16),
    )

    assert reconciled == (
        {"request_id": "software-stale-1", "status": "INTERRUPTED"},
    )
    state = coordinator.get("software-stale-1")
    assert state["execution_status"] == "INTERRUPTED"
    assert state["terminal"] is True
    assert "recovery window" in str(state["terminal_reason"])
    assert cast(list[dict[str, object]], grants.state()["grants"]) == []
