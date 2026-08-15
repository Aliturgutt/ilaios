"""Durable one-prompt Web Factory finished-product adapter."""

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

from .web_factory import GovernedWebFactory, WebsiteSpec, derive_website_spec
from .web_project import materialize_next_project
from .web_repair import BoundedWebRepairPolicy, WebRepairAttempt, WebRepairError

_VERIFIED_LOCAL_FEATURES = frozenset({"contact-form"})


class WebProductRuntimeError(RuntimeError):
    """Raised when the finished website cannot pass its bounded acceptance contract."""


class DurableWebProductRuntime:
    """Compose canonical governance, grants, Web Factory, and delivery evidence."""

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
        self._repair = BoundedWebRepairPolicy()
        database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS web_product_requests ("
                "request_id TEXT PRIMARY KEY, goal_id TEXT NOT NULL, "
                "job_id TEXT NOT NULL, proposal_id TEXT NOT NULL, "
                "principal_id TEXT NOT NULL, tenant_id TEXT NOT NULL, "
                "spec_json TEXT NOT NULL, status TEXT NOT NULL, "
                "manifest_json TEXT)"
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
    ) -> dict[str, object]:
        if now.tzinfo is None:
            raise WebProductRuntimeError("web execution time must be timezone-aware")
        spec = derive_website_spec(request_id, objective)
        unsupported_features = tuple(
            sorted(set(spec.features).difference(_VERIFIED_LOCAL_FEATURES))
        )
        if unsupported_features:
            raise WebProductRuntimeError(
                "requested web functionality has no verified finished-product adapter: "
                + ", ".join(unsupported_features)
            )

        goal = self._control_plane.create_goal(token, objective)
        job = self._control_plane.create_job(token, goal.goal_id)
        proposal = self._control_plane.create_proposal(
            token,
            goal.goal_id,
            acceptance_criteria=(
                "Structured WebsiteSpec and context-derived design strategy exist",
                "ILAIOS-owned Next.js/React/TypeScript source project is content addressed",
                "Rendered preview bundle passes bounded quality gates",
                "Bounded repair evidence is retained when a deterministic repair occurs",
                "Acceptance manifest binds request, tenant, source, and artifact evidence",
            ),
            risk_class=RiskClass.MEDIUM,
            data_class=DataClass.INTERNAL,
            budget=BudgetEnvelope(1, 60, 0),
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
                "objective": objective,
                "tenant_id": tenant_id,
                "site_id": spec.site_id,
            },
            (),
            risk="medium",
        )
        if (
            admission.get("admission_decision") != "ALLOW"
            or admission.get("human_approval_required") is not False
        ):
            raise WebProductRuntimeError("medium web admission did not fail closed")
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
                        json.dumps(
                            spec.to_dict(), sort_keys=True, separators=(",", ":")
                        ),
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
            "risk": "medium",
            "admission_decision": "ALLOW",
            "status": "admitted_pending_grant",
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
                raise WebProductRuntimeError("governed web execution admission is not proven")
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
            acceptance, spec, repair_attempts = self._build_with_bounded_repair(
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
                raise WebProductRuntimeError("generated Next.js source project is incomplete")

            grant_rows = cast(list[dict[str, object]], self._grants.state()["grants"])
            grant_proven = any(
                grant["grant_id"] == grant_id and grant["used_side_effects"] == 1
                for grant in grant_rows
            )
            completed_job = self._control_plane.transition_job(
                token,
                job_id,
                JobState.COMPLETED,
                reason="website source, preview artifact and acceptance evidence verified",
                now=now,
            )
            if not all(
                (
                    grant_proven,
                    completed_job.state is JobState.COMPLETED,
                    acceptance.accepted,
                    bool(acceptance.artifact_hash),
                    bool(acceptance.spec_hash),
                    bool(source_project.digest),
                )
            ):
                raise WebProductRuntimeError("durable web AcceptanceManifest checks failed")

            source_sha = os.environ.get("ILAIOS_SOURCE_SHA", "UNBOUND")
            manifest: dict[str, object] = {
                "manifest_version": "1.2",
                "adapter_id": self.adapter_id,
                "request_id": request_id,
                "requester_id": row["principal_id"],
                "tenant_id": row["tenant_id"],
                "identity_proven": bool(row["principal_id"])
                and bool(row["tenant_id"]),
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
                    {
                        "path": item.relative_path,
                        "sha256": item.sha256,
                        "size": item.size,
                    }
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
                "repair_policy": {
                    "max_attempts": self._repair.max_attempts,
                    "attempts_used": len(repair_attempts),
                },
                "repair_attempts": [
                    attempt.to_dict() for attempt in repair_attempts
                ],
                "grant_id": grant_id,
                "grant_proven": grant_proven,
                "risk": admission["risk"],
                "admission_decision": admission["admission_decision"],
                "human_approval_required": admission["human_approval_required"],
                "approval_proven": admission["approval_proven"],
                "admission_proven": admission["admission_proven"],
                "deployment_state": "NOT_DEPLOYED",
                "deployment_contract": "web.deployment-receipt.v1",
                "rollback_reference": acceptance.artifact_hash,
                "verification_scope": "LOCAL_FINISHED_ARTIFACT_AND_SOURCE_PROJECT",
                "accepted": True,
            }
            with self._connect() as connection:
                changed = connection.execute(
                    "UPDATE web_product_requests SET status = 'accepted', "
                    "manifest_json = ? WHERE request_id = ? AND status = 'pending'",
                    (json.dumps(manifest, sort_keys=True), request_id),
                ).rowcount
                if changed != 1:
                    raise WebProductRuntimeError(
                        "web product state changed during closure"
                    )
                connection.execute(
                    "INSERT INTO web_product_closure VALUES (?, 'accepted', ?, ?)",
                    (
                        request_id,
                        "website source, preview artifact and acceptance evidence verified",
                        now.isoformat(),
                    ),
                )
            return manifest
        except Exception as error:
            self._fail_web_product(row, token=token, now=now, error=error)
            raise

    def _build_with_bounded_repair(
        self,
        spec: WebsiteSpec,
        *,
        grant: ExecutionGrant,
        now: datetime,
    ) -> tuple[object, WebsiteSpec, tuple[WebRepairAttempt, ...]]:
        attempts: list[WebRepairAttempt] = []
        try:
            acceptance = self._factory.build_generated_site(
                spec,
                grant=grant,
                now=now,
            )
            return acceptance, spec, tuple(attempts)
        except ValueError as error:
            try:
                repaired, attempt = self._repair.repair_spec(
                    spec,
                    error,
                    prior_attempts=len(attempts),
                )
            except WebRepairError as repair_error:
                raise WebProductRuntimeError(str(repair_error)) from error
            attempts.append(attempt)
            acceptance = self._factory.build_generated_site(
                repaired,
                grant=grant,
                now=now,
            )
            return acceptance, repaired, tuple(attempts)

    def get_manifest(self, request_id: str) -> dict[str, object]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT status, manifest_json FROM web_product_requests "
                "WHERE request_id = ?",
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
                "WHERE request_id = ?",
                (request_id,),
            ).fetchone()
            closure = connection.execute(
                "SELECT terminal_status, reason, terminal_at FROM web_product_closure "
                "WHERE request_id = ?",
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
            "terminal_status": None
            if closure is None
            else str(closure["terminal_status"]),
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
        if not reason or reason != reason.strip():
            raise WebProductRuntimeError(
                "interruption reason must be non-blank and trimmed"
            )
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM web_product_requests WHERE request_id = ?", (request_id,)
            ).fetchone()
        if row is None:
            raise WebProductRuntimeError("unknown web product request")
        if row["status"] != "pending":
            return self.get_state(request_id)
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
                "UPDATE web_product_requests SET status = 'interrupted' "
                "WHERE request_id = ? AND status = 'pending'",
                (request_id,),
            ).rowcount
            if changed == 1:
                connection.execute(
                    "INSERT OR IGNORE INTO web_product_closure VALUES "
                    "(?, 'interrupted', ?, ?)",
                    (request_id, reason, now.isoformat()),
                )
        return self.get_state(request_id)

    def _pending(self, request_id: str) -> sqlite3.Row:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM web_product_requests WHERE request_id = ?",
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
            reason = (
                f"{reason}; cleanup_failure={type(cleanup_error).__name__}"
            )[:2048]
        with self._connect() as connection:
            connection.execute(
                "UPDATE web_product_requests SET status = 'failed' "
                "WHERE request_id = ? AND status = 'pending'",
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
