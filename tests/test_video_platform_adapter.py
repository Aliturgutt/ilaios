"""Governed Video Automation adapter tests for PLATFORM.P14."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest

from services.evidence import EvidenceStore
from services.integrations import VideoChainAdapter, VideoIntegrationError
from services.runtime import (
    BlastRadiusBudget,
    ExecutionGrant,
    GrantError,
    GrantPolicy,
)
from src.video_automation.configuration import BudgetPolicy
from src.video_automation.models import CostRecord
from src.video_automation.workflow_orchestrator import (
    VideoWorkflowOrchestrator,
    WorkflowGate,
    WorkflowStage,
    WorkflowStep,
)


def _steps() -> tuple[WorkflowStep, ...]:
    return tuple(
        WorkflowStep(stage, WorkflowGate(), _execute, stage.value)
        for stage in tuple(WorkflowStage)[1:]
    )


def _execute(context: Mapping[str, Any]) -> str:
    return str(context["job_id"])


def _grant(now: datetime) -> ExecutionGrant:
    return ExecutionGrant(
        "grant-video",
        "worker-video",
        frozenset({"video.execute"}),
        frozenset({"job-video"}),
        now + timedelta(minutes=10),
        BlastRadiusBudget(1, 1),
    )


def _cost(now: datetime) -> tuple[CostRecord, ...]:
    return (CostRecord("job-video", "local", "render", 1.0, 0.8, "USD", now),)


def test_proven_video_chain_passes_platform_governance_and_evidence(
    tmp_path: Path,
) -> None:
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    adapter = VideoChainAdapter(
        VideoWorkflowOrchestrator(), GrantPolicy(), EvidenceStore(tmp_path / "evidence")
    )
    result = adapter.run(
        job_id="job-video",
        steps=_steps(),
        grant=_grant(now),
        costs=_cost(now),
        budget=BudgetPolicy(max_cost_per_video=2.0),
        observed_latency_ms=900,
        max_latency_ms=1000,
        publish_evidence_id="publish-proof-1",
        now=now,
    )

    assert result.workflow.progress.stage is WorkflowStage.COMPLETED
    assert result.contract.payload["qa_passed"] is True
    assert result.contract.payload["publish_evidence_id"] == "publish-proof-1"
    assert result.cost.actual_total == 0.8
    assert result.evidence.action == "video.integration.completed"


def test_grant_cost_latency_and_publish_gates_fail_closed(tmp_path: Path) -> None:
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    policy = GrantPolicy()
    adapter = VideoChainAdapter(
        VideoWorkflowOrchestrator(), policy, EvidenceStore(tmp_path / "evidence")
    )
    policy.revoke("grant-video")
    with pytest.raises(GrantError, match="revoked"):
        adapter.run(
            job_id="job-video",
            steps=_steps(),
            grant=_grant(now),
            costs=_cost(now),
            budget=BudgetPolicy(max_cost_per_video=2.0),
            observed_latency_ms=900,
            max_latency_ms=1000,
            publish_evidence_id="publish-proof-1",
            now=now,
        )

    clean = VideoChainAdapter(
        VideoWorkflowOrchestrator(), GrantPolicy(), EvidenceStore(tmp_path / "clean")
    )
    with pytest.raises(VideoIntegrationError, match="latency"):
        clean.run(
            job_id="job-video",
            steps=_steps(),
            grant=_grant(now),
            costs=_cost(now),
            budget=BudgetPolicy(max_cost_per_video=2.0),
            observed_latency_ms=1001,
            max_latency_ms=1000,
            publish_evidence_id="publish-proof-1",
            now=now,
        )
