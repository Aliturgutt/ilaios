"""Policy propagation tests for the canonical durable Video finished-product runtime."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from services.control_plane import (
    BudgetEnvelope,
    ControlPlane,
    ControlPlaneConfig,
    DataClass,
)
from services.control_plane.workflows import WorkflowStore, WorkflowStoreConfig
from services.evidence import EvidenceStore
from services.governance import GovernedRuntimeGateway
from services.integrations import DeterministicLocalVideoRuntime, DurableVideoProductRuntime
from services.integrations.product_runtime import ProductRuntimeError
from services.runtime import DurableGrantPolicy, DurableWorkerScheduler, GovernedRuntime


def _runtime(tmp_path: Path) -> tuple[DurableVideoProductRuntime, GovernedRuntimeGateway, DurableWorkerScheduler]:
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
    return (
        DurableVideoProductRuntime(
            tmp_path / "product.sqlite3",
            control,
            workflows,
            scheduler,
            grants,
            governance,
            video,
        ),
        governance,
        scheduler,
    )


def test_high_risk_policy_reaches_authoritative_governance_without_early_lease(
    tmp_path: Path,
) -> None:
    runtime, governance, scheduler = _runtime(tmp_path)
    now = datetime(2026, 8, 16, 0, 0, tzinfo=timezone.utc)
    budget = BudgetEnvelope(2, 120, 25)

    prepared = runtime.prepare(
        "policy-high-1",
        "Create a private-data launch video",
        token="token",
        now=now,
        requester_id="oidc|user@example.test",
        tenant_id="tenant/example",
        defer_lease=True,
        risk="high",
        data_class=DataClass.RESTRICTED,
        budget=budget,
    )

    assert prepared["risk"] == "high"
    assert prepared["data_class"] == DataClass.RESTRICTED.value
    assert prepared["budget"] == {
        "max_attempts": 2,
        "max_runtime_seconds": 120,
        "max_external_spend_minor": 25,
    }
    assert prepared["admission_decision"] == "REQUIRE_APPROVAL"
    assert prepared["human_approval_required"] is True
    assert prepared["status"] == "pending_approval"
    assert governance.admission_snapshot("policy-high-1") == {
        "risk": "high",
        "admission_decision": "REQUIRE_APPROVAL",
        "human_approval_required": True,
        "approval_proven": False,
        "admission_proven": False,
    }
    assert governance.admission_proven("policy-high-1") is False
    assert scheduler.state()["leases"] == []


def test_unknown_policy_classification_fails_closed(tmp_path: Path) -> None:
    runtime, _, _ = _runtime(tmp_path)
    now = datetime(2026, 8, 16, 0, 0, tzinfo=timezone.utc)

    with pytest.raises(ProductRuntimeError, match="risk classification"):
        runtime.prepare(
            "policy-invalid-1",
            "Create a launch video",
            token="token",
            now=now,
            risk="critical",
        )
