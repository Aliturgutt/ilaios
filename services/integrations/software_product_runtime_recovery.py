"""Recovery-safe extension for the bounded Software finished-product runtime."""

from __future__ import annotations

import json
from datetime import datetime

from src.video_automation.models import JobState

from .software_product_runtime import (
    DurableSoftwareProductRuntime,
    SoftwareProductRuntimeError,
)


class RecoverableSoftwareProductRuntime(DurableSoftwareProductRuntime):
    """Add durable terminal/recovery semantics without creating a second Software Factory."""

    def execute(
        self, request_id: str, grant_id: str, *, token: str, now: datetime
    ) -> dict[str, object]:
        try:
            return super().execute(request_id, grant_id, token=token, now=now)
        except Exception as error:
            reason = _failure_reason(error)
            with self._connect() as connection:
                connection.execute(
                    "UPDATE software_product_proofs SET status='failed', manifest_json=? "
                    "WHERE request_id=? AND status='pending'",
                    (json.dumps({"reason": reason}, sort_keys=True), request_id),
                )
            raise

    def get_state(self, request_id: str) -> dict[str, object]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT status, manifest_json FROM software_product_proofs WHERE request_id=?",
                (request_id,),
            ).fetchone()
        if row is None:
            raise SoftwareProductRuntimeError("software proof request is unavailable")
        result: dict[str, object] = {"status": str(row["status"])}
        raw = row["manifest_json"]
        if raw is not None:
            value = json.loads(str(raw))
            if isinstance(value, dict) and isinstance(value.get("reason"), str):
                result["reason"] = value["reason"]
        return result

    def interrupt(
        self,
        request_id: str,
        *,
        token: str,
        now: datetime,
        reason: str,
    ) -> dict[str, object]:
        if now.tzinfo is None:
            raise SoftwareProductRuntimeError("interruption time must be timezone-aware")
        normalized_reason = " ".join(reason.split())
        if not normalized_reason:
            raise SoftwareProductRuntimeError("interruption reason is required")
        with self._connect() as connection:
            row = connection.execute(
                "SELECT job_id, workflow_id, status, manifest_json "
                "FROM software_product_proofs WHERE request_id=?",
                (request_id,),
            ).fetchone()
        if row is None:
            raise SoftwareProductRuntimeError("software proof request is unavailable")
        status = str(row["status"])
        if status == "accepted":
            return {"status": "accepted"}
        if status in {"failed", "interrupted"}:
            return self.get_state(request_id)
        if status != "pending":
            raise SoftwareProductRuntimeError("software proof cannot be interrupted")

        self._workflows.recover_expired_attempts(now=now)
        workflow_state = self._workflows.workflow_state(str(row["workflow_id"]))
        if not bool(workflow_state["terminal"]):
            self._workflows.cancel_workflow(
                str(row["workflow_id"]),
                reason=normalized_reason,
                now=now,
            )
        try:
            self._control_plane.transition_job(
                token,
                str(row["job_id"]),
                JobState.FAILED,
                reason=normalized_reason,
                now=now,
            )
        except Exception:
            # The Control Plane may already hold a terminal state; durable Software proof
            # closure remains authoritative for this bounded interruption operation.
            pass
        payload = json.dumps({"reason": normalized_reason}, sort_keys=True)
        with self._connect() as connection:
            changed = connection.execute(
                "UPDATE software_product_proofs SET status='interrupted', manifest_json=? "
                "WHERE request_id=? AND status='pending'",
                (payload, request_id),
            ).rowcount
        if changed != 1:
            latest = self.get_state(request_id)
            if latest["status"] in {"accepted", "failed", "interrupted"}:
                return latest
            raise SoftwareProductRuntimeError("software interruption state was lost")
        return {"status": "interrupted", "reason": normalized_reason}


def _failure_reason(error: Exception) -> str:
    message = " ".join(str(error).split())
    if not message:
        message = "software execution failed without an error message"
    return f"{type(error).__name__}: {message}"[:2048]
