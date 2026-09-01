"""End-to-end governed product proof tests for PLATFORM.P15."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest

from services.control_plane import ControlPlane, ControlPlaneConfig
from services.evidence import EvidenceStore
from services.governance import HumanApprovalStore
from services.integrations import (
    DesktopGoalRequest,
    GovernedVideoProductProof,
    ProductProofError,
    VideoChainAdapter,
)
from services.runtime import (
    BlastRadiusBudget,
    ExecutionGrant,
    GrantPolicy,
    WorkerProfile,
    WorkerScheduler,
)
from src.video_automation.configuration import BudgetPolicy
from src.video_automation.models import CostRecord
from src.video_automation.workflow_orchestrator import (
    VideoWorkflowOrchestrator,
    WorkflowGate,
    WorkflowStage,
    WorkflowStep,
)


def _execute(context: Mapping[str, Any]) -> str:
    return str(context["job_id"])


def _steps() -> tuple[WorkflowStep, ...]:
    return tuple(
        WorkflowStep(stage, WorkflowGate(), _execute, stage.value)
        for stage in tuple(WorkflowStage)[1:]
    )


def _proof(tmp_path: Path) -> tuple[GovernedVideoProductProof, HumanApprovalStore]:
    approvals = HumanApprovalStore(tmp_path / "approvals.sqlite3")
    scheduler = WorkerScheduler(lease_duration=timedelta(minutes=5))
    scheduler.register(WorkerProfile("worker-video", frozenset({"video"}), 1))
    video = VideoChainAdapter(
        VideoWorkflowOrchestrator(),
        GrantPolicy(),
        EvidenceStore(tmp_path / "evidence"),
    )
    return (
        GovernedVideoProductProof(
            ControlPlane(ControlPlaneConfig(tmp_path / "control.sqlite3", "token")),
            approvals,
            scheduler,
            video,
        ),
        approvals,
    )


def test_windows_goal_produces_complete_acceptance_manifest(tmp_path: Path) -> None:
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    proof, approvals = _proof(tmp_path)
    approvals.decide("request-1", approved=True, approver="owner")
    grant = ExecutionGrant(
        "grant-1",
        "worker-video",
        frozenset({"video.execute"}),
        frozenset({"job-00000001"}),
        now + timedelta(minutes=10),
        BlastRadiusBudget(1, 1),
    )
    manifest = proof.run(
        DesktopGoalRequest("request-1", "Create and deliver a governed video"),
        token="token",
        steps=_steps(),
        grant=grant,
        costs=(CostRecord("job-00000001", "local", "render", 1.0, 0.8, "USD", now),),
        budget=BudgetPolicy(max_cost_per_video=2.0),
        delivery_evidence_id="delivery-proof-1",
        now=now,
    )

    assert manifest.accepted is True
    assert manifest.approval_proven is True
    assert manifest.cost_proven is True
    assert manifest.job_id == "job-00000001"
    assert manifest.worker_id == "worker-video"
    assert manifest.delivery_evidence_id == "delivery-proof-1"
    assert len(manifest.evidence_hash) == 64


def test_product_proof_rejects_non_desktop_or_unapproved_requests(
    tmp_path: Path,
) -> None:
    proof, _ = _proof(tmp_path)
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    grant = ExecutionGrant(
        "grant-1",
        "worker-video",
        frozenset({"video.execute"}),
        frozenset({"job-00000001"}),
        now + timedelta(minutes=10),
        BlastRadiusBudget(1, 1),
    )
    with pytest.raises(ProductProofError, match="Windows Desktop"):
        proof.run(
            DesktopGoalRequest("request-1", "goal", "web"),
            token="token",
            steps=_steps(),
            grant=grant,
            costs=(),
            budget=BudgetPolicy(max_cost_per_video=2.0),
            delivery_evidence_id="delivery-proof-1",
            now=now,
        )
    with pytest.raises(ProductProofError, match="approval"):
        proof.run(
            DesktopGoalRequest("request-1", "goal"),
            token="token",
            steps=_steps(),
            grant=grant,
            costs=(),
            budget=BudgetPolicy(max_cost_per_video=2.0),
            delivery_evidence_id="delivery-proof-1",
            now=now,
        )
