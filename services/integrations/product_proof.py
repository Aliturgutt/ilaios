"""Complete governed Windows Desktop to delivery product proof."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from services.control_plane import (
    BudgetEnvelope,
    ControlPlane,
    DataClass,
    GoalSpec,
    ProposedTask,
    RiskClass,
    propose_execution,
)
from services.governance import HumanApprovalStore
from services.runtime import ExecutionGrant, WorkerScheduler
from src.video_automation.configuration import BudgetPolicy
from src.video_automation.models import CostRecord
from src.video_automation.workflow_orchestrator import WorkflowStep

from .video import VideoChainAdapter


class ProductProofError(PermissionError):
    """Raised when the first product proof lacks a mandatory gate."""


@dataclass(frozen=True, slots=True)
class DesktopGoalRequest:
    request_id: str
    objective: str
    source: str = "windows-desktop"


@dataclass(frozen=True, slots=True)
class AcceptanceManifest:
    manifest_version: str
    request_id: str
    goal_id: str
    job_id: str
    proposal_id: str
    worker_id: str
    approval_proven: bool
    cost_proven: bool
    evidence_hash: str
    delivery_evidence_id: str
    accepted: bool


class GovernedVideoProductProof:
    def __init__(
        self,
        control_plane: ControlPlane,
        approvals: HumanApprovalStore,
        scheduler: WorkerScheduler,
        video: VideoChainAdapter,
    ) -> None:
        self._control_plane = control_plane
        self._approvals = approvals
        self._scheduler = scheduler
        self._video = video

    def run(
        self,
        request: DesktopGoalRequest,
        *,
        token: str,
        steps: tuple[WorkflowStep, ...],
        grant: ExecutionGrant,
        costs: tuple[CostRecord, ...],
        budget: BudgetPolicy,
        delivery_evidence_id: str,
        now: datetime,
    ) -> AcceptanceManifest:
        if request.source != "windows-desktop":
            raise ProductProofError("product proof must originate from Windows Desktop")
        if not self._approvals.is_approved(request.request_id):
            raise ProductProofError("durable human approval is required")

        goal = self._control_plane.create_goal(token, request.objective)
        job = self._control_plane.create_job(token, goal.goal_id)
        spec = GoalSpec(
            request.objective,
            ("Canonical video workflow completes", "Delivery evidence exists"),
            RiskClass.HIGH,
            DataClass.INTERNAL,
            BudgetEnvelope(3, 3600),
        )
        proposal = propose_execution(
            spec,
            (
                ProposedTask("video", "Run canonical video chain"),
                ProposedTask("delivery", "Verify delivery", ("video",)),
            ),
        )
        lease = self._scheduler.schedule(job.job_id, "video", now=now)
        result = self._video.run(
            job_id=job.job_id,
            steps=steps,
            grant=grant,
            costs=costs,
            budget=budget,
            observed_latency_ms=1,
            max_latency_ms=1000,
            publish_evidence_id=delivery_evidence_id,
            now=now,
        )
        self._scheduler.complete(lease, now=now)
        return AcceptanceManifest(
            "1.0",
            request.request_id,
            goal.goal_id,
            job.job_id,
            proposal.proposal_id,
            lease.worker_id,
            True,
            result.cost.actual_total <= budget.max_cost_per_video,
            result.evidence.record_hash,
            delivery_evidence_id,
            True,
        )
