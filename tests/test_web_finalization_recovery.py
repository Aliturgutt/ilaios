"""Fault-injection coverage for crash-safe Web cross-store finalization."""

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
    WebProductFinalizationPending,
    WebProductRuntimeError,
)
from services.runtime import DurableGrantPolicy, DurableWorkerScheduler, GovernedRuntime
from src.video_automation.models import JobState


def _coordinator(tmp_path: Path) -> tuple[ExecutionCoordinator, DurableWebProductRuntime, ControlPlane]:
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
    video_product = DurableVideoProductRuntime(
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
    coordinator = ExecutionCoordinator(
        tmp_path / "coordinator.sqlite3",
        control,
        governance,
        grants,
        video_product,
        web,
    )
    return coordinator, web, control


def test_web_finalizing_survives_crash_and_recovers_exactly_once(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    coordinator, web, control = _coordinator(tmp_path)
    prepared_at = datetime(2026, 8, 16, 1, 0, tzinfo=timezone.utc)
    request_id = "exec-web-finalize-crash"
    prepared = coordinator.prepare(
        request_id,
        "Build a premium bilingual Turkish/English website for a corporate law firm",
        token="token",
        principal_id="oidc|web-finalize@example.test",
        tenant_id="tenant/web-finalize",
        now=prepared_at,
    )
    job_id = cast(str, prepared["job_id"])
    real_recover = web.recover_finalizing

    def crash_boundary(
        request_id_arg: str, *, token: str, now: datetime
    ) -> dict[str, object]:
        del token, now
        assert request_id_arg == request_id
        raise WebProductRuntimeError("simulated crash after provisional finalization")

    monkeypatch.setattr(web, "recover_finalizing", crash_boundary)
    with pytest.raises(WebProductFinalizationPending, match="durably finalizing"):
        coordinator.resume(
            request_id,
            token="token",
            now=prepared_at + timedelta(seconds=1),
        )

    coordinator_state = coordinator.get(request_id)
    assert coordinator_state["execution_status"] == "EXECUTING"
    assert coordinator_state["terminal"] is False
    assert control.get_job("token", job_id).state is JobState.VALIDATING
    with sqlite3.connect(tmp_path / "web-product.sqlite3") as connection:
        status, manifest_json = connection.execute(
            "SELECT status, manifest_json FROM web_product_requests WHERE request_id = ?",
            (request_id,),
        ).fetchone()
        closure = connection.execute(
            "SELECT terminal_status FROM web_product_closure WHERE request_id = ?",
            (request_id,),
        ).fetchone()
    assert status == "finalizing"
    assert manifest_json is not None
    assert closure is None

    monkeypatch.setattr(web, "recover_finalizing", real_recover)
    manifest = web.recover_finalizing(
        request_id,
        token="token",
        now=prepared_at + timedelta(seconds=2),
    )
    assert manifest["accepted"] is True
    assert manifest["job_state_proven"] is True
    assert manifest["finalization_status"] == "accepted"
    assert manifest["deployment_state"] == "NOT_DEPLOYED"
    assert control.get_job("token", job_id).state is JobState.COMPLETED

    repeated = web.recover_finalizing(
        request_id,
        token="token",
        now=prepared_at + timedelta(seconds=3),
    )
    assert repeated == manifest
    with sqlite3.connect(tmp_path / "web-product.sqlite3") as connection:
        accepted_count = connection.execute(
            "SELECT COUNT(*) FROM web_product_closure "
            "WHERE request_id = ? AND terminal_status = 'accepted'",
            (request_id,),
        ).fetchone()[0]
    assert accepted_count == 1

    coordinator_manifest = coordinator.resume(
        request_id,
        token="token",
        now=prepared_at + timedelta(seconds=4),
    )
    assert coordinator_manifest == manifest
    assert coordinator.get(request_id)["execution_status"] == "ACCEPTED"


def test_finalizing_web_interrupt_recovers_acceptance_instead_of_overwriting_it(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    coordinator, web, _ = _coordinator(tmp_path)
    now = datetime(2026, 8, 16, 1, 0, tzinfo=timezone.utc)
    request_id = "exec-web-finalize-interrupt"
    coordinator.prepare(
        request_id,
        "Build a premium website for a furniture company",
        token="token",
        principal_id="oidc|web@example.test",
        tenant_id="tenant/web",
        now=now,
    )
    real_recover = web.recover_finalizing

    def crash_boundary(
        request_id_arg: str, *, token: str, now: datetime
    ) -> dict[str, object]:
        del request_id_arg, token, now
        raise WebProductRuntimeError("simulated finalization crash")

    monkeypatch.setattr(web, "recover_finalizing", crash_boundary)
    with pytest.raises(WebProductFinalizationPending):
        coordinator.resume(request_id, token="token", now=now + timedelta(seconds=1))
    monkeypatch.setattr(web, "recover_finalizing", real_recover)

    state = web.interrupt(
        request_id,
        token="token",
        now=now + timedelta(seconds=2),
        reason="late cancellation race",
    )
    assert state["status"] == "accepted"
    assert state["terminal_status"] == "accepted"
