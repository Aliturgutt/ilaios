"""Regression coverage for Video finalization while Web shares the coordinator."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import cast

import pytest

from services.control_plane import ControlPlane, ControlPlaneConfig
from services.control_plane.workflows import WorkflowStore, WorkflowStoreConfig
from services.evidence import EvidenceStore
from services.execution_coordinator import ExecutionCoordinator
from services.governance import GovernedRuntimeGateway
from services.integrations import (
    DeterministicLocalVideoRuntime,
    DurableVideoProductRuntime,
    DurableWebProductRuntime,
    ProductFinalizationPending,
    ProductRuntimeError,
)
from services.runtime import DurableGrantPolicy, DurableWorkerScheduler, GovernedRuntime


def _coordinator(
    tmp_path: Path,
) -> tuple[ExecutionCoordinator, DurableWorkerScheduler, DurableGrantPolicy]:
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
    web = DurableWebProductRuntime(
        tmp_path / "web-product.sqlite3",
        control,
        grants,
        governance,
        tmp_path / "web",
    )
    return (
        ExecutionCoordinator(
            tmp_path / "coordinator.sqlite3",
            control,
            governance,
            grants,
            product,
            web,
        ),
        scheduler,
        grants,
    )


def test_video_finalizing_recovers_without_web_regression(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    coordinator, scheduler, grants = _coordinator(tmp_path)
    prepared_at = datetime(2026, 8, 15, 8, 0, tzinfo=timezone.utc)
    request_id = "exec-video-finalize-web-shared"
    coordinator.prepare(
        request_id,
        "Create a launch video and final MP4",
        token="token",
        principal_id="oidc|user@example.test",
        tenant_id="tenant/example",
        now=prepared_at,
    )
    product = cast(DurableVideoProductRuntime, getattr(coordinator, "_video"))
    real_recover = product.recover_finalizing

    def crash_boundary(
        request_id_arg: str, *, token: str, now: datetime
    ) -> dict[str, object]:
        del token, now
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
            "SELECT status FROM product_proofs WHERE request_id = ?", (request_id,)
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
            "SELECT status FROM product_proofs WHERE request_id = ?", (request_id,)
        ).fetchone()
        product_closure = connection.execute(
            "SELECT terminal_status FROM product_proof_closure WHERE request_id = ?",
            (request_id,),
        ).fetchone()
    assert product_status == ("accepted",)
    assert product_closure == ("accepted",)
