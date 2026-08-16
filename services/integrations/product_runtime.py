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


class ProductFinalizationPending(ProductRuntimeError):
    """Raised when acceptance reached a durable recoverable finalization boundary."""


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
            connection.execute(
                "CREATE TABLE IF NOT EXISTS product_proof_identity ("
                "request_id TEXT PRIMARY KEY, requester_id TEXT NOT NULL, tenant_id TEXT)"
            )
            connection.execute(
                "CREATE TABLE IF NOT EXISTS product_proof_closure ("
                "request_id TEXT PRIMARY KEY, terminal_status TEXT NOT NULL, "
                "reason TEXT NOT NULL, terminal_at TEXT NOT NULL)"
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path, timeout=10)
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
        risk: str = "medium",
        data_class: DataClass = DataClass.INTERNAL,
        budget: BudgetEnvelope | None = None,
    ) -> dict[str, object]:
        _require_identity(request_id, "request_id")
        _require_actor(requester_id, "requester_id")
        if tenant_id is not None:
            _require_actor(tenant_id, "tenant_id")
        if risk not in {"low", "medium", "high"}:
            raise ProductRuntimeError("unknown product risk classification")
        if not isinstance(data_class, DataClass):
            raise ProductRuntimeError("unknown product data classification")
        execution_budget = budget or BudgetEnvelope(1, 60, 10)
        risk_class = RiskClass(risk)

        goal = self._control_plane.create_goal(token, objective)
        job = self._control_plane.create_job(token, goal.goal_id)
        proposal = self._control_plane.create_proposal(
            token,
            goal.goal_id,
            acceptance_criteria=(
                "Canonical governed video workflow completes",
                "Verified delivery and AcceptanceManifest exist",
            ),
            risk_class=risk_class,
            data_class=data_class,
            budget=execution_budget,
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
            risk=risk,
        )
        admission_decision = admission.get("admission_decision")
        human_approval_required = admission.get("human_approval_required")
        valid_admission = (
            risk in {"low", "medium"}
            and admission_decision == "ALLOW"
            and human_approval_required is False
        ) or (
            risk == "high"
            and admission_decision == "REQUIRE_APPROVAL"
            and human_approval_required is True
        )
        if not valid_admission:
            if lease is not None:
                self._scheduler.release(lease)
            raise ProductRuntimeError("product admission policy is inconsistent")
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
                connection.execute(
                    "INSERT INTO product_proof_identity VALUES (?, ?, ?)",
                    (request_id, requester_id, tenant_id),
                )
            except sqlite3.IntegrityError as error:
                if lease is not None:
                    self._scheduler.release(lease)
                raise ProductRuntimeError("product proof request already exists") from error
        return {
            "request_id": request_id,
            "requester_id": requester_id,
            "tenant_id": tenant_id,
            "goal_id": goal.goal_id,
            "job_id": job.job_id,
            "proposal_id": proposal_id,
            "workflow_id": workflow_id,
            "worker_id": worker_id,
            "lease": None if lease is None else _lease_json(lease),
            "risk": risk,
            "data_class": data_class.value,
            "budget": {
                "max_attempts": execution_budget.max_attempts,
                "max_runtime_seconds": execution_budget.max_runtime_seconds,
                "max_external_spend_minor": execution_budget.max_external_spend_minor,
            },
            "admission_decision": admission_decision,
            "human_approval_required": human_approval_required,
            "status": "pending_approval"
            if human_approval_required is True
            else "admitted_pending_grant",
        }

    def execute(
        self, request_id: str, grant_id: str, *, token: str, now: datetime
    ) -> dict[str, object]:
        row = self._pending(request_id)
        identity = self._identity(request_id)
        lease: Lease | None = None
        try:
            admission = self._governance.admission_snapshot(request_id)
            if admission["admission_proven"] is not True:
                raise ProductRuntimeError("governed execution admission is not proven")
            identity_proven = bool(identity["requester_id"])
            if not identity_proven:
                raise ProductRuntimeError("product proof identity is not durable")
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
                    "requester_id": identity["requester_id"],
                    "tenant_id": identity["tenant_id"],
                    "delivery_id": verified_delivery["delivery_id"],
                    "artifact_digest": video["artifact_digest"],
                },
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
            job_ready_proven = (
                self._control_plane.get_job(token, str(row["job_id"])).state
                is JobState.VALIDATING
            )
            qa = cast(dict[str, object], video["qa"])
            finalization_ready = all(
                (
                    admission_proven,
                    identity_proven,
                    dag_proven,
                    worker_lease_proven,
                    grant_proven,
                    cost_proven,
                    job_ready_proven,
                    qa.get("passed") is True,
                    verified_delivery["sha256"] == video["artifact_digest"],
                )
            )
            if not finalization_ready:
                raise ProductRuntimeError("durable AcceptanceManifest checks failed")
            manifest: dict[str, object] = {
                "manifest_version": "1.0",
                "request_id": request_id,
                "requester_id": identity["requester_id"],
                "tenant_id": identity["tenant_id"],
                "identity_proven": identity_proven,
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
                "job_state_proven": False,
                "evidence_hash": video["provenance_record_hash"],
                "artifact_digest": video["artifact_digest"],
                "delivery_id": verified_delivery["delivery_id"],
                "delivery_sha256": verified_delivery["sha256"],
                "qa": qa,
                "latency_ms": video["latency_ms"],
                "finalization_status": "finalizing",
                "accepted": False,
            }
            if not self._scheduler.release(lease):
                raise ProductRuntimeError("worker lease disappeared before product closure")
            lease = None
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                changed = connection.execute(
                    "UPDATE product_proofs SET status = 'finalizing', manifest_json = ? "
                    "WHERE request_id = ? AND status = 'pending'",
                    (json.dumps(manifest, sort_keys=True), request_id),
                ).rowcount
            if changed != 1:
                raise ProductRuntimeError("product finalization state changed concurrently")
            try:
                return self.recover_finalizing(request_id, token=token, now=now)
            except Exception as error:
                raise ProductFinalizationPending(
                    "product acceptance is durably finalizing and requires recovery"
                ) from error
        except ProductFinalizationPending:
            raise
        except Exception as error:
            self._fail_product_proof(row, token=token, now=now, error=error)
            raise
        finally:
            if lease is not None:
                self._scheduler.release(lease)

    def recover_finalizing(
        self, request_id: str, *, token: str, now: datetime
    ) -> dict[str, object]:
        """Idempotently finish a crash-interrupted cross-store acceptance saga."""
        if now.tzinfo is None:
            raise ProductRuntimeError("finalization time must be timezone-aware")
        with self._connect() as connection:
            row = connection.execute(
                "SELECT status, job_id, manifest_json FROM product_proofs "
                "WHERE request_id = ?",
                (request_id,),
            ).fetchone()
        if row is None:
            raise ProductRuntimeError("unknown product proof")
        if row["status"] == "accepted":
            return self.get_manifest(request_id)
        if row["status"] != "finalizing" or row["manifest_json"] is None:
            raise ProductRuntimeError("product proof is not finalizing")
        value = json.loads(str(row["manifest_json"]))
        if not isinstance(value, dict):
            raise ProductRuntimeError("stored finalizing AcceptanceManifest is malformed")
        manifest = cast(dict[str, object], value)
        qa = manifest.get("qa")
        if not isinstance(qa, dict):
            raise ProductRuntimeError("stored finalizing QA evidence is malformed")
        if not all(
            (
                manifest.get("admission_proven") is True,
                manifest.get("identity_proven") is True,
                manifest.get("dag_proven") is True,
                manifest.get("worker_lease_proven") is True,
                manifest.get("grant_proven") is True,
                manifest.get("cost_proven") is True,
                qa.get("passed") is True,
                manifest.get("artifact_digest") == manifest.get("delivery_sha256"),
            )
        ):
            raise ProductRuntimeError("stored finalizing evidence is incomplete")

        job_id = str(row["job_id"])
        current = self._control_plane.get_job(token, job_id)
        if current.state is JobState.VALIDATING:
            try:
                current = self._control_plane.transition_job(
                    token,
                    job_id,
                    JobState.COMPLETED,
                    reason="durable product finalization evidence verified",
                    now=now,
                )
            except Exception as error:
                current = self._control_plane.get_job(token, job_id)
                if current.state is not JobState.COMPLETED:
                    raise ProductRuntimeError(
                        "job completion could not be reconciled"
                    ) from error
        if current.state is not JobState.COMPLETED:
            raise ProductRuntimeError("finalizing product job is not completable")

        manifest["job_state_proven"] = True
        manifest["finalization_status"] = "accepted"
        manifest["accepted"] = True
        serialized = json.dumps(manifest, sort_keys=True)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            current_row = connection.execute(
                "SELECT status, manifest_json FROM product_proofs WHERE request_id = ?",
                (request_id,),
            ).fetchone()
            if current_row is None:
                raise ProductRuntimeError("unknown product proof")
            if current_row["status"] == "accepted":
                stored = current_row["manifest_json"]
                if stored is None:
                    raise ProductRuntimeError("accepted product manifest is missing")
                accepted_value = json.loads(str(stored))
                if not isinstance(accepted_value, dict):
                    raise ProductRuntimeError("stored AcceptanceManifest is malformed")
                return cast(dict[str, object], accepted_value)
            if current_row["status"] != "finalizing":
                raise ProductRuntimeError("product finalization state changed concurrently")
            changed = connection.execute(
                "UPDATE product_proofs SET status = 'accepted', manifest_json = ? "
                "WHERE request_id = ? AND status = 'finalizing'",
                (serialized, request_id),
            ).rowcount
            if changed != 1:
                raise ProductRuntimeError("product finalization state changed concurrently")
            connection.execute(
                "INSERT OR IGNORE INTO product_proof_closure VALUES (?, 'accepted', ?, ?)",
                (
                    request_id,
                    "delivery, identity, and cross-store acceptance evidence verified",
                    now.isoformat(),
                ),
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

    def get_state(self, request_id: str) -> dict[str, object]:
        """Return product-proof terminal truth without treating failure as acceptance."""
        identity = self._identity(request_id)
        with self._connect() as connection:
            row = connection.execute(
                "SELECT status FROM product_proofs WHERE request_id = ?", (request_id,)
            ).fetchone()
            closure = connection.execute(
                "SELECT terminal_status, reason, terminal_at FROM product_proof_closure "
                "WHERE request_id = ?",
                (request_id,),
            ).fetchone()
        if row is None:
            raise ProductRuntimeError("unknown product proof")
        return {
            "request_id": request_id,
            "requester_id": identity["requester_id"],
            "tenant_id": identity["tenant_id"],
            "status": str(row["status"]),
            "terminal": closure is not None,
            "terminal_status": None if closure is None else str(closure["terminal_status"]),
            "reason": None if closure is None else str(closure["reason"]),
            "terminal_at": None if closure is None else str(closure["terminal_at"]),
        }

    def interrupt(
        self,
        request_id: str,
        *,
        token: str,
        now: datetime,
        reason: str,
    ) -> dict[str, object]:
        """Close a stale or explicitly cancelled product proof and owned resources."""
        _require_actor(reason, "reason")
        if now.tzinfo is None:
            raise ProductRuntimeError("interruption time must be timezone-aware")
        terminal_status = (
            "cancelled"
            if reason == "cancelled by authenticated execution owner"
            else "interrupted"
        )
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM product_proofs WHERE request_id = ?", (request_id,)
            ).fetchone()
        if row is None:
            raise ProductRuntimeError("unknown product proof")
        if row["status"] != "pending":
            return self.get_state(request_id)

        lease = _optional_lease(str(row["lease_json"]))
        if lease is not None:
            try:
                self._scheduler.release(lease)
            except Exception as error:
                raise ProductRuntimeError(
                    "worker lease cleanup failed during interruption"
                ) from error
        self._workflows.cancel_workflow(
            str(row["workflow_id"]), reason=reason, now=now
        )
        current = self._control_plane.get_job(token, str(row["job_id"]))
        if current.state not in {JobState.COMPLETED, JobState.FAILED, JobState.CANCELLED}:
            self._control_plane.transition_job(
                token,
                str(row["job_id"]),
                JobState.CANCELLED,
                reason=f"finished-product execution {terminal_status}",
                now=now,
            )
        with self._connect() as connection:
            changed = connection.execute(
                "UPDATE product_proofs SET status = ? "
                "WHERE request_id = ? AND status = 'pending'",
                (terminal_status, request_id),
            ).rowcount
            if changed == 1:
                connection.execute(
                    "INSERT OR IGNORE INTO product_proof_closure VALUES (?, ?, ?, ?)",
                    (request_id, terminal_status, reason, now.isoformat()),
                )
        return self.get_state(request_id)

    def _pending(self, request_id: str) -> sqlite3.Row:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM product_proofs WHERE request_id = ?", (request_id,)
            ).fetchone()
        if row is None or row["status"] != "pending":
            raise ProductRuntimeError("product proof is not pending")
        return cast(sqlite3.Row, row)

    def _identity(self, request_id: str) -> dict[str, str | None]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT requester_id, tenant_id FROM product_proof_identity WHERE request_id = ?",
                (request_id,),
            ).fetchone()
        if row is None:
            raise ProductRuntimeError("product proof identity is unavailable")
        return {
            "requester_id": str(row["requester_id"]),
            "tenant_id": None if row["tenant_id"] is None else str(row["tenant_id"]),
        }

    def _fail_product_proof(
        self,
        row: sqlite3.Row,
        *,
        token: str,
        now: datetime,
        error: Exception,
    ) -> None:
        request_id = str(row["request_id"])
        job_id = str(row["job_id"])
        workflow_id = str(row["workflow_id"])
        reason = _failure_reason(error)
        cleanup_failures: list[str] = []
        try:
            self._workflows.cancel_workflow(workflow_id, reason=reason, now=now)
        except Exception as cleanup_error:
            cleanup_failures.append(f"workflow={type(cleanup_error).__name__}")
        try:
            current = self._control_plane.get_job(token, job_id)
            if current.state is JobState.PENDING:
                self._control_plane.transition_job(
                    token,
                    job_id,
                    JobState.CANCELLED,
                    reason="finished-product execution failed before start",
                    now=now,
                )
            elif current.state in {
                JobState.RUNNING,
                JobState.WAITING_PROVIDER,
                JobState.VALIDATING,
                JobState.RETRY_PENDING,
            }:
                self._control_plane.transition_job(
                    token,
                    job_id,
                    JobState.FAILED,
                    reason="finished-product execution failed closed",
                    now=now,
                )
        except Exception as cleanup_error:
            cleanup_failures.append(f"job={type(cleanup_error).__name__}")
        closure_reason = reason
        if cleanup_failures:
            closure_reason = f"{reason}; cleanup_failures={','.join(cleanup_failures)}"[:2048]
        with self._connect() as connection:
            connection.execute(
                "UPDATE product_proofs SET status = 'failed' "
                "WHERE request_id = ? AND status = 'pending'",
                (request_id,),
            )
            connection.execute(
                "INSERT OR IGNORE INTO product_proof_closure VALUES (?, 'failed', ?, ?)",
                (request_id, closure_reason, now.isoformat()),
            )

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


def _optional_lease(raw_json: str) -> Lease | None:
    try:
        raw = json.loads(raw_json)
    except (TypeError, ValueError, json.JSONDecodeError) as error:
        raise ProductRuntimeError("stored product lease is malformed") from error
    if not isinstance(raw, dict):
        raise ProductRuntimeError("stored product lease is malformed")
    required = {"task_id", "worker_id", "fencing_token", "expires_at"}
    if not required <= raw.keys():
        return None
    try:
        return Lease(
            str(raw["task_id"]),
            str(raw["worker_id"]),
            int(raw["fencing_token"]),
            datetime.fromisoformat(str(raw["expires_at"])),
        )
    except (TypeError, ValueError) as error:
        raise ProductRuntimeError("stored product lease is malformed") from error


def _lease_json(lease: Lease) -> dict[str, object]:
    return {
        "task_id": lease.task_id,
        "worker_id": lease.worker_id,
        "fencing_token": lease.fencing_token,
        "expires_at": lease.expires_at.isoformat(),
    }


def _failure_reason(error: Exception) -> str:
    message = " ".join(str(error).split())
    if not message:
        message = "execution failed without an error message"
    return f"{type(error).__name__}: {message}"[:2048]


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
