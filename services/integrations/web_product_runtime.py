"""Durable crash-safe one-prompt Web finished-product adapter.

The runtime composes the canonical Control Plane, governance, durable grants,
first-party Web Factory and source-project materializer. Verified acceptance is
persisted as ``finalizing`` before the authoritative job may become COMPLETED,
so a process crash cannot create a false-completion window.
"""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import cast

from services.control_plane import (
    BudgetEnvelope,
    ControlPlane,
    DataClass,
    ProposedTask,
    RiskClass,
)
from services.governance import GovernedRuntimeGateway
from services.runtime import (
    BlastRadiusBudget,
    DurableGrantPolicy,
    ExecutionGrant,
    GrantPolicy,
)
from src.video_automation.models import JobState

from .product_runtime import ProductFinalizationPending
from .web_factory import (
    GovernedWebFactory,
    WebsiteAcceptance,
    WebsiteSpec,
    derive_website_spec,
)
from .web_project import materialize_next_project

_VERIFIED_LOCAL_FEATURES = frozenset({"contact-form"})


class WebProductRuntimeError(RuntimeError):
    """Raised when a requested website cannot pass its bounded acceptance contract."""


class WebProductFinalizationPending(ProductFinalizationPending):
    """Durable Web acceptance is finalizing and must be reconciled, not failed."""


class DurableWebProductRuntime:
    """Canonical governed Web finished-product adapter."""

    adapter_id = "web.product-runtime.v1"

    def __init__(
        self,
        database_path: Path,
        control_plane: ControlPlane,
        grants: DurableGrantPolicy,
        governance: GovernedRuntimeGateway,
        artifact_root: Path,
    ) -> None:
        self._database_path = database_path
        self._control_plane = control_plane
        self._grants = grants
        self._governance = governance
        self._artifact_root = artifact_root
        self._factory = GovernedWebFactory(GrantPolicy(), artifact_root)
        artifact_root.mkdir(parents=True, exist_ok=True)
        database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS web_product_requests ("
                "request_id TEXT PRIMARY KEY, goal_id TEXT NOT NULL, "
                "job_id TEXT NOT NULL, proposal_id TEXT NOT NULL, "
                "principal_id TEXT NOT NULL, tenant_id TEXT NOT NULL, "
                "spec_json TEXT NOT NULL, status TEXT NOT NULL, manifest_json TEXT)"
            )
            connection.execute(
                "CREATE TABLE IF NOT EXISTS web_product_closure ("
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
        requester_id: str,
        tenant_id: str,
        risk: str = "medium",
        data_class: DataClass = DataClass.INTERNAL,
        budget: BudgetEnvelope = BudgetEnvelope(1, 60, 0),
    ) -> dict[str, object]:
        if now.tzinfo is None:
            raise WebProductRuntimeError("web execution time must be timezone-aware")
        spec = derive_website_spec(request_id, objective)
        unsupported = tuple(
            sorted(set(spec.features).difference(_VERIFIED_LOCAL_FEATURES))
        )
        if unsupported:
            raise WebProductRuntimeError(
                "requested web functionality has no verified finished-product adapter: "
                + ", ".join(unsupported)
            )
        try:
            risk_class = RiskClass(risk)
        except ValueError as error:
            raise WebProductRuntimeError("unsupported web risk classification") from error
        goal = self._control_plane.create_goal(token, objective)
        job = self._control_plane.create_job(token, goal.goal_id)
        proposal = self._control_plane.create_proposal(
            token,
            goal.goal_id,
            acceptance_criteria=(
                "Structured WebsiteSpec and context-derived design strategy exist",
                "First-party Next.js/React/TypeScript source is content addressed",
                "Rendered preview bundle passes bounded quality validation",
                "Acceptance binds request, tenant, source and artifact evidence",
            ),
            risk_class=risk_class,
            data_class=data_class,
            budget=budget,
            tasks=(
                ProposedTask("web-build", "Build governed finished website artifact"),
                ProposedTask(
                    "web-validate",
                    "Validate website artifact and acceptance evidence",
                    ("web-build",),
                ),
            ),
        )
        proposal_id = str(proposal["proposal_id"])
        admission = self._governance.submit(
            request_id,
            requester_id,
            "web-agent",
            "web-factory-finished-product-v1",
            "web",
            {
                "goal_id": goal.goal_id,
                "job_id": job.job_id,
                "tenant_id": tenant_id,
                "site_id": spec.site_id,
                "provider_policy": "LOCAL_FREE_ONLY",
            },
            (),
            risk=risk,
        )
        decision = str(admission.get("admission_decision", ""))
        human = bool(admission.get("human_approval_required", False))
        if decision not in {"ALLOW", "REQUIRE_APPROVAL"}:
            raise WebProductRuntimeError("web admission was denied or malformed")
        if decision == "ALLOW" and human:
            raise WebProductRuntimeError("web admission approval state is inconsistent")
        if decision == "REQUIRE_APPROVAL" and not human:
            raise WebProductRuntimeError("web approval requirement is inconsistent")
        with self._connect() as connection:
            try:
                connection.execute(
                    "INSERT INTO web_product_requests VALUES "
                    "(?, ?, ?, ?, ?, ?, ?, 'pending', NULL)",
                    (
                        request_id,
                        goal.goal_id,
                        job.job_id,
                        proposal_id,
                        requester_id,
                        tenant_id,
                        json.dumps(spec.to_dict(), sort_keys=True, separators=(",", ":")),
                    ),
                )
            except sqlite3.IntegrityError as error:
                raise WebProductRuntimeError("web product request already exists") from error
        return {
            "request_id": request_id,
            "requester_id": requester_id,
            "tenant_id": tenant_id,
            "goal_id": goal.goal_id,
            "job_id": job.job_id,
            "proposal_id": proposal_id,
            "site_id": spec.site_id,
            "adapter_id": self.adapter_id,
            "risk": risk,
            "data_class": data_class.value,
            "budget": {
                "max_attempts": budget.max_attempts,
                "max_runtime_seconds": budget.max_runtime_seconds,
                "max_external_spend_minor": budget.max_external_spend_minor,
            },
            "admission_decision": decision,
            "human_approval_required": human,
            "status": "pending_approval" if human else "admitted_pending_grant",
        }

    def execute(
        self,
        request_id: str,
        grant_id: str,
        *,
        token: str,
        now: datetime,
    ) -> dict[str, object]:
        if now.tzinfo is None:
            raise WebProductRuntimeError("web execution time must be timezone-aware")
        row = self._pending(request_id)
        try:
            admission = self._governance.admission_snapshot(request_id)
            if admission["admission_proven"] is not True:
                raise WebProductRuntimeError(
                    "governed web execution admission is not proven"
                )
            spec_value = json.loads(str(row["spec_json"]))
            if not isinstance(spec_value, dict):
                raise WebProductRuntimeError("stored WebsiteSpec is malformed")
            spec = WebsiteSpec.from_dict(cast(dict[str, object], spec_value))
            job_id = str(row["job_id"])
            self._control_plane.transition_job(
                token,
                job_id,
                JobState.RUNNING,
                reason="governed web finished-product build started",
                now=now,
            )
            self._grants.authorize_and_record(
                grant_id,
                subject_id="worker-web",
                action="web.build",
                resource=job_id,
                now=now,
            )
            local_grant = ExecutionGrant(
                f"actuator-{grant_id}",
                "web-worker",
                frozenset({"web.build"}),
                frozenset({spec.site_id}),
                now + timedelta(minutes=5),
                BlastRadiusBudget(max_side_effects=1, max_resources=1),
            )
            acceptance: WebsiteAcceptance = self._factory.build_generated_site(
                spec,
                grant=local_grant,
                now=now,
            )
            self._control_plane.transition_job(
                token,
                job_id,
                JobState.VALIDATING,
                reason="website built; validating acceptance evidence",
                now=now,
            )
            if (
                not acceptance.accepted
                or acceptance.qa is None
                or acceptance.qa.get("passed") is not True
                or acceptance.design_strategy is None
            ):
                raise WebProductRuntimeError("web acceptance checks failed")
            source_project = materialize_next_project(
                spec,
                acceptance.design_strategy,
                self._artifact_root / "source-projects",
            )
            if not source_project.digest or not source_project.files:
                raise WebProductRuntimeError(
                    "generated Next.js source project is incomplete"
                )
            grants = cast(list[dict[str, object]], self._grants.state()["grants"])
            grant_proven = any(
                item["grant_id"] == grant_id and item["used_side_effects"] == 1
                for item in grants
            )
            if not grant_proven:
                raise WebProductRuntimeError("web execution grant proof is missing")
            source_sha = os.environ.get("ILAIOS_SOURCE_SHA", "UNBOUND")
            manifest: dict[str, object] = {
                "manifest_version": "1.3",
                "adapter_id": self.adapter_id,
                "request_id": request_id,
                "requester_id": row["principal_id"],
                "tenant_id": row["tenant_id"],
                "identity_proven": bool(row["principal_id"]) and bool(row["tenant_id"]),
                "goal_id": row["goal_id"],
                "job_id": job_id,
                "proposal_id": row["proposal_id"],
                "site_id": spec.site_id,
                "source_commit_sha": source_sha,
                "source_commit_bound": source_sha != "UNBOUND",
                "implementation_stack": "Next.js 16 / React 19 / TypeScript",
                "source_project_id": source_project.project_id,
                "source_project_path": source_project.root_path,
                "source_project_digest": source_project.digest,
                "source_project_files": [
                    {"path": item.relative_path, "sha256": item.sha256, "size": item.size}
                    for item in source_project.files
                ],
                "artifact_digest": acceptance.artifact_hash,
                "bundle_id": acceptance.bundle_id,
                "bundle_path": acceptance.bundle_path,
                "routes": acceptance.routes,
                "spec_hash": acceptance.spec_hash,
                "functional_features": spec.features,
                "design_strategy": acceptance.design_strategy,
                "qa": acceptance.qa,
                "grant_id": grant_id,
                "grant_proven": True,
                "risk": admission["risk"],
                "admission_decision": admission["admission_decision"],
                "human_approval_required": admission["human_approval_required"],
                "approval_proven": admission["approval_proven"],
                "admission_proven": admission["admission_proven"],
                "job_state_proven": False,
                "deployment_state": "NOT_DEPLOYED",
                "deployment_contract": "web.deployment-receipt.v1",
                "rollback_reference": acceptance.artifact_hash,
                "verification_scope": "LOCAL_FINISHED_ARTIFACT_AND_SOURCE_PROJECT",
                "finalization_status": "finalizing",
                "accepted": False,
            }
            serialized = json.dumps(manifest, sort_keys=True, separators=(",", ":"))
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                changed = connection.execute(
                    "UPDATE web_product_requests SET status='finalizing', manifest_json=? "
                    "WHERE request_id=? AND status='pending'",
                    (serialized, request_id),
                ).rowcount
            if changed != 1:
                raise WebProductRuntimeError(
                    "web product finalization state changed concurrently"
                )
            try:
                return self.recover_finalizing(request_id, token=token, now=now)
            except Exception as error:
                raise WebProductFinalizationPending(
                    "web product acceptance is durably finalizing and requires recovery"
                ) from error
        except WebProductFinalizationPending:
            raise
        except Exception as error:
            self._fail_web_product(row, token=token, now=now, error=error)
            raise

    def recover_finalizing(
        self,
        request_id: str,
        *,
        token: str,
        now: datetime,
    ) -> dict[str, object]:
        if now.tzinfo is None:
            raise WebProductRuntimeError("web finalization time must be timezone-aware")
        with self._connect() as connection:
            row = connection.execute(
                "SELECT status, job_id, manifest_json FROM web_product_requests "
                "WHERE request_id=?",
                (request_id,),
            ).fetchone()
        if row is None:
            raise WebProductRuntimeError("unknown web product request")
        if row["status"] == "accepted":
            return self.get_manifest(request_id)
        if row["status"] != "finalizing" or row["manifest_json"] is None:
            raise WebProductRuntimeError("web product is not finalizing")
        value = json.loads(str(row["manifest_json"]))
        if not isinstance(value, dict):
            raise WebProductRuntimeError("stored finalizing Web manifest is malformed")
        manifest = cast(dict[str, object], value)
        qa = manifest.get("qa")
        if not isinstance(qa, dict) or qa.get("passed") is not True:
            raise WebProductRuntimeError("stored Web QA evidence is incomplete")
        if not all(
            (
                manifest.get("adapter_id") == self.adapter_id,
                manifest.get("request_id") == request_id,
                manifest.get("job_id") == row["job_id"],
                manifest.get("identity_proven") is True,
                manifest.get("admission_proven") is True,
                manifest.get("grant_proven") is True,
                bool(manifest.get("artifact_digest")),
                bool(manifest.get("spec_hash")),
                bool(manifest.get("source_project_digest")),
                manifest.get("deployment_state") == "NOT_DEPLOYED",
                manifest.get("finalization_status") == "finalizing",
                manifest.get("accepted") is False,
            )
        ):
            raise WebProductRuntimeError(
                "stored finalizing Web acceptance evidence is incomplete"
            )
        job_id = str(row["job_id"])
        current = self._control_plane.get_job(token, job_id)
        if current.state is JobState.VALIDATING:
            current = self._control_plane.transition_job(
                token,
                job_id,
                JobState.COMPLETED,
                reason="durable Web finalization evidence verified",
                now=now,
            )
        if current.state is not JobState.COMPLETED:
            raise WebProductRuntimeError("finalizing Web job is not completable")
        manifest["job_state_proven"] = True
        manifest["finalization_status"] = "accepted"
        manifest["accepted"] = True
        serialized = json.dumps(manifest, sort_keys=True, separators=(",", ":"))
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            current_row = connection.execute(
                "SELECT status, manifest_json FROM web_product_requests WHERE request_id=?",
                (request_id,),
            ).fetchone()
            if current_row is None:
                raise WebProductRuntimeError("unknown web product request")
            if current_row["status"] == "accepted":
                stored = current_row["manifest_json"]
                if stored is None:
                    raise WebProductRuntimeError("accepted Web manifest is missing")
                result = json.loads(str(stored))
                if not isinstance(result, dict):
                    raise WebProductRuntimeError("stored Web manifest is malformed")
                return cast(dict[str, object], result)
            if current_row["status"] != "finalizing":
                raise WebProductRuntimeError(
                    "web product finalization state changed concurrently"
                )
            changed = connection.execute(
                "UPDATE web_product_requests SET status='accepted', manifest_json=? "
                "WHERE request_id=? AND status='finalizing'",
                (serialized, request_id),
            ).rowcount
            if changed != 1:
                raise WebProductRuntimeError(
                    "web product finalization state changed concurrently"
                )
            connection.execute(
                "INSERT OR IGNORE INTO web_product_closure VALUES "
                "(?, 'accepted', ?, ?)",
                (
                    request_id,
                    "website source, preview artifact and acceptance evidence verified",
                    now.isoformat(),
                ),
            )
        return manifest

    def get_manifest(self, request_id: str) -> dict[str, object]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT status, manifest_json FROM web_product_requests WHERE request_id=?",
                (request_id,),
            ).fetchone()
        if row is None or row["status"] != "accepted" or row["manifest_json"] is None:
            raise WebProductRuntimeError("accepted web product is unavailable")
        value = json.loads(str(row["manifest_json"]))
        if not isinstance(value, dict):
            raise WebProductRuntimeError("stored web AcceptanceManifest is malformed")
        return cast(dict[str, object], value)

    def get_state(self, request_id: str) -> dict[str, object]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT principal_id, tenant_id, status FROM web_product_requests "
                "WHERE request_id=?",
                (request_id,),
            ).fetchone()
            closure = connection.execute(
                "SELECT terminal_status, reason, terminal_at FROM web_product_closure "
                "WHERE request_id=?",
                (request_id,),
            ).fetchone()
        if row is None:
            raise WebProductRuntimeError("unknown web product request")
        return {
            "request_id": request_id,
            "requester_id": str(row["principal_id"]),
            "tenant_id": str(row["tenant_id"]),
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
        if now.tzinfo is None:
            raise WebProductRuntimeError("interruption time must be timezone-aware")
        normalized = " ".join(reason.split())
        if not normalized:
            raise WebProductRuntimeError("interruption reason is required")
        state = self.get_state(request_id)
        if state["status"] == "accepted":
            return state
        if state["status"] == "finalizing":
            self.recover_finalizing(request_id, token=token, now=now)
            return self.get_state(request_id)
        if state["status"] in {"failed", "interrupted", "cancelled"}:
            return state
        with self._connect() as connection:
            row = connection.execute(
                "SELECT job_id FROM web_product_requests WHERE request_id=?",
                (request_id,),
            ).fetchone()
        if row is None:
            raise WebProductRuntimeError("unknown web product request")
        current = self._control_plane.get_job(token, str(row["job_id"]))
        if current.state not in {JobState.COMPLETED, JobState.FAILED, JobState.CANCELLED}:
            self._control_plane.transition_job(
                token,
                str(row["job_id"]),
                JobState.CANCELLED,
                reason="finished web product execution interrupted",
                now=now,
            )
        with self._connect() as connection:
            changed = connection.execute(
                "UPDATE web_product_requests SET status='interrupted' "
                "WHERE request_id=? AND status='pending'",
                (request_id,),
            ).rowcount
            if changed == 1:
                connection.execute(
                    "INSERT OR IGNORE INTO web_product_closure VALUES "
                    "(?, 'interrupted', ?, ?)",
                    (request_id, normalized, now.isoformat()),
                )
        return self.get_state(request_id)

    def _pending(self, request_id: str) -> sqlite3.Row:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM web_product_requests WHERE request_id=?",
                (request_id,),
            ).fetchone()
        if row is None or row["status"] != "pending":
            raise WebProductRuntimeError("web product request is not pending")
        return cast(sqlite3.Row, row)

    def _fail_web_product(
        self,
        row: sqlite3.Row,
        *,
        token: str,
        now: datetime,
        error: Exception,
    ) -> None:
        request_id = str(row["request_id"])
        reason = _failure_reason(error)
        try:
            current = self._control_plane.get_job(token, str(row["job_id"]))
            if current.state is JobState.PENDING:
                self._control_plane.transition_job(
                    token,
                    str(row["job_id"]),
                    JobState.CANCELLED,
                    reason="web finished-product execution failed before start",
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
                    str(row["job_id"]),
                    JobState.FAILED,
                    reason="web finished-product execution failed closed",
                    now=now,
                )
        except Exception as cleanup_error:
            reason = f"{reason}; cleanup_failure={type(cleanup_error).__name__}"[:2048]
        with self._connect() as connection:
            connection.execute(
                "UPDATE web_product_requests SET status='failed' "
                "WHERE request_id=? AND status='pending'",
                (request_id,),
            )
            connection.execute(
                "INSERT OR IGNORE INTO web_product_closure VALUES "
                "(?, 'failed', ?, ?)",
                (request_id, reason, now.isoformat()),
            )


def _failure_reason(error: Exception) -> str:
    message = " ".join(str(error).split())
    if not message:
        message = "web execution failed without an error message"
    return f"{type(error).__name__}: {message}"[:2048]
