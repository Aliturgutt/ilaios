"""Crash-recoverable bounded Software finished-product runtime.

This module preserves the reviewed local task-manager builder and composes it with
a durable cross-store finalization saga. Verified evidence is persisted under a
``finalizing`` proof before the Control Plane may become ``COMPLETED``.
"""

from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import cast

from services.control_plane import ControlPlane
from services.control_plane.workflows import WorkflowStore
from services.evidence import EvidenceStore
from services.governance import GovernedRuntimeGateway
from services.runtime import DurableGrantPolicy, DurableWorkerScheduler
from src.video_automation.models import JobState

from .product_runtime import ProductFinalizationPending
from .software_product_runtime_legacy import (
    DurableSoftwareProductRuntime as _LegacyDurableSoftwareProductRuntime,
    FinishedSoftwareBuilder,
    SoftwareProductRuntimeError,
    SoftwareProductSecurityError,
    SoftwareProductValidationError,
)


class SoftwareProductFinalizationPending(ProductFinalizationPending):
    """Software acceptance is durably finalizing and requires reconciliation."""


class DurableSoftwareProductRuntime(_LegacyDurableSoftwareProductRuntime):
    """Software runtime with crash-safe finalization and explicit lease closure."""

    def __init__(
        self,
        database_path: Path,
        control_plane: ControlPlane,
        workflows: WorkflowStore,
        scheduler: DurableWorkerScheduler,
        grants: DurableGrantPolicy,
        governance: GovernedRuntimeGateway,
        evidence: EvidenceStore,
        product_root: Path,
        *,
        source_head_sha: str,
    ) -> None:
        super().__init__(
            database_path,
            control_plane,
            workflows,
            scheduler,
            grants,
            governance,
            evidence,
            product_root,
            source_head_sha=source_head_sha,
        )
        with self._connect() as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS software_product_closure ("
                "request_id TEXT PRIMARY KEY, terminal_status TEXT NOT NULL, "
                "reason TEXT NOT NULL, terminal_at TEXT NOT NULL)"
            )

    def execute(
        self, request_id: str, grant_id: str, *, token: str, now: datetime
    ) -> dict[str, object]:
        if now.tzinfo is None:
            raise SoftwareProductRuntimeError(
                "software execution time must be timezone-aware"
            )
        row = self._pending(request_id)
        admission = self._governance.admission_snapshot(request_id)
        if admission["admission_proven"] is not True:
            raise SoftwareProductRuntimeError(
                "governed software admission is not proven"
            )
        lease = self._execution_lease(row, now)
        self._scheduler.authorize(lease, now=now)
        self._control_plane.transition_job(
            token,
            str(row["job_id"]),
            JobState.RUNNING,
            reason="governed Software Factory finished-product execution started",
            now=now,
        )
        amount = self._governance.authorize_billable(request_id)
        started = time.monotonic()
        software_attempt = self._workflows.begin_attempt(
            str(row["workflow_id"]), "software", deadline=now + timedelta(minutes=5)
        )
        software_done = False
        delivery_attempt = None
        delivery_done = False
        finalizing = False
        lease_released = False
        try:
            self._grants.authorize_and_record(
                grant_id,
                subject_id="worker-software",
                action="software.execute",
                resource=str(row["job_id"]),
                now=now,
            )
            product = self._builder.build(request_id, str(row["objective"]))
            artifact = self._evidence.put_artifact(
                cast(bytes, product.pop("artifact_bytes"))
            )
            provenance = self._evidence.append_provenance(
                str(row["job_id"]), artifact, "software.local.finished-product"
            )
            self._workflows.complete_attempt(software_attempt.attempt_id)
            software_done = True
            self._control_plane.transition_job(
                token,
                str(row["job_id"]),
                JobState.VALIDATING,
                reason="software built and runtime-tested; validating delivery",
                now=now,
            )
            delivery_attempt = self._workflows.begin_attempt(
                str(row["workflow_id"]),
                "delivery",
                deadline=now + timedelta(minutes=5),
            )
            if (
                hashlib.sha256(
                    self._evidence.get_artifact(artifact.digest)
                ).hexdigest()
                != artifact.digest
            ):
                raise SoftwareProductRuntimeError(
                    "software delivery integrity failed"
                )
            self._workflows.complete_attempt(delivery_attempt.attempt_id)
            delivery_done = True
            self._scheduler.record_side_effect(
                lease,
                now=now,
                payload={"request_id": request_id, "artifact_digest": artifact.digest},
            )
            tasks = self._workflows.task_state(str(row["workflow_id"]))
            dag_proven = tasks == (
                {"task_id": "delivery", "status": "completed"},
                {"task_id": "software", "status": "completed"},
            )
            scheduler_state = self._scheduler.state()
            lease_proven = any(
                effect["task_id"] == row["job_id"]
                and effect["fencing_token"] == lease.fencing_token
                for effect in scheduler_state["effects"]
            )
            grants = cast(
                list[dict[str, object]], self._grants.state()["grants"]
            )
            grant_proven = any(
                item["grant_id"] == grant_id and item["used_side_effects"] == 1
                for item in grants
            )
            job_ready = (
                self._control_plane.get_job(token, str(row["job_id"])).state
                is JobState.VALIDATING
            )
            finalization_ready = all(
                (
                    dag_proven,
                    lease_proven,
                    grant_proven,
                    job_ready,
                    cast(dict[str, object], product["security_result"])["passed"]
                    is True,
                    cast(dict[str, object], product["test_result"])["passed"] is True,
                    cast(dict[str, object], product["build_result"])["passed"]
                    is True,
                    cast(dict[str, object], product["runtime_result"])["passed"]
                    is True,
                )
            )
            if not finalization_ready:
                raise SoftwareProductRuntimeError(
                    "software AcceptanceManifest checks failed"
                )
            manifest: dict[str, object] = {
                "manifest_version": "1.1",
                "request_sha256": hashlib.sha256(
                    str(row["objective"]).encode()
                ).hexdigest(),
                "request_id": request_id,
                "job_id": row["job_id"],
                "goal_id": row["goal_id"],
                "proposal_id": row["proposal_id"],
                "factory": "ilaios.capability.software-factory",
                "adapter_id": "software.product-runtime.v1",
                "base_sha": self._source_head_sha,
                "source_head_sha": self._source_head_sha,
                "generated_files": product["generated_files"],
                "generated_source_sha256": product["generated_source_sha256"],
                "dependency_evidence": product["dependency_evidence"],
                "license_evidence": product["license_evidence"],
                "sbom": product["sbom"],
                "security_result": product["security_result"],
                "test_result": product["test_result"],
                "build_result": product["build_result"],
                "runtime_result": product["runtime_result"],
                "repair_history": product["repair_history"],
                "artifact_path": str(artifact.path),
                "artifact_sha256": artifact.digest,
                "artifact_size": artifact.size,
                "provenance_record_hash": provenance.record_hash,
                "admission_proven": admission["admission_proven"],
                "worker_lease_proven": lease_proven,
                "grant_proven": grant_proven,
                "dag_proven": dag_proven,
                "provider_mode": "LOCAL_FREE_ONLY",
                "external_provider_cost_minor": 0,
                "governance_reserved_minor": amount,
                "governance_actual_minor": amount,
                "latency_ms": int((time.monotonic() - started) * 1000),
                "job_state_proven": False,
                "finalization_status": "finalizing",
                "final_disposition": "PENDING_FINALIZATION",
                "accepted": False,
                "commercial_release_pass": False,
            }
            if not self._scheduler.release(lease):
                raise SoftwareProductRuntimeError(
                    "software worker lease disappeared before product closure"
                )
            lease_released = True
            serialized = json.dumps(manifest, sort_keys=True)
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                changed = connection.execute(
                    "UPDATE software_product_proofs SET status='finalizing', "
                    "lease_json='{}', manifest_json=? "
                    "WHERE request_id=? AND status='pending'",
                    (serialized, request_id),
                ).rowcount
            if changed != 1:
                raise SoftwareProductRuntimeError(
                    "software finalization state changed concurrently"
                )
            finalizing = True
            try:
                return self.recover_finalizing(request_id, token=token, now=now)
            except Exception as error:
                raise SoftwareProductFinalizationPending(
                    "software acceptance is durably finalizing and requires recovery"
                ) from error
        except SoftwareProductFinalizationPending:
            raise
        except Exception:
            if delivery_attempt is not None and not delivery_done:
                try:
                    self._workflows.fail_attempt(
                        delivery_attempt.attempt_id, reason="delivery failed"
                    )
                except Exception:
                    pass
            if not software_done:
                try:
                    self._workflows.fail_attempt(
                        software_attempt.attempt_id, reason="software failed"
                    )
                except Exception:
                    pass
            if not finalizing:
                try:
                    self._governance.reconcile_billable(
                        request_id, actual_minor=0, status="failed"
                    )
                except Exception:
                    pass
                try:
                    self._control_plane.transition_job(
                        token,
                        str(row["job_id"]),
                        JobState.FAILED,
                        reason="Software Factory finished-product execution failed",
                        now=now,
                    )
                except Exception:
                    pass
            raise
        finally:
            if not lease_released:
                try:
                    self._scheduler.release(lease)
                except Exception:
                    pass

    def recover_finalizing(
        self, request_id: str, *, token: str, now: datetime
    ) -> dict[str, object]:
        """Idempotently finish a crash-interrupted Software acceptance saga."""
        if now.tzinfo is None:
            raise SoftwareProductRuntimeError(
                "software finalization time must be timezone-aware"
            )
        with self._connect() as connection:
            row = connection.execute(
                "SELECT status, job_id, manifest_json FROM software_product_proofs "
                "WHERE request_id=?",
                (request_id,),
            ).fetchone()
        if row is None:
            raise SoftwareProductRuntimeError(
                "software proof request is unavailable"
            )
        if row["status"] == "accepted":
            return self.get_manifest(request_id)
        if row["status"] != "finalizing" or row["manifest_json"] is None:
            raise SoftwareProductRuntimeError("software proof is not finalizing")
        value = json.loads(str(row["manifest_json"]))
        if not isinstance(value, dict):
            raise SoftwareProductRuntimeError(
                "stored finalizing Software manifest is malformed"
            )
        manifest = cast(dict[str, object], value)
        if not all(
            (
                manifest.get("adapter_id") == "software.product-runtime.v1",
                manifest.get("request_id") == request_id,
                manifest.get("job_id") == row["job_id"],
                manifest.get("admission_proven") is True,
                manifest.get("worker_lease_proven") is True,
                manifest.get("grant_proven") is True,
                manifest.get("dag_proven") is True,
                cast(dict[str, object], manifest.get("security_result", {})).get(
                    "passed"
                )
                is True,
                cast(dict[str, object], manifest.get("test_result", {})).get(
                    "passed"
                )
                is True,
                cast(dict[str, object], manifest.get("build_result", {})).get(
                    "passed"
                )
                is True,
                cast(dict[str, object], manifest.get("runtime_result", {})).get(
                    "passed"
                )
                is True,
                bool(manifest.get("artifact_sha256")),
                manifest.get("finalization_status") == "finalizing",
                manifest.get("accepted") is False,
            )
        ):
            raise SoftwareProductRuntimeError(
                "stored finalizing Software evidence is incomplete"
            )
        job_id = str(row["job_id"])
        current = self._control_plane.get_job(token, job_id)
        if current.state is JobState.VALIDATING:
            try:
                current = self._control_plane.transition_job(
                    token,
                    job_id,
                    JobState.COMPLETED,
                    reason="durable Software product finalization evidence verified",
                    now=now,
                )
            except Exception as error:
                current = self._control_plane.get_job(token, job_id)
                if current.state is not JobState.COMPLETED:
                    raise SoftwareProductRuntimeError(
                        "Software job completion could not be reconciled"
                    ) from error
        if current.state is not JobState.COMPLETED:
            raise SoftwareProductRuntimeError(
                "finalizing Software product job is not completable"
            )
        manifest["job_state_proven"] = True
        manifest["finalization_status"] = "accepted"
        manifest["final_disposition"] = "ACCEPT"
        manifest["accepted"] = True
        actual_minor = manifest.get("governance_actual_minor")
        if not isinstance(actual_minor, int) or isinstance(actual_minor, bool):
            raise SoftwareProductRuntimeError(
                "stored Software governance cost evidence is malformed"
            )
        self._governance.reconcile_billable(
            request_id,
            actual_minor=actual_minor,
            status="executed",
            result=manifest,
        )
        serialized = json.dumps(manifest, sort_keys=True)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            current_row = connection.execute(
                "SELECT status, manifest_json FROM software_product_proofs "
                "WHERE request_id=?",
                (request_id,),
            ).fetchone()
            if current_row is None:
                raise SoftwareProductRuntimeError(
                    "software proof request is unavailable"
                )
            if current_row["status"] == "accepted":
                stored = current_row["manifest_json"]
                if stored is None:
                    raise SoftwareProductRuntimeError(
                        "accepted Software manifest is missing"
                    )
                accepted_value = json.loads(str(stored))
                if not isinstance(accepted_value, dict):
                    raise SoftwareProductRuntimeError(
                        "stored Software manifest is malformed"
                    )
                return cast(dict[str, object], accepted_value)
            if current_row["status"] != "finalizing":
                raise SoftwareProductRuntimeError(
                    "software finalization state changed concurrently"
                )
            changed = connection.execute(
                "UPDATE software_product_proofs SET status='accepted', manifest_json=? "
                "WHERE request_id=? AND status='finalizing'",
                (serialized, request_id),
            ).rowcount
            if changed != 1:
                raise SoftwareProductRuntimeError(
                    "software finalization state changed concurrently"
                )
            connection.execute(
                "INSERT OR IGNORE INTO software_product_closure VALUES "
                "(?, 'accepted', ?, ?)",
                (
                    request_id,
                    "software artifact, governance and cross-store acceptance evidence verified",
                    now.isoformat(),
                ),
            )
        return manifest


__all__ = [
    "DurableSoftwareProductRuntime",
    "FinishedSoftwareBuilder",
    "SoftwareProductFinalizationPending",
    "SoftwareProductRuntimeError",
    "SoftwareProductSecurityError",
    "SoftwareProductValidationError",
]
