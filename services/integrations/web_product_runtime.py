"""Crash-recoverable Web finished-product runtime.

The implementation extends the previously reviewed Web runtime without creating a
second execution authority.  The critical difference is the cross-store closure
order: verified acceptance evidence is durably persisted as ``finalizing`` before
the authoritative Control Plane job may become ``COMPLETED``.  Recovery then
reconciles that state idempotently, mirroring the canonical Video product saga.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from typing import cast

from services.runtime import BlastRadiusBudget, ExecutionGrant
from src.video_automation.models import JobState

from .product_runtime import ProductFinalizationPending
from .web_factory import WebsiteSpec
from .web_product_runtime_legacy import (
    DurableWebProductRuntime as _LegacyDurableWebProductRuntime,
    WebProductRuntimeError,
)
from .web_project import materialize_next_project


class WebProductFinalizationPending(ProductFinalizationPending):
    """Durable Web acceptance is finalizing and must be reconciled, not failed."""


class DurableWebProductRuntime(_LegacyDurableWebProductRuntime):
    """Web runtime with a crash-safe, idempotent cross-store acceptance saga."""

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
            acceptance, repaired_spec, repair_attempts = self._build_with_bounded_repair(
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
                repaired_spec,
                acceptance.design_strategy,
                self._artifact_root / "source-projects",
            )
            if not source_project.digest or not source_project.files:
                raise WebProductRuntimeError(
                    "generated Next.js source project is incomplete"
                )

            grant_rows = cast(
                list[dict[str, object]], self._grants.state()["grants"]
            )
            grant_proven = any(
                grant["grant_id"] == grant_id and grant["used_side_effects"] == 1
                for grant in grant_rows
            )
            validating_job = self._control_plane.get_job(token, job_id)
            if not all(
                (
                    grant_proven,
                    validating_job.state is JobState.VALIDATING,
                    acceptance.accepted,
                    bool(acceptance.artifact_hash),
                    bool(acceptance.spec_hash),
                    bool(source_project.digest),
                )
            ):
                raise WebProductRuntimeError(
                    "durable web AcceptanceManifest checks failed"
                )

            source_sha = os.environ.get("ILAIOS_SOURCE_SHA", "UNBOUND")
            manifest: dict[str, object] = {
                "manifest_version": "1.3",
                "adapter_id": self.adapter_id,
                "request_id": request_id,
                "requester_id": row["principal_id"],
                "tenant_id": row["tenant_id"],
                "identity_proven": bool(row["principal_id"])
                and bool(row["tenant_id"]),
                "goal_id": row["goal_id"],
                "job_id": job_id,
                "proposal_id": row["proposal_id"],
                "site_id": repaired_spec.site_id,
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
                "functional_features": repaired_spec.features,
                "design_strategy": acceptance.design_strategy,
                "qa": acceptance.qa,
                "repair_policy": {
                    "max_attempts": self._repair.max_attempts,
                    "attempts_used": len(repair_attempts),
                },
                "repair_attempts": [attempt.to_dict() for attempt in repair_attempts],
                "grant_id": grant_id,
                "grant_proven": grant_proven,
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
            serialized = json.dumps(manifest, sort_keys=True)
            repaired_spec_json = json.dumps(
                repaired_spec.to_dict(), sort_keys=True, separators=(",", ":")
            )
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                changed = connection.execute(
                    "UPDATE web_product_requests SET status = 'finalizing', "
                    "spec_json = ?, manifest_json = ? "
                    "WHERE request_id = ? AND status = 'pending'",
                    (repaired_spec_json, serialized, request_id),
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
        """Idempotently reconcile Web acceptance after a crash boundary."""
        if now.tzinfo is None:
            raise WebProductRuntimeError("web finalization time must be timezone-aware")
        with self._connect() as connection:
            row = connection.execute(
                "SELECT status, job_id, manifest_json FROM web_product_requests "
                "WHERE request_id = ?",
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
            raise WebProductRuntimeError(
                "stored finalizing Web AcceptanceManifest is malformed"
            )
        manifest = cast(dict[str, object], value)
        qa = manifest.get("qa")
        if not isinstance(qa, dict):
            raise WebProductRuntimeError("stored finalizing Web QA evidence is malformed")
        if not all(
            (
                manifest.get("adapter_id") == self.adapter_id,
                manifest.get("request_id") == request_id,
                manifest.get("job_id") == row["job_id"],
                manifest.get("identity_proven") is True,
                manifest.get("admission_proven") is True,
                manifest.get("grant_proven") is True,
                qa.get("passed") is True,
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
            try:
                current = self._control_plane.transition_job(
                    token,
                    job_id,
                    JobState.COMPLETED,
                    reason="durable Web product finalization evidence verified",
                    now=now,
                )
            except Exception as error:
                current = self._control_plane.get_job(token, job_id)
                if current.state is not JobState.COMPLETED:
                    raise WebProductRuntimeError(
                        "Web job completion could not be reconciled"
                    ) from error
        if current.state is not JobState.COMPLETED:
            raise WebProductRuntimeError(
                "finalizing Web product job is not completable"
            )

        manifest["job_state_proven"] = True
        manifest["finalization_status"] = "accepted"
        manifest["accepted"] = True
        serialized = json.dumps(manifest, sort_keys=True)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            current_row = connection.execute(
                "SELECT status, manifest_json FROM web_product_requests "
                "WHERE request_id = ?",
                (request_id,),
            ).fetchone()
            if current_row is None:
                raise WebProductRuntimeError("unknown web product request")
            if current_row["status"] == "accepted":
                stored = current_row["manifest_json"]
                if stored is None:
                    raise WebProductRuntimeError(
                        "accepted Web product manifest is missing"
                    )
                accepted_value = json.loads(str(stored))
                if not isinstance(accepted_value, dict):
                    raise WebProductRuntimeError(
                        "stored Web AcceptanceManifest is malformed"
                    )
                return cast(dict[str, object], accepted_value)
            if current_row["status"] != "finalizing":
                raise WebProductRuntimeError(
                    "Web product finalization state changed concurrently"
                )
            changed = connection.execute(
                "UPDATE web_product_requests SET status = 'accepted', manifest_json = ? "
                "WHERE request_id = ? AND status = 'finalizing'",
                (serialized, request_id),
            ).rowcount
            if changed != 1:
                raise WebProductRuntimeError(
                    "Web product finalization state changed concurrently"
                )
            connection.execute(
                "INSERT OR IGNORE INTO web_product_closure VALUES "
                "(?, 'accepted', ?, ?)",
                (
                    request_id,
                    "website source, preview artifact and cross-store acceptance evidence verified",
                    now.isoformat(),
                ),
            )
        return manifest

    def interrupt(
        self,
        request_id: str,
        *,
        token: str,
        now: datetime,
        reason: str,
    ) -> dict[str, object]:
        """Never let cancellation/interruption overwrite durable finalization evidence."""
        state = self.get_state(request_id)
        if state["status"] == "finalizing":
            self.recover_finalizing(request_id, token=token, now=now)
            return self.get_state(request_id)
        return super().interrupt(
            request_id,
            token=token,
            now=now,
            reason=reason,
        )


__all__ = [
    "DurableWebProductRuntime",
    "WebProductFinalizationPending",
    "WebProductRuntimeError",
]
