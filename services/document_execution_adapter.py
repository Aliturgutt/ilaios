"""Canonical ExecutionCoordinator adapter for governed PDF/DOCX document outputs."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

from services.control_plane import BudgetEnvelope, DataClass
from services.control_plane.api import ControlPlane
from services.control_plane.proposals import ProposedTask, RiskClass
from services.execution_adapters import register_verified_adapter
from services.execution_coordinator import (
    AdapterDescriptor,
    CapabilityMaturity,
    ExecutionCoordinator,
    ExecutionCoordinatorError,
)
from services.governance import GovernedRuntimeGateway
from services.integrations.document_product_runtime import (
    CAPABILITY_ID,
    DocumentProductRuntime,
)


class DocumentExecutionAdapter:
    """Durable coordinator adapter over the bounded DocumentProductRuntime."""

    descriptor = AdapterDescriptor(
        "document.product-runtime.pdf-docx.v1",
        CAPABILITY_ID,
        CapabilityMaturity.VERIFIED_FINISHED_PRODUCT_ADAPTER,
        worker_subject="worker-document",
        action="document.create",
        supports_cancellation=False,
    )

    def __init__(
        self,
        database_path: Path,
        control_plane: ControlPlane,
        governance: GovernedRuntimeGateway,
        runtime: DocumentProductRuntime,
    ) -> None:
        self._database_path = database_path
        self._control_plane = control_plane
        self._governance = governance
        self._runtime = runtime
        database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS document_execution_requests ("
                "request_id TEXT PRIMARY KEY, principal_id TEXT NOT NULL, "
                "tenant_id TEXT NOT NULL, objective TEXT NOT NULL, "
                "goal_id TEXT NOT NULL, job_id TEXT NOT NULL, proposal_id TEXT NOT NULL, "
                "status TEXT NOT NULL, manifest_json TEXT)"
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
        principal_id: str,
        tenant_id: str,
        now: datetime,
        risk: str,
        data_class: DataClass,
        budget: BudgetEnvelope,
    ) -> dict[str, object]:
        if now.tzinfo is None:
            raise ExecutionCoordinatorError("document execution time must be timezone-aware")
        if risk != "medium" or data_class is not DataClass.INTERNAL:
            raise ExecutionCoordinatorError(
                "verified Document adapter does not widen risk or data policy"
            )
        if budget.max_attempts < 1 or budget.max_runtime_seconds < 1:
            raise ExecutionCoordinatorError("document execution budget is invalid")
        goal = self._control_plane.create_goal(token, objective)
        job = self._control_plane.create_job(token, goal.goal_id)
        proposal = self._control_plane.create_proposal(
            token,
            goal.goal_id,
            acceptance_criteria=(
                "PDF and DOCX outputs are persisted through governed Files/Outputs",
                "Artifact metadata remains tenant and execution scoped",
                "Execution evidence remains bound to the canonical coordinator request",
            ),
            risk_class=RiskClass(risk),
            data_class=data_class,
            budget=budget,
            tasks=(
                ProposedTask("document-render", "Render governed PDF and DOCX outputs"),
            ),
        )
        admission = self._governance.submit(
            request_id,
            principal_id,
            "document-agent",
            "document-finished-product-pdf-docx-v1",
            "document",
            {
                "goal_id": goal.goal_id,
                "job_id": job.job_id,
                "tenant_id": tenant_id,
                "formats": ["pdf", "docx"],
            },
            (),
            risk=risk,
        )
        decision = str(admission.get("admission_decision", ""))
        human = bool(admission.get("human_approval_required", False))
        if decision not in {"ALLOW", "REQUIRE_APPROVAL"}:
            raise ExecutionCoordinatorError("document admission was denied or malformed")
        if (decision == "ALLOW" and human) or (
            decision == "REQUIRE_APPROVAL" and not human
        ):
            raise ExecutionCoordinatorError("document admission approval state is inconsistent")
        proposal_id = str(proposal["proposal_id"])
        with self._connect() as connection:
            try:
                connection.execute(
                    "INSERT INTO document_execution_requests VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL)",
                    (
                        request_id,
                        principal_id,
                        tenant_id,
                        objective,
                        goal.goal_id,
                        job.job_id,
                        proposal_id,
                        "pending",
                    ),
                )
            except sqlite3.IntegrityError as error:
                raise ExecutionCoordinatorError("document execution request already exists") from error
        return {
            "request_id": request_id,
            "goal_id": goal.goal_id,
            "job_id": job.job_id,
            "proposal_id": proposal_id,
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
        del token
        if now.tzinfo is None:
            raise ExecutionCoordinatorError("document execution time must be timezone-aware")
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM document_execution_requests WHERE request_id = ?",
                (request_id,),
            ).fetchone()
        if row is None:
            raise ExecutionCoordinatorError("document execution request not found")
        if str(row["status"]) == "accepted" and row["manifest_json"] is not None:
            return json.loads(str(row["manifest_json"]))
        objective = str(row["objective"])
        title = objective.strip().splitlines()[0][:120]
        manifest = self._runtime.create(
            artifact_id=request_id,
            version_id="v1",
            tenant_id=str(row["tenant_id"]),
            project_id=f"execution/{request_id}",
            job_id=str(row["job_id"]),
            title=title,
            body=objective,
        )
        result: dict[str, object] = {
            **manifest,
            "accepted": True,
            "final_disposition": "ACCEPT",
            "adapter_id": self.descriptor.adapter_id,
            "request_id": request_id,
            "tenant_id": str(row["tenant_id"]),
            "project_id": f"execution/{request_id}",
            "job_id": str(row["job_id"]),
            "grant_id": grant_id,
            "evidence_scope": "GOVERNED_PDF_DOCX_FILES_OUTPUTS",
        }
        serialized = json.dumps(result, sort_keys=True, separators=(",", ":"))
        with self._connect() as connection:
            connection.execute(
                "UPDATE document_execution_requests SET status = 'accepted', manifest_json = ? "
                "WHERE request_id = ?",
                (serialized, request_id),
            )
        return result

    def accepted_result(self, request_id: str) -> dict[str, object]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT manifest_json FROM document_execution_requests WHERE request_id = ?",
                (request_id,),
            ).fetchone()
        if row is None or row["manifest_json"] is None:
            raise ExecutionCoordinatorError("document execution is not accepted")
        return json.loads(str(row["manifest_json"]))

    def state(self, request_id: str) -> dict[str, object]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT status FROM document_execution_requests WHERE request_id = ?",
                (request_id,),
            ).fetchone()
        if row is None:
            raise ExecutionCoordinatorError("document execution request not found")
        return {"request_id": request_id, "status": str(row["status"])}

    def recover_finalizing(
        self,
        request_id: str,
        *,
        token: str,
        now: datetime,
    ) -> dict[str, object]:
        del token, now
        return self.accepted_result(request_id)

    def interrupt(
        self,
        request_id: str,
        *,
        token: str,
        now: datetime,
        reason: str,
    ) -> dict[str, object]:
        del token, now, reason
        return self.state(request_id)


def register_document_runtime(
    coordinator: ExecutionCoordinator,
    *,
    database_path: Path,
    control_plane: ControlPlane,
    governance: GovernedRuntimeGateway,
    runtime: DocumentProductRuntime,
) -> None:
    """Register the bounded Document runtime into the one canonical coordinator."""
    register_verified_adapter(
        coordinator,
        DocumentExecutionAdapter(database_path, control_plane, governance, runtime),
    )


__all__ = ["DocumentExecutionAdapter", "register_document_runtime"]
