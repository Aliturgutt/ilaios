"""Governed adapter for the proven canonical Video Automation chain."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone

from packages.contracts.ilaios_contracts import (
    ContractEnvelope,
    ContractKind,
    SchemaVersion,
)
from services.evidence import EvidenceStore, ProvenanceRecord
from services.runtime import ExecutionGrant, GrantPolicy
from src.video_automation.configuration import BudgetPolicy
from src.video_automation.cost_control import CostController, CostSummary
from src.video_automation.models import CostRecord
from src.video_automation.workflow_orchestrator import (
    VideoWorkflowOrchestrator,
    WorkflowRunResult,
    WorkflowStage,
    WorkflowStep,
)


class VideoIntegrationError(ValueError):
    """Raised when platform governance cannot prove a video chain result."""


@dataclass(frozen=True, slots=True)
class VideoIntegrationResult:
    workflow: WorkflowRunResult
    contract: ContractEnvelope
    cost: CostSummary
    evidence: ProvenanceRecord


class VideoChainAdapter:
    """Adds platform governance without reimplementing proven video behavior."""

    def __init__(
        self,
        orchestrator: VideoWorkflowOrchestrator,
        grants: GrantPolicy,
        evidence: EvidenceStore,
    ) -> None:
        self._orchestrator = orchestrator
        self._grants = grants
        self._evidence = evidence

    def run(
        self,
        *,
        job_id: str,
        steps: tuple[WorkflowStep, ...],
        grant: ExecutionGrant,
        costs: tuple[CostRecord, ...],
        budget: BudgetPolicy,
        observed_latency_ms: int,
        max_latency_ms: int,
        publish_evidence_id: str,
        now: datetime,
    ) -> VideoIntegrationResult:
        self._grants.authorize(
            grant,
            subject_id=grant.subject_id,
            action="video.execute",
            resource=job_id,
            now=now,
        )
        if observed_latency_ms < 0 or observed_latency_ms > max_latency_ms:
            raise VideoIntegrationError("video latency acceptance failed")
        if not publish_evidence_id or publish_evidence_id != publish_evidence_id.strip():
            raise VideoIntegrationError("publish evidence is required")

        cost = CostController().enforce_video_budget(costs, budget)
        workflow = self._orchestrator.run(job_id, steps)
        required_qa = {
            WorkflowStage.TECHNICALLY_VALIDATED,
            WorkflowStage.CONTENT_VALIDATED,
            WorkflowStage.PUBLISH_READY,
            WorkflowStage.COMPLETED,
        }
        if not required_qa <= set(workflow.executed_stages):
            raise VideoIntegrationError("video QA and publish stages are incomplete")

        payload = {
            "job_id": job_id,
            "final_stage": workflow.progress.stage.value,
            "estimated_cost": cost.estimated_total,
            "actual_cost": cost.actual_total,
            "currency": cost.currency,
            "latency_ms": observed_latency_ms,
            "publish_evidence_id": publish_evidence_id,
            "qa_passed": True,
        }
        artifact = self._evidence.put_artifact(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        )
        evidence = self._evidence.append_provenance(
            job_id, artifact, "video.integration.completed"
        )
        self._grants.record_side_effect(grant, job_id)
        contract = ContractEnvelope(
            SchemaVersion.V1,
            f"video-result:{job_id}",
            ContractKind.EVENT,
            datetime.now(timezone.utc),
            payload,
        )
        return VideoIntegrationResult(workflow, contract, cost, evidence)
