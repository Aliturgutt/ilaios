"""Fault-injection proof for Software cross-store finalization and lease closure."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import cast

import pytest

from services.control_plane import ControlPlane, ControlPlaneConfig
from services.control_plane.workflows import WorkflowStore, WorkflowStoreConfig
from services.evidence import EvidenceStore
from services.governance import GovernedRuntimeGateway
from services.integrations.software_product_runtime import (
    SoftwareProductFinalizationPending,
    SoftwareProductRuntimeError,
)
from services.integrations.software_product_runtime_recovery import (
    RecoverableSoftwareProductRuntime,
)
from services.runtime import (
    BlastRadiusBudget,
    DurableGrantPolicy,
    DurableWorkerScheduler,
    ExecutionGrant,
    GovernedRuntime,
)
from src.video_automation.models import JobState


def _runtime(tmp_path: Path) -> tuple[RecoverableSoftwareProductRuntime, ControlPlane, DurableGrantPolicy, DurableWorkerScheduler]:
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
    runtime = RecoverableSoftwareProductRuntime(
        tmp_path / "software-product.sqlite3",
        control,
        workflows,
        scheduler,
        grants,
        governance,
        EvidenceStore(tmp_path / "evidence"),
        tmp_path / "software",
        source_head_sha="a" * 40,
    )
    return runtime, control, grants, scheduler


def test_software_finalizing_is_recoverable_without_duplicate_acceptance(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime, control, grants, scheduler = _runtime(tmp_path)
    now = datetime(2026, 8, 16, 1, 0, tzinfo=timezone.utc)
    request_id = "software-finalize-crash"
    prepared = runtime.prepare(
        request_id,
        "Build a local task manager application",
        token="token",
        now=now,
        requester_id="oidc|software@example.test",
        tenant_id="tenant/software",
        defer_lease=True,
    )
    job_id = cast(str, prepared["job_id"])
    grant_id = "software-finalize-grant"
    grants.register(
        ExecutionGrant(
            grant_id,
            "worker-software",
            frozenset({"software.execute"}),
            frozenset({job_id}),
            now + timedelta(minutes=10),
            BlastRadiusBudget(1, 1),
        )
    )
    real_recover = runtime.recover_finalizing

    def crash_boundary(
        request_id_arg: str, *, token: str, now: datetime
    ) -> dict[str, object]:
        del token, now
        assert request_id_arg == request_id
        raise SoftwareProductRuntimeError("simulated crash after finalizing persist")

    monkeypatch.setattr(runtime, "recover_finalizing", crash_boundary)
    with pytest.raises(SoftwareProductFinalizationPending, match="durably finalizing"):
        runtime.execute(request_id, grant_id, token="token", now=now + timedelta(seconds=1))

    assert control.get_job("token", job_id).state is JobState.VALIDATING
    assert scheduler.state()["leases"] == []
    with sqlite3.connect(tmp_path / "software-product.sqlite3") as connection:
        status = connection.execute(
            "SELECT status FROM software_product_proofs WHERE request_id=?",
            (request_id,),
        ).fetchone()
        closure = connection.execute(
            "SELECT terminal_status FROM software_product_closure WHERE request_id=?",
            (request_id,),
        ).fetchone()
    assert status == ("finalizing",)
    assert closure is None

    monkeypatch.setattr(runtime, "recover_finalizing", real_recover)
    manifest = runtime.recover_finalizing(
        request_id, token="token", now=now + timedelta(seconds=2)
    )
    assert manifest["accepted"] is True
    assert manifest["job_state_proven"] is True
    assert manifest["finalization_status"] == "accepted"
    assert manifest["commercial_release_pass"] is False
    assert control.get_job("token", job_id).state is JobState.COMPLETED
    repeated = runtime.recover_finalizing(
        request_id, token="token", now=now + timedelta(seconds=3)
    )
    assert repeated == manifest
    with sqlite3.connect(tmp_path / "software-product.sqlite3") as connection:
        accepted_count = connection.execute(
            "SELECT COUNT(*) FROM software_product_closure "
            "WHERE request_id=? AND terminal_status='accepted'",
            (request_id,),
        ).fetchone()[0]
    assert accepted_count == 1
