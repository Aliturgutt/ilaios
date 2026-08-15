"""Durable first-product proof composed on the authenticated service boundary."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, cast

from services.control_plane import (
    BudgetEnvelope,
    ControlPlane,
    DataClass,
    ProposedTask,
    RiskClass,
)
from services.control_plane.workflows import WorkflowStore
from services.governance import GovernedRuntimeGateway
from services.runtime import (
    DurableGrantPolicy,
    DurableWorkerScheduler,
    Lease,
    WorkerProfile,
)
from src.video_automation.models import JobState

from .video_runtime import DeterministicLocalVideoRuntime


class ProductRuntimeError(RuntimeError):
    """Raised when a complete product proof cannot be derived from durable state."""


class DurableVideoProductRuntime:
    """Compose existing platform boundaries into one durable product proof."""

    def __init__(
        self,
        database_path: Path,
        control_plane: ControlPlane,
        workflows: WorkflowStore,
        scheduler: DurableWorkerScheduler,
        grants: DurableGrantPolicy,
        governance: GovernedRuntimeGateway,
        video: DeterministicLocalVideoRuntime,
    ) -> None:
        self._database_path = database_path
        self._control_plane = control_plane
        self._workflows = workflows
        self._scheduler = scheduler
        self._grants = grants
        self._governance = governance
        self._video = video
        database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS product_proofs ("
                "request_id TEXT PRIMARY KEY, goal_id TEXT NOT NULL, "
                "job_id TEXT NOT NULL, proposal_id TEXT NOT NULL, "
                "workflow_id TEXT NOT NULL, worker_id TEXT NOT NULL, "
                "lease_json TEXT NOT NULL, status TEXT NOT NULL, manifest_json TEXT)"
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def prepare(
        self,
        request_id: str,
        objective: str,
        *,
        token: str,
        now: datetime,
        requester_id: str = "windows-desktop-user",
        tenant_id: str | None = None,
        defer_lease: bool = False,
    ) -> dict[str, object]:
        _require_identity(request_id, "request_id")
        _require_actor(requester_id, "requester_id")
        if tenant_id is not None:
            _require_actor(tenant_id, "tenant_id")
        goal = self._control_plane.create_goal(token, objective)
        job = self._control_plane.create_job(token, goal.goal_id)
        proposal = self._control_plane.create_proposal(
            token,
            goal.goal_id,
            acceptance_criteria=(
                "Canonical governed video workflow completes",
                "Verified delivery and AcceptanceManifest exist",
            ),
            risk_class=RiskClass.MEDIUM,
            data_class=DataClass.INTERNAL,
            budget=BudgetEnvelope(1, 60, 10),
            tasks=(
                ProposedTask("video", "Execute governed local video"),
                ProposedTask(
                    "delivery",
                    "Verify content-addressed delivery",
                    ("video",),
                ),
            ),
        )
        proposal_id = str(proposal["proposal_id"])
        workflow_id = f"proof-{request_id}"
        self._workflows.create_workflow(workflow_id)
        self._workflows.add_task(workflow_id, "video", max_attempts=1)
        self._workflows.add_task(workflow_id, "delivery", max_attempts=1)
        worker_id = f"worker-{request_id}"
        self._scheduler.register(WorkerProfile(worker_id, frozenset({"video"}), 1))
        lease = (
            None
            if defer_lease
            else self._scheduler.schedule(job.job_id, "video", now=now)
        )
        governance_payload: dict[str, object] = {
            "goal_id": goal.goal_id,
            "job_id": job.job_id,
            "objective": objective,
        }
        if tenant_id is not None:
            governance_payload["tenant_id"] = tenant_id
        admission = self._governance.submit(
            request_id,
            requester_id,
            "video-agent",
            "video-chain-v30",
            "video",
            governance_payload,
            (),
            risk="medium",
        )
        if (
            admission.get("admission_decision") != "ALLOW"
            or admission.get("human_approval_required") is not False
        ):
            raise ProductRuntimeError("medium video admission did not fail closed")
        lease_json = (
            "{}" if lease is None else json.dumps(_lease_json(lease), sort_keys=True)
        )
        with self._connect() as connection:
            try:
                connection.execute(
                    "INSERT INTO product_proofs VALUES "
                    "(?, ?, ?, ?, ?, ?, ?, 'pending', NULL)",
                    (
                        request_id,
                        goal.goal_id,
                        job.job_id,
                        proposal_id,
                        workflow_id,
                        worker_id,
                        lease_json,
                    ),
                )
            except sqlite3.IntegrityError as error:
                raise ProductRuntimeError("product proof request already exists") from error
        return {
            "request_id": request_id,
            "goal_id": goal.goal_id,
            "job_id": job.job_id,
            "proposal_id": proposal_id,
            "workflow_id": workflow_id,
            "worker_id": worker_id,
            "lease": None if lease is None else _lease_json(lease),
            "risk": "medium",
            "admission_decision": "ALLOW",
            "status": "admitted_pending_grant",
        }

    def execute(
        self, request_id: str, grant_id: str, *, token: str, now: datetime
    ) -> dict[str, object]:
        row = self._pending(request_id)
        admission = self._governance.admission_snapshot(request_id)
        if admission["admission_proven"] is not True:
            raise ProductRuntimeError("governed execution admission is not proven")
        lease = self._execution_lease(row, now=now)
        self._scheduler.authorize(lease, now=now)
        self._control_plane.transition_job(
            token,
            str(row["job_id"]),
            JobState.RUNNING,
            reason="governed product proof started",
            now=now,
        )
        deadline = now + timedelta(minutes=5)
        video_attempt = self._workflows.begin_attempt(
            str(row["workflow_id"]), "video", deadline=deadline
        )
        try:
            video = self._video.execute(
                request_id=request_id,
                job_id=str(row["job_id"]),
                grant_id=grant_id,
                now=now,
            )
        except Exception:
            self._workflows.fail_attempt(video_attempt.attempt_id, reason="video failed")
            self._control_plane.transition_job(
                token,
                str(row["job_id"]),
                JobState.FAILED,
                reason="governed video execution failed",
                now=now,
            )
            raise
        self._workflows.complete_attempt(video_attempt.attempt_id)
        self._control_plane.transition_job(
            token,
            str(row["job_id"]),
            JobState.VALIDATING,
            reason="video rendered; validating delivery",
            now=now,
        )
        delivery_attempt = self._workflows.begin_attempt(
            str(row["workflow_id"]), "delivery", deadline=deadline
        )
        delivery = cast(dict[str, Any], video["delivery"])
        verified_delivery = self._video.get_delivery(str(delivery["delivery_id"]))
        if verified_delivery["sha256"] != video["artifact_digest"]:
            self._workflows.fail_attempt(
                delivery_attempt.attempt_id, reason="delivery integrity failed"
            )
            raise ProductRuntimeError("delivery does not match evidence artifact")
        self._workflows.complete_attempt(delivery_attempt.attempt_id)
        self._scheduler.record_side_effect(
            lease,
            now=now,
            payload={
                "request_id": request_id,
                "delivery_id": verified_delivery["delivery_id"],
                "artifact_digest": video["artifact_digest"],
            },
        )
        completed_job = self._control_plane.transition_job(
            token,
            str(row["job_id"]),
            JobState.COMPLETED,
            reason="delivery and acceptance evidence verified",
            now=now,
        )
        workflow_tasks = self._workflows.task_state(str(row["workflow_id"]))
        dag_proven = workflow_tasks == (
            {"task_id": "delivery", "status": "completed"},
            {"task_id": "video", "status": "completed"},
        )
        scheduler_state = self._scheduler.state()
        worker_lease_proven = any(
            effect["task_id"] == row["job_id"]
            and effect["fencing_token"] == lease.fencing_token
            for effect in scheduler_state["effects"]
        )
        grant_state = self._grants.state()
        grants = cast(list[dict[str, object]], grant_state["grants"])
        grant_proven = any(
            grant["grant_id"] == grant_id and grant["used_side_effects"] == 1
            for grant in grants
        )
        approval_proven = bool(admission["approval_proven"])
        admission_proven = bool(admission["admission_proven"])
        cost_proven = video["reserved_minor"] == video["actual_minor"]
        job_state_proven = completed_job.state is JobState.COMPLETED
        qa = cast(dict[str, object], video["qa"])
        accepted = all(
            (
                admission_proven,
                dag_proven,
                worker_lease_proven,
                grant_proven,
                cost_proven,
                job_state_proven,
                qa.get("passed") is True,
                verified_delivery["sha256"] == video["artifact_digest"],
            )
        )
        if not accepted:
            raise ProductRuntimeError("durable AcceptanceManifest checks failed")
        manifest: dict[str, object] = {
            "manifest_version": "1.0",
            "request_id": request_id,
            "goal_id": row["goal_id"],
            "job_id": row["job_id"],
            "proposal_id": row["proposal_id"],
            "workflow_id": row["workflow_id"],
            "worker_id": row["worker_id"],
            "grant_id": grant_id,
            "risk": admission["risk"],
            "admission_decision": admission["admission_decision"],
            "human_approval_required": admission["human_approval_required"],
            "admission_proven": admission_proven,
            "approval_proven": approval_proven,
            "dag_proven": dag_proven,
            "workflow_tasks": workflow_tasks,
            "worker_lease_proven": worker_lease_proven,
            "grant_proven": grant_proven,
            "cost_proven": cost_proven,
            "job_state_proven": job_state_proven,
            "evidence_hash": video["provenance_record_hash"],
            "artifact_digest": video["artifact_digest"],
            "delivery_id": verified_delivery["delivery_id"],
            "delivery_sha256": verified_delivery["sha256"],
            "qa": qa,
            "latency_ms": video["latency_ms"],
            "accepted": accepted,
        }
        with self._connect() as connection:
            connection.execute(
                "UPDATE product_proofs SET status = 'accepted', manifest_json = ? "
                "WHERE request_id = ?",
                (json.dumps(manifest, sort_keys=True), request_id),
            )
        return manifest

    def get_manifest(self, request_id: str) -> dict[str, object]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT status, manifest_json FROM product_proofs WHERE request_id = ?",
                (request_id,),
            ).fetchone()
        if row is None or row["status"] != "accepted" or row["manifest_json"] is None:
            raise ProductRuntimeError("accepted product proof is unavailable")
        value = json.loads(row["manifest_json"])
        if not isinstance(value, dict):
            raise ProductRuntimeError("stored AcceptanceManifest is malformed")
        return cast(dict[str, object], value)

    def _pending(self, request_id: str) -> sqlite3.Row:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM product_proofs WHERE request_id = ?", (request_id,)
            ).fetchone()
        if row is None or row["status"] != "pending":
            raise ProductRuntimeError("product proof is not pending")
        return cast(sqlite3.Row, row)

    def _execution_lease(self, row: sqlite3.Row, *, now: datetime) -> Lease:
        raw = json.loads(str(row["lease_json"]))
        if not isinstance(raw, dict):
            raise ProductRuntimeError("stored product lease is malformed")
        lease_raw = cast(dict[str, Any], raw)
        required = {"task_id", "worker_id", "fencing_token", "expires_at"}
        if not required <= lease_raw.keys():
            lease = self._scheduler.schedule(str(row["job_id"]), "video", now=now)
            self._store_lease(str(row["request_id"]), lease)
            return lease
        try:
            lease = Lease(
                str(lease_raw["task_id"]),
                str(lease_raw["worker_id"]),
                int(lease_raw["fencing_token"]),
                datetime.fromisoformat(str(lease_raw["expires_at"])),
            )
        except (TypeError, ValueError) as error:
            raise ProductRuntimeError("stored product lease is malformed") from error
        if lease.expires_at <= now:
            lease = self._scheduler.reschedule_expired(
                str(row["job_id"]), "video", now=now
            )
            self._store_lease(str(row["request_id"]), lease)
        return lease

    def _store_lease(self, request_id: str, lease: Lease) -> None:
        with self._connect() as connection:
            connection.execute(
                "UPDATE product_proofs SET lease_json = ? WHERE request_id = ?",
                (json.dumps(_lease_json(lease), sort_keys=True), request_id),
            )


def _lease_json(lease: Lease) -> dict[str, object]:
    return {
        "task_id": lease.task_id,
        "worker_id": lease.worker_id,
        "fencing_token": lease.fencing_token,
        "expires_at": lease.expires_at.isoformat(),
    }


def _require_identity(value: str, field: str) -> None:
    if not value or any(
        character
        not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
        for character in value
    ):
        raise ProductRuntimeError(f"invalid {field}")


def _require_actor(value: str, field: str) -> None:
    if (
        not value
        or value != value.strip()
        or len(value) > 512
        or any(ord(character) < 32 or ord(character) == 127 for character in value)
    ):
        raise ProductRuntimeError(f"invalid {field}")
