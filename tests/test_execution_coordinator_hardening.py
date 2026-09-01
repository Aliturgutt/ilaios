"""Focused lifecycle/security tests for canonical Execution Coordinator hardening."""

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
    CapabilityMaturity,
    ExecutionCoordinator,
    ExecutionCoordinatorError,
)
from services.governance import GovernedRuntimeGateway
from services.integrations import DeterministicLocalVideoRuntime, DurableVideoProductRuntime
from services.integrations.product_runtime import ProductRuntimeError
from services.runtime import DurableGrantPolicy, DurableWorkerScheduler, GovernedRuntime


class _Fixture:
    def __init__(self, tmp_path: Path) -> None:
        self.state = tmp_path / "state.sqlite3"
        self.control = ControlPlane(ControlPlaneConfig(self.state, "token"))
        self.workflows = WorkflowStore(WorkflowStoreConfig(self.state))
        self.scheduler = DurableWorkerScheduler(
            self.state, lease_duration=timedelta(seconds=30)
        )
        self.grants = DurableGrantPolicy(self.state)
        self.governance = GovernedRuntimeGateway(
            tmp_path / "governance.sqlite3",
            GovernedRuntime(self.state),
            hard_cap_minor=100,
        )
        self.evidence = EvidenceStore(tmp_path / "evidence")
        video = DeterministicLocalVideoRuntime(
            tmp_path / "video",
            self.grants,
            self.governance,
            self.evidence,
        )
        self.product = DurableVideoProductRuntime(
            tmp_path / "product.sqlite3",
            self.control,
            self.workflows,
            self.scheduler,
            self.grants,
            self.governance,
            video,
        )
        self.coordinator_path = tmp_path / "coordinator.sqlite3"
        self.coordinator = ExecutionCoordinator(
            self.coordinator_path,
            self.control,
            self.governance,
            self.grants,
            self.product,
            self.evidence,
        )


def _now() -> datetime:
    return datetime(2026, 8, 16, 0, 0, tzinfo=timezone.utc)


def _prepare_video(
    fixture: _Fixture,
    request_id: str,
    *,
    objective: str = "Create a launch video and final MP4",
    principal_id: str = "oidc|user@example.test",
    tenant_id: str = "tenant/example",
) -> dict[str, object]:
    return fixture.coordinator.prepare(
        request_id,
        objective,
        token="token",
        principal_id=principal_id,
        tenant_id=tenant_id,
        now=_now(),
    )


def test_unverified_capability_and_mixed_plan_remain_fail_closed(
    tmp_path: Path,
) -> None:
    fixture = _Fixture(tmp_path)
    web = fixture.coordinator.prepare(
        "hard-web-1",
        "Build a premium website",
        token="token",
        principal_id="oidc|user@example.test",
        tenant_id="tenant/example",
        now=_now(),
    )
    assert web["execution_status"] == "BLOCKED"
    assert web["blocker_code"] == "GENERAL_PURPOSE_WEB_ADAPTER_UNAVAILABLE"

    mixed = fixture.coordinator.prepare(
        "hard-multi-1",
        "Build a website and a launch video",
        token="token",
        principal_id="oidc|user@example.test",
        tenant_id="tenant/example",
        now=_now(),
    )
    assert mixed["execution_status"] == "BLOCKED"
    assert mixed["blocker_code"] == "GENERAL_PURPOSE_WEB_ADAPTER_UNAVAILABLE"


def test_high_risk_video_requires_independent_human_approval(tmp_path: Path) -> None:
    fixture = _Fixture(tmp_path)
    principal = "oidc|requester@example.test"
    prepared = _prepare_video(
        fixture,
        "hard-high-1",
        objective="Create a private data launch video and final MP4",
        principal_id=principal,
    )
    assert prepared["execution_status"] == "PENDING_APPROVAL"
    with pytest.raises(ExecutionCoordinatorError, match="independent human approver"):
        fixture.coordinator.decide(
            "hard-high-1",
            approver_id=principal,
            tenant_id="tenant/example",
            decision="approved",
            now=_now() + timedelta(seconds=1),
        )
    assert fixture.coordinator.decide(
        "hard-high-1",
        approver_id="oidc|independent@example.test",
        tenant_id="tenant/example",
        decision="approved",
        now=_now() + timedelta(seconds=2),
    ) == "ADMITTED"
    manifest = fixture.coordinator.resume(
        "hard-high-1", token="token", now=_now() + timedelta(seconds=3)
    )
    assert manifest["accepted"] is True
    assert manifest["risk"] == "high"
    assert manifest["approval_proven"] is True


def test_finalizing_is_recoverable_and_never_false_terminal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture = _Fixture(tmp_path)
    _prepare_video(fixture, "hard-finalizing-1")
    original = fixture.product.recover_finalizing
    calls = {"count": 0}

    def fail_once(request_id: str, *, token: str, now: datetime) -> dict[str, object]:
        calls["count"] += 1
        if calls["count"] == 1:
            raise ProductRuntimeError("simulated cross-store crash")
        return original(request_id, token=token, now=now)

    monkeypatch.setattr(fixture.product, "recover_finalizing", fail_once)
    with pytest.raises(Exception, match="finalizing"):
        fixture.coordinator.resume(
            "hard-finalizing-1", token="token", now=_now() + timedelta(seconds=1)
        )
    state = fixture.coordinator.get("hard-finalizing-1")
    assert state["execution_status"] == "EXECUTING"
    assert state["terminal"] is False
    assert fixture.product.get_state("hard-finalizing-1")["status"] == "finalizing"

    recovered = fixture.coordinator.recover_stale(
        token="token", now=_now() + timedelta(seconds=2)
    )
    assert recovered == (
        {"request_id": "hard-finalizing-1", "status": "ACCEPTED"},
    )
    final = fixture.coordinator.get("hard-finalizing-1")
    assert final["execution_status"] == "ACCEPTED"
    assert final["terminal"] is True


def test_prepare_replay_and_owner_tenant_checks_fail_closed(tmp_path: Path) -> None:
    fixture = _Fixture(tmp_path)
    first = _prepare_video(fixture, "hard-owner-1")
    second = _prepare_video(fixture, "hard-owner-1")
    assert second["goal_id"] == first["goal_id"]
    with pytest.raises(ExecutionCoordinatorError, match="conflicts"):
        _prepare_video(
            fixture,
            "hard-owner-1",
            objective="Create a different video and final MP4",
        )
    with pytest.raises(ExecutionCoordinatorError, match="principal"):
        fixture.coordinator.get(
            "hard-owner-1",
            principal_id="oidc|attacker@example.test",
            tenant_id="tenant/example",
        )
    with pytest.raises(ExecutionCoordinatorError, match="cross-tenant"):
        fixture.coordinator.get(
            "hard-owner-1",
            principal_id="oidc|user@example.test",
            tenant_id="tenant/other",
        )


def test_accepted_result_tamper_and_concurrent_state_are_fail_closed(tmp_path: Path) -> None:
    fixture = _Fixture(tmp_path)
    _prepare_video(fixture, "hard-tamper-1")
    fixture.coordinator.resume(
        "hard-tamper-1", token="token", now=_now() + timedelta(seconds=1)
    )
    with sqlite3.connect(fixture.coordinator_path) as connection:
        connection.execute(
            "UPDATE execution_requests SET result_json = ? WHERE request_id = ?",
            ('{"accepted":true,"artifact_digest":"tampered"}', "hard-tamper-1"),
        )
    with pytest.raises(ExecutionCoordinatorError, match="integrity"):
        fixture.coordinator.get("hard-tamper-1")


def test_adapter_matrix_exposes_current_reality_without_fake_adapters(tmp_path: Path) -> None:
    fixture = _Fixture(tmp_path)
    matrix = {
        str(item["capability_id"]): item
        for item in fixture.coordinator.adapter_matrix()
    }
    assert matrix["ilaios.capability.video-media-factory"]["maturity"] == (
        CapabilityMaturity.VERIFIED_FINISHED_PRODUCT_ADAPTER.value
    )
    assert matrix["ilaios.capability.video-media-factory"]["executable"] is True
    assert matrix["ilaios.capability.web-factory"]["executable"] is False
    assert matrix["ilaios.capability.software-factory"]["executable"] is False


def test_failure_error_contract_binds_capability_and_adapter(tmp_path: Path) -> None:
    fixture = _Fixture(tmp_path)
    _prepare_video(fixture, "hard-error-1")
    fixture.grants.kill("worker-video", now=_now())
    with pytest.raises(Exception):
        fixture.coordinator.resume(
            "hard-error-1", token="token", now=_now() + timedelta(seconds=1)
        )
    state = fixture.coordinator.get("hard-error-1")
    error = cast(dict[str, object], state["error"])
    assert error["capability_id"] == "ilaios.capability.video-media-factory"
    assert error["adapter_id"] == "video.product-runtime.v1"
    assert "safe_message" in error
