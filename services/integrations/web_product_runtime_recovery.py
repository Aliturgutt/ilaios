"""Recovery-safe terminal semantics and final source assurance for Web runtime."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import cast

from services.control_plane import BudgetEnvelope, DataClass, ProposedTask, RiskClass
from src.video_automation.models import JobState

from .web_assurance import WebAssuranceError, certify_with_bounded_repair
from .web_factory import derive_website_spec
from .web_product_runtime import DurableWebProductRuntime, WebProductRuntimeError

_VERIFIED_BOUNDED_FEATURES = frozenset(
    {"contact-form", "content", "newsletter", "search"}
)


class RecoverableWebProductRuntime(DurableWebProductRuntime):
    """Crash-safe Web runtime with bounded feature and assurance promotion.

    The class keeps the canonical ``web.product-runtime.v1`` adapter identity. It
    extends preparation in place for first-party bounded modules and certifies the
    generated Next.js source before the inherited durable finalization can mark the
    authoritative job completed.
    """

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
        budget: BudgetEnvelope = BudgetEnvelope(2, 120, 0),
    ) -> dict[str, object]:
        if now.tzinfo is None:
            raise WebProductRuntimeError("web execution time must be timezone-aware")
        spec = derive_website_spec(request_id, objective)
        unsupported = tuple(
            sorted(set(spec.features).difference(_VERIFIED_BOUNDED_FEATURES))
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
                "Bounded source assurance and repair pass before finalization",
                "Accessibility, SEO, security, performance and design receipts exist",
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
                ProposedTask(
                    "web-certify",
                    "Certify and bounded-repair deployable Web source",
                    ("web-validate",),
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
                "bounded_features": list(spec.features),
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
            "risk": risk,
            "data_class": data_class.value,
            "budget": {
                "max_attempts": budget.max_attempts,
                "max_runtime_seconds": budget.max_runtime_seconds,
                "max_external_spend_minor": budget.max_external_spend_minor,
            },
            "functional_features": spec.features,
            "admission_decision": decision,
            "human_approval_required": human,
            "status": "pending_approval" if human else "admitted_pending_grant",
        }

    def _assert_accepted_assurance(
        self,
        request_id: str,
        manifest: dict[str, object],
    ) -> None:
        assurance = manifest.get("source_assurance")
        qa = manifest.get("qa")
        build_result = manifest.get("build_result")
        receipt_names = (
            "design_acceptance",
            "accessibility_evidence",
            "seo_evidence",
            "security_evidence",
            "performance_evidence",
        )
        receipts_pass = all(
            isinstance(manifest.get(name), dict)
            and cast(dict[str, object], manifest[name]).get("status") == "PASS"
            for name in receipt_names
        )
        if not all(
            (
                manifest.get("adapter_id") == self.adapter_id,
                manifest.get("request_id") == request_id,
                bool(manifest.get("job_id")),
                manifest.get("accepted") is True,
                manifest.get("finalization_status") == "accepted",
                manifest.get("job_state_proven") is True,
                isinstance(assurance, dict),
                isinstance(assurance, dict) and assurance.get("passed") is True,
                isinstance(qa, dict),
                isinstance(qa, dict) and qa.get("source_assurance_passed") is True,
                isinstance(build_result, dict),
                isinstance(build_result, dict)
                and build_result.get("status") == "SOURCE_CERTIFIED",
                bool(manifest.get("source_project_path")),
                bool(manifest.get("source_project_digest")),
                bool(manifest.get("source_project_files")),
                bool(manifest.get("certified_routes")),
                receipts_pass,
            )
        ):
            raise WebProductRuntimeError(
                "accepted Web assurance evidence is incomplete"
            )

    def get_manifest(self, request_id: str) -> dict[str, object]:
        manifest = super().get_manifest(request_id)
        self._assert_accepted_assurance(request_id, manifest)
        return manifest

    def get_state(self, request_id: str) -> dict[str, object]:
        state = super().get_state(request_id)
        if state["status"] == "accepted":
            self.get_manifest(request_id)
        return state

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
            return super().recover_finalizing(request_id, token=token, now=now)

        value = json.loads(str(row["manifest_json"]))
        if not isinstance(value, dict):
            raise WebProductRuntimeError("stored finalizing Web manifest is malformed")
        manifest = cast(dict[str, object], value)
        assurance_value = manifest.get("source_assurance")
        assurance_passed = (
            isinstance(assurance_value, dict)
            and assurance_value.get("passed") is True
        )
        if not assurance_passed:
            project_value = manifest.get("source_project_path")
            if not isinstance(project_value, str) or not project_value:
                raise WebProductRuntimeError(
                    "generated Web source path is missing before assurance"
                )
            try:
                assurance = certify_with_bounded_repair(
                    Path(project_value),
                    max_attempts=2,
                )
            except WebAssuranceError as error:
                self._fail_assurance(
                    request_id,
                    row_job_id=str(row["job_id"]),
                    manifest=manifest,
                    token=token,
                    now=now,
                    error=error,
                )
                raise WebProductRuntimeError(
                    "bounded Web source assurance exhausted without acceptance"
                ) from error

            manifest["source_project_original_digest"] = manifest.get(
                "source_project_digest"
            )
            manifest["source_project_path"] = assurance["certified_project_path"]
            manifest["source_project_digest"] = assurance["source_project_digest"]
            manifest["source_project_files"] = assurance["source_project_files"]
            manifest["certified_routes"] = assurance["certified_routes"]
            manifest["functional_features"] = assurance["functional_features"]
            manifest["source_assurance"] = assurance
            manifest["repair_attempts"] = assurance["repair_attempts"]
            manifest["design_acceptance"] = assurance["design"]
            manifest["accessibility_evidence"] = assurance["accessibility"]
            manifest["seo_evidence"] = assurance["seo"]
            manifest["security_evidence"] = assurance["security"]
            manifest["performance_evidence"] = assurance["performance"]
            manifest["build_result"] = {
                "status": "SOURCE_CERTIFIED",
                "production_build_required": True,
            }
            manifest["verification_scope"] = (
                "LOCAL_CERTIFIED_SOURCE_AND_PREVIEW_BROWSER_BUILD_REQUIRED"
            )
            qa = manifest.get("qa")
            if isinstance(qa, dict):
                qa = dict(qa)
                qa["source_assurance_passed"] = True
                qa["repair_attempt_count"] = assurance["repair_attempt_count"]
                manifest["qa"] = qa
            serialized = json.dumps(
                manifest, sort_keys=True, separators=(",", ":")
            )
            with self._connect() as connection:
                changed = connection.execute(
                    "UPDATE web_product_requests SET manifest_json=? "
                    "WHERE request_id=? AND status='finalizing'",
                    (serialized, request_id),
                ).rowcount
            if changed != 1:
                raise WebProductRuntimeError(
                    "Web assurance evidence could not be bound to finalization"
                )

        result = super().recover_finalizing(request_id, token=token, now=now)
        self._assert_accepted_assurance(request_id, result)
        return result

    def _fail_assurance(
        self,
        request_id: str,
        *,
        row_job_id: str,
        manifest: dict[str, object],
        token: str,
        now: datetime,
        error: Exception,
    ) -> None:
        manifest["source_assurance"] = {
            "schema": "ilaios.web.source-assurance.v1",
            "passed": False,
            "failure": type(error).__name__,
            "message": str(error),
        }
        manifest["accepted"] = False
        manifest["finalization_status"] = "failed"
        serialized = json.dumps(manifest, sort_keys=True, separators=(",", ":"))
        current = self._control_plane.get_job(token, row_job_id)
        if current.state is JobState.VALIDATING:
            self._control_plane.transition_job(
                token,
                row_job_id,
                JobState.FAILED,
                reason="bounded Web source assurance failed closed",
                now=now,
            )
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            changed = connection.execute(
                "UPDATE web_product_requests SET status='failed', manifest_json=? "
                "WHERE request_id=? AND status='finalizing'",
                (serialized, request_id),
            ).rowcount
            if changed == 1:
                connection.execute(
                    "INSERT OR IGNORE INTO web_product_closure VALUES "
                    "(?, 'failed', ?, ?)",
                    (request_id, "bounded source assurance failed", now.isoformat()),
                )

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
        terminal_status = (
            "cancelled"
            if normalized == "cancelled by authenticated execution owner"
            else "interrupted"
        )
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
                reason=f"finished web product execution {terminal_status}",
                now=now,
            )
        with self._connect() as connection:
            changed = connection.execute(
                "UPDATE web_product_requests SET status=? "
                "WHERE request_id=? AND status='pending'",
                (terminal_status, request_id),
            ).rowcount
            if changed == 1:
                connection.execute(
                    "INSERT OR IGNORE INTO web_product_closure VALUES "
                    "(?, ?, ?, ?)",
                    (request_id, terminal_status, normalized, now.isoformat()),
                )
        if changed != 1:
            latest = self.get_state(request_id)
            if latest["status"] in {"accepted", "failed", "interrupted", "cancelled"}:
                return latest
            raise WebProductRuntimeError("web interruption state was lost")
        return self.get_state(request_id)


__all__ = ["RecoverableWebProductRuntime"]
