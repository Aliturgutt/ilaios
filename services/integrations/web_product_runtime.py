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
        self._factory = GovernedWebFactory(GrantPolicy(), artifact_root)
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
        goal = self._control_plane.create_goal(token, objective)
        job = self._control_plane.create_job(token, goal.goal_id)
        proposal = self._control_plane.create_proposal(
            token,
            goal.goal_id,
            acceptance_criteria=(
                "Structured WebsiteSpec and context-derived design strategy exist",
                "Content-addressed website bundle passes bounded quality gates",
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
                        json.dumps(spec.to_dict(), sort_keys=True, separators=(",", ":")),
                    ),
                )
            except sqlite3.IntegrityError as error:
                raise WebProductRuntimeError("web product request already exists") from error
        return {
            "request_id": request_id,
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
        admission = self._governance.admission_snapshot(request_id)
        if admission["admission_proven"] is not True:
            raise WebProductRuntimeError("governed web execution admission is not proven")
        job_id = str(row["job_id"])
        spec_value = json.loads(str(row["spec_json"]))
        if not isinstance(spec_value, dict):
            raise WebProductRuntimeError("stored WebsiteSpec is malformed")
        spec = WebsiteSpec.from_dict(cast(dict[str, object], spec_value))
        self._control_plane.transition_job(
            token,
            job_id,
            JobState.RUNNING,
            reason="governed web finished-product build started",
            now=now,
        )
        try:
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
            acceptance = self._factory.build_generated_site(
                spec,
                grant=local_grant,
                now=now,
            )
        except Exception:
            self._mark_failed(request_id)
            self._control_plane.transition_job(
                token,
                job_id,
                JobState.FAILED,
                reason="governed web finished-product build failed",
                now=now,
            )
            raise

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
        ):
            self._mark_failed(request_id)
            raise WebProductRuntimeError("web acceptance checks failed")
        grant_state = self._grants.state()
        grant_rows = cast(list[dict[str, object]], grant_state["grants"])
        grant_proven = any(
            grant["grant_id"] == grant_id and grant["used_side_effects"] == 1
            for grant in grant_rows
        )
        completed_job = self._control_plane.transition_job(
            token,
            job_id,
            JobState.COMPLETED,
            reason="website artifact and acceptance evidence verified",
            now=now,
        )
        accepted = bool(
            grant_proven
            and completed_job.state is JobState.COMPLETED
            and acceptance.accepted
            and acceptance.artifact_hash
            and acceptance.spec_hash
        )
        if not accepted:
            self._mark_failed(request_id)
            raise WebProductRuntimeError("durable web AcceptanceManifest checks failed")
        manifest: dict[str, object] = {
            "manifest_version": "1.0",
            "adapter_id": self.adapter_id,
            "request_id": request_id,
            "goal_id": row["goal_id"],
            "job_id": job_id,
            "proposal_id": row["proposal_id"],
            "principal_id": row["principal_id"],
            "tenant_id": row["tenant_id"],
            "site_id": spec.site_id,
            "source_commit_sha": os.environ.get("ILAIOS_SOURCE_SHA", "UNBOUND"),
            "artifact_digest": acceptance.artifact_hash,
            "bundle_id": acceptance.bundle_id,
            "bundle_path": acceptance.bundle_path,
            "routes": acceptance.routes,
            "spec_hash": acceptance.spec_hash,
            "design_strategy": acceptance.design_strategy,
            "qa": acceptance.qa,
            "grant_id": grant_id,
            "grant_proven": grant_proven,
            "risk": admission["risk"],
            "admission_decision": admission["admission_decision"],
            "human_approval_required": admission["human_approval_required"],
            "approval_proven": admission["approval_proven"],
            "admission_proven": admission["admission_proven"],
            "deployment_state": "NOT_DEPLOYED",
            "rollback_reference": acceptance.artifact_hash,
            "verification_scope": "LOCAL_FINISHED_ARTIFACT",
            "accepted": True,
        }
        with self._connect() as connection:
            connection.execute(
                "UPDATE web_product_requests SET status = 'accepted', manifest_json = ? "
                "WHERE request_id = ?",
                (json.dumps(manifest, sort_keys=True), request_id),
            )
        return manifest

    def get_manifest(self, request_id: str) -> dict[str, object]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT status, manifest_json FROM web_product_requests WHERE request_id = ?",
                (request_id,),
            ).fetchone()
        if row is None or row["status"] != "accepted" or row["manifest_json"] is None:
            raise WebProductRuntimeError("accepted web product is unavailable")
        value = json.loads(str(row["manifest_json"]))
        if not isinstance(value, dict):
            raise WebProductRuntimeError("stored web AcceptanceManifest is malformed")
        return cast(dict[str, object], value)

    def _pending(self, request_id: str) -> sqlite3.Row:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM web_product_requests WHERE request_id = ?",
                (request_id,),
            ).fetchone()
        if row is None or row["status"] != "pending":
            raise WebProductRuntimeError("web product request is not pending")
        return cast(sqlite3.Row, row)

    def _mark_failed(self, request_id: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "UPDATE web_product_requests SET status = 'failed' "
                "WHERE request_id = ? AND status = 'pending'",
                (request_id,),
            )
