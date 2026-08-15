"""Red-team tests for the canonical one-prompt execution coordinator."""

from __future__ import annotations

import sqlite3
from concurrent.futures import ThreadPoolExecutor
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
    classify_execution_plan,
    classify_execution_route,
)
from services.governance import GovernedRuntimeGateway
from services.integrations import DeterministicLocalVideoRuntime, DurableVideoProductRuntime
from services.runtime import DurableGrantPolicy, DurableWorkerScheduler, GovernedRuntime


class _Fixture:
    def __init__(self, tmp_path: Path) -> None:
        self.tmp_path = tmp_path
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
        self.coordinator = self.new_coordinator()

    def new_coordinator(self) -> ExecutionCoordinator:
        return ExecutionCoordinator(
            self.coordinator_path,
            self.control,
            self.governance,
            self.grants,
            self.product,
            self.evidence,
        )


def _now() -> datetime:
    return datetime(2026, 8, 15, 8, 0, tzinfo=timezone.utc)


def _prepare_video(
    fixture: _Fixture,
    request_id: str,
    *,
    objective: str = "Create a launch video and final MP4",
    principal_id: str = "oidc|user@example.test",
    tenant_id: str = "tenant/example",
    now: datetime | None = None,
) -> dict[str, object]:
    return fixture.coordinator.prepare(
        request_id,
        objective,
        token="token",
        principal_id=principal_id,
        tenant_id=tenant_id,
        now=_now() if now is None else now,
    )


def test_route_selection_is_boundary_aware_and_canonical() -> None:
    video = classify_execution_route("Create a 60 second launch video and final MP4")
    assert video.capability_id == "ilaios.capability.video-media-factory"
    assert video.adapter_id == "video.product-runtime.v1"

    web = classify_execution_route("Build a premium website for a furniture company")
    assert web.capability_id == "ilaios.capability.web-factory"
    assert web.adapter_id is None

    with pytest.raises(ExecutionCoordinatorError, match="could not be selected"):
        classify_execution_route("Make something excellent")
    with pytest.raises(ExecutionCoordinatorError, match="could not be selected"):
        classify_execution_route("This repositoryish word must not match")
    with pytest.raises(ExecutionCoordinatorError, match="multiple capabilities"):
        classify_execution_route("Build a website and a launch video")


def test_multi_capability_plan_uses_canonical_dependency_order() -> None:
    app_plan = classify_execution_plan("Build a mobile app and software repository")
    assert app_plan.capability_ids.index("ilaios.capability.software-factory") < (
        app_plan.capability_ids.index("ilaios.capability.app-factory")
    )

    mixed = classify_execution_plan("Build a website and a launch video")
    assert set(mixed.capability_ids) == {
        "ilaios.capability.web-factory",
        "ilaios.capability.video-media-factory",
    }


def test_unverified_web_adapter_fails_closed_with_machine_blocker(
    tmp_path: Path,
) -> None:
    fixture = _Fixture(tmp_path)
    prepared = fixture.coordinator.prepare(
        "exec-web-1",
        "Build a premium website for my furniture company",
        token="token",
        principal_id="oidc|user@example.test",
        tenant_id="tenant/example",
        now=_now(),
    )

    assert prepared["capability_id"] == "ilaios.capability.web-factory"
    assert prepared["adapter_id"] is None
    assert prepared["execution_status"] == "BLOCKED"
    assert prepared["blocker_code"] == "GENERAL_PURPOSE_WEB_ADAPTER_UNAVAILABLE"
    plan = cast(dict[str, object], prepared["plan"])
    blockers = cast(list[dict[str, object]], plan["blockers"])
    assert blockers[0]["maturity"] == "IMPLEMENTED_NOT_EXECUTABLE"
    assert fixture.governance.state()["work"] == []
    assert fixture.evidence.verify()
    with pytest.raises(ExecutionCoordinatorError, match="not resumable"):
        fixture.coordinator.resume("exec-web-1", token="token", now=_now())


def test_multi_capability_request_is_planned_then_fail_closed(tmp_path: Path) -> None:
    fixture = _Fixture(tmp_path)
    prepared = fixture.coordinator.prepare(
        "exec-multi-1",
        "Build a website and a launch video",
        token="token",
        principal_id="oidc|user@example.test",
        tenant_id="tenant/example",
        now=_now(),
    )

    assert prepared["execution_status"] == "BLOCKED"
    assert prepared["blocker_code"] == "MULTI_CAPABILITY_ADAPTER_SET_INCOMPLETE"
    plan = cast(dict[str, object], prepared["plan"])
    routes = cast(list[dict[str, object]], plan["routes"])
    assert {item["capability_id"] for item in routes} == {
        "ilaios.capability.web-factory",
        "ilaios.capability.video-media-factory",
    }


def test_video_external_mutation_scope_is_not_false_accepted(tmp_path: Path) -> None:
    fixture = _Fixture(tmp_path)
    prepared = _prepare_video(
        fixture,
        "exec-publish-1",
        objective="Create a launch video and publish it to YouTube",
    )
    assert prepared["execution_status"] == "BLOCKED"
    assert prepared["blocker_code"] == "VIDEO_EXTERNAL_MUTATION_ADAPTER_UNAVAILABLE"
    plan = cast(dict[str, object], prepared["plan"])
    blockers = cast(list[dict[str, object]], plan["blockers"])
    assert blockers[0]["blocker_code"] == "VIDEO_EXTERNAL_MUTATION_ADAPTER_UNAVAILABLE"


def test_medium_video_is_admitted_without_human_approval_or_early_lease(
    tmp_path: Path,
) -> None:
    fixture = _Fixture(tmp_path)
    principal_id = "oidc|subject:user@example.test"
    tenant_id = "tenant/global-example"
    prepared = _prepare_video(
        fixture,
        "exec-video-1",
        objective="Create a short launch video and deliver the final MP4",
        principal_id=principal_id,
        tenant_id=tenant_id,
    )

    assert prepared["execution_status"] == "ADMITTED"
    assert fixture.scheduler.state()["leases"] == []
    assert fixture.governance.approval_proven("exec-video-1") is False
    assert fixture.governance.admission_snapshot("exec-video-1") == {
        "risk": "medium",
        "admission_decision": "ALLOW",
        "human_approval_required": False,
        "approval_proven": False,
        "admission_proven": True,
    }
    with pytest.raises(ExecutionCoordinatorError, match="not awaiting approval"):
        fixture.coordinator.decide(
            "exec-video-1",
            approver_id="oidc|approver@example.test",
            tenant_id=tenant_id,
            decision="approved",
            now=_now() + timedelta(seconds=1),
        )


def test_high_risk_video_requires_independent_human_approval(tmp_path: Path) -> None:
    fixture = _Fixture(tmp_path)
    principal = "oidc|requester@example.test"
    tenant = "tenant/example"
    prepared = _prepare_video(
        fixture,
        "exec-high-1",
        objective="Create a private data launch video and final MP4",
        principal_id=principal,
        tenant_id=tenant,
    )
    assert prepared["execution_status"] == "PENDING_APPROVAL"
    snapshot = fixture.governance.admission_snapshot("exec-high-1")
    assert snapshot["admission_decision"] == "REQUIRE_APPROVAL"

    with pytest.raises(ExecutionCoordinatorError, match="independent human approver"):
        fixture.coordinator.decide(
            "exec-high-1",
            approver_id=principal,
            tenant_id=tenant,
            decision="approved",
            now=_now() + timedelta(seconds=1),
        )

    assert fixture.coordinator.decide(
        "exec-high-1",
        approver_id="oidc|independent-approver@example.test",
        tenant_id=tenant,
        decision="approved",
        now=_now() + timedelta(seconds=2),
    ) == "ADMITTED"
    manifest = fixture.coordinator.resume(
        "exec-high-1", token="token", now=_now() + timedelta(seconds=3)
    )
    assert manifest["accepted"] is True
    assert manifest["risk"] == "high"
    assert manifest["human_approval_required"] is True
    assert manifest["approval_proven"] is True


def test_video_executes_to_verified_acceptance_with_fresh_grant_and_lease(
    tmp_path: Path,
) -> None:
    fixture = _Fixture(tmp_path)
    principal_id = "oidc|subject:user@example.test"
    tenant_id = "tenant/global-example"
    _prepare_video(
        fixture,
        "exec-video-2",
        objective="Create a short launch video and deliver the final MP4",
        principal_id=principal_id,
        tenant_id=tenant_id,
    )
    manifest = fixture.coordinator.resume(
        "exec-video-2", token="token", now=_now() + timedelta(seconds=1)
    )

    assert manifest["accepted"] is True
    assert manifest["admission_proven"] is True
    assert manifest["worker_lease_proven"] is True
    assert manifest["grant_proven"] is True
    assert manifest["artifact_digest"] == manifest["delivery_sha256"]
    state = fixture.coordinator.get(
        "exec-video-2", principal_id=principal_id, tenant_id=tenant_id
    )
    assert state["execution_status"] == "ACCEPTED"
    grants = cast(list[dict[str, object]], fixture.grants.state()["grants"])
    assert grants[0]["used_side_effects"] == 1
    assert len(fixture.evidence.verify()) >= 2


def test_prepare_is_idempotent_and_conflicting_replay_is_rejected(
    tmp_path: Path,
) -> None:
    fixture = _Fixture(tmp_path)
    first = fixture.coordinator.prepare(
        "exec-idempotent-1",
        "Create a launch video and final MP4",
        token="token",
        principal_id="oidc|user@example.test",
        tenant_id="tenant/example",
        now=_now(),
    )
    second = fixture.coordinator.prepare(
        "exec-idempotent-1",
        "Create a launch video and final MP4",
        token="token",
        principal_id="oidc|user@example.test",
        tenant_id="tenant/example",
        now=_now(),
    )
    assert second["goal_id"] == first["goal_id"]
    assert second["job_id"] == first["job_id"]

    with pytest.raises(ExecutionCoordinatorError, match="conflicts"):
        fixture.coordinator.prepare(
            "exec-idempotent-1",
            "Create a different launch video and final MP4",
            token="token",
            principal_id="oidc|user@example.test",
            tenant_id="tenant/example",
            now=_now(),
        )


def test_execution_is_single_use_after_acceptance(tmp_path: Path) -> None:
    fixture = _Fixture(tmp_path)
    _prepare_video(fixture, "exec-video-3")
    first = fixture.coordinator.resume(
        "exec-video-3", token="token", now=_now() + timedelta(seconds=1)
    )
    second = fixture.coordinator.resume(
        "exec-video-3", token="token", now=_now() + timedelta(seconds=2)
    )
    assert second == first


def test_cancellation_is_idempotent_and_revokes_execution_authority(
    tmp_path: Path,
) -> None:
    fixture = _Fixture(tmp_path)
    principal = "oidc|user@example.test"
    tenant = "tenant/example"
    _prepare_video(
        fixture,
        "exec-cancel-1",
        principal_id=principal,
        tenant_id=tenant,
    )

    assert fixture.coordinator.cancel(
        "exec-cancel-1",
        actor_id=principal,
        tenant_id=tenant,
        now=_now() + timedelta(seconds=1),
    ) == "CANCELLED"
    assert fixture.coordinator.cancel(
        "exec-cancel-1",
        actor_id=principal,
        tenant_id=tenant,
        now=_now() + timedelta(seconds=2),
    ) == "CANCELLED"
    assert fixture.scheduler.state()["leases"] == []
    revoked = cast(list[dict[str, object]], fixture.grants.state()["revoked"])
    assert revoked
    with pytest.raises(ExecutionCoordinatorError, match="not resumable"):
        fixture.coordinator.resume(
            "exec-cancel-1", token="token", now=_now() + timedelta(seconds=3)
        )


def test_cross_tenant_and_cross_principal_access_fail_closed(tmp_path: Path) -> None:
    fixture = _Fixture(tmp_path)
    _prepare_video(
        fixture,
        "exec-owner-1",
        principal_id="oidc|owner@example.test",
        tenant_id="tenant/a",
    )

    with pytest.raises(ExecutionCoordinatorError, match="principal"):
        fixture.coordinator.get(
            "exec-owner-1",
            principal_id="oidc|attacker@example.test",
            tenant_id="tenant/a",
        )
    with pytest.raises(ExecutionCoordinatorError, match="cross-tenant"):
        fixture.coordinator.get(
            "exec-owner-1",
            principal_id="oidc|owner@example.test",
            tenant_id="tenant/b",
        )
    with pytest.raises(ExecutionCoordinatorError):
        fixture.coordinator.cancel(
            "exec-owner-1",
            actor_id="oidc|attacker@example.test",
            tenant_id="tenant/b",
            now=_now() + timedelta(seconds=1),
        )


def test_accepted_result_tamper_is_detected(tmp_path: Path) -> None:
    fixture = _Fixture(tmp_path)
    _prepare_video(fixture, "exec-tamper-1")
    fixture.coordinator.resume(
        "exec-tamper-1", token="token", now=_now() + timedelta(seconds=1)
    )

    with sqlite3.connect(fixture.coordinator_path) as connection:
        connection.execute(
            "UPDATE execution_requests SET result_json = ? WHERE request_id = ?",
            ('{"accepted":true,"artifact_digest":"tampered"}', "exec-tamper-1"),
        )
    with pytest.raises(ExecutionCoordinatorError, match="integrity"):
        fixture.coordinator.get("exec-tamper-1")


def test_legacy_null_deadline_and_plan_are_backfilled_on_restart(tmp_path: Path) -> None:
    fixture = _Fixture(tmp_path)
    _prepare_video(fixture, "exec-legacy-1")
    with sqlite3.connect(fixture.coordinator_path) as connection:
        connection.execute(
            "UPDATE execution_requests SET deadline_at = NULL, plan_json = NULL "
            "WHERE request_id = ?",
            ("exec-legacy-1",),
        )
    restarted = fixture.new_coordinator()
    state = restarted.get("exec-legacy-1")
    assert isinstance(state["deadline_at"], str)
    plan = cast(dict[str, object], state["plan"])
    assert plan["capabilities"] == ["ilaios.capability.video-media-factory"]


def test_recovery_marks_stale_interrupted_execution_retryable(tmp_path: Path) -> None:
    fixture = _Fixture(tmp_path)
    _prepare_video(fixture, "exec-recover-1")
    with sqlite3.connect(fixture.coordinator_path) as connection:
        connection.execute(
            "UPDATE execution_requests SET status = 'EXECUTING', attempt = 1, updated_at = ? "
            "WHERE request_id = ?",
            ((_now() - timedelta(minutes=5)).isoformat(), "exec-recover-1"),
        )

    recovery = fixture.coordinator.recover(token="token", now=_now())
    assert recovery == {"recovered": 0, "failed_retryable": 1}
    state = fixture.coordinator.get("exec-recover-1")
    assert state["execution_status"] == "FAILED_RETRYABLE"
    error = cast(dict[str, object], state["error"])
    assert error["error_code"] == "INTERRUPTED_EXECUTION"
    assert error["retryable"] is True


def test_concurrent_resume_allows_only_one_side_effect(tmp_path: Path) -> None:
    fixture = _Fixture(tmp_path)
    _prepare_video(fixture, "exec-race-1")

    def resume() -> object:
        try:
            return fixture.coordinator.resume(
                "exec-race-1", token="token", now=_now() + timedelta(seconds=1)
            )
        except Exception as error:
            return error

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(resume), executor.submit(resume)]
        results = [future.result() for future in futures]

    assert fixture.coordinator.get("exec-race-1")["execution_status"] == "ACCEPTED"
    assert any(
        isinstance(item, dict) and item.get("accepted") is True for item in results
    )
    grants = cast(list[dict[str, object]], fixture.grants.state()["grants"])
    effects = cast(list[dict[str, object]], fixture.scheduler.state()["effects"])
    assert len(grants) == 1
    assert len(effects) == 1


def test_adapter_matrix_reports_current_reality_without_fake_executability(
    tmp_path: Path,
) -> None:
    fixture = _Fixture(tmp_path)
    matrix = {
        str(item["capability_id"]): item
        for item in fixture.coordinator.adapter_matrix()
    }
    assert matrix["ilaios.capability.video-media-factory"]["maturity"] == (
        CapabilityMaturity.VERIFIED_FINISHED_PRODUCT_ADAPTER.value
    )
    assert matrix["ilaios.capability.video-media-factory"]["executable"] is True
    assert matrix["ilaios.capability.web-factory"]["maturity"] == (
        CapabilityMaturity.IMPLEMENTED_NOT_EXECUTABLE.value
    )
    assert matrix["ilaios.capability.web-factory"]["executable"] is False
    for capability_id in (
        "ilaios.capability.software-factory",
        "ilaios.capability.app-factory",
        "ilaios.capability.commerce-growth",
        "ilaios.capability.personal-operations",
    ):
        assert matrix[capability_id]["maturity"] == CapabilityMaturity.REVIEW_ONLY.value
        assert matrix[capability_id]["executable"] is False


def test_metrics_are_low_cardinality_and_do_not_expose_identity(tmp_path: Path) -> None:
    fixture = _Fixture(tmp_path)
    fixture.coordinator.prepare(
        "exec-metrics-1",
        "Build a website",
        token="token",
        principal_id="oidc|sensitive-user@example.test",
        tenant_id="tenant/sensitive",
        now=_now(),
    )
    metrics = fixture.coordinator.metrics()
    serialized = str(metrics)
    assert metrics["blocked"] == 1
    assert "sensitive-user" not in serialized
    assert "tenant/sensitive" not in serialized
