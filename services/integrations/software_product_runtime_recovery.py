"""Recovery-safe extension for the bounded Software finished-product runtime."""

from __future__ import annotations

import json
from datetime import datetime

from src.video_automation.models import JobState

from .software_product_runtime import (
    DurableSoftwareProductRuntime,
    SoftwareProductFinalizationPending,
    SoftwareProductRuntimeError,
)


class RecoverableSoftwareProductRuntime(DurableSoftwareProductRuntime):
    """Add durable terminal/recovery semantics without a second Software Factory."""

    def execute(
        self, request_id: str, grant_id: str, *, token: str, now: datetime
    ) -> dict[str, object]:
        try:
            return super().execute(request_id, grant_id, token=token, now=now)
        except SoftwareProductFinalizationPending:
            raise
        except Exception as error:
            reason = _failure_reason(error)
            with self._connect() as connection:
                connection.execute(
                    "UPDATE software_product_proofs SET status='failed', manifest_json=? "
                    "WHERE request_id=? AND status='pending'",
                    (json.dumps({"reason": reason}, sort_keys=True), request_id),
                )
                connection.execute(
                    "INSERT OR IGNORE INTO software_product_closure VALUES "
                    "(?, 'failed', ?, ?)",
                    (request_id, reason, now.isoformat()),
                )
            raise

    def get_state(self, request_id: str) -> dict[str, object]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT status, manifest_json FROM software_product_proofs WHERE request_id=?",
                (request_id,),
            ).fetchone()
            closure = connection.execute(
                "SELECT terminal_status, reason, terminal_at FROM software_product_closure "
                "WHERE request_id=?",
                (request_id,),
            ).fetchone()
        if row is None:
            raise SoftwareProductRuntimeError("software proof request is unavailable")
        result: dict[str, object] = {
            "status": str(row["status"]),
            "terminal": closure is not None,
            "terminal_status": None if closure is None else str(closure["terminal_status"]),
            "reason": None if closure is None else str(closure["reason"]),
            "terminal_at": None if closure is None else str(closure["terminal_at"]),
        }
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
        terminal_status = (
            "cancelled"
            if normalized_reason == "cancelled by authenticated execution owner"
            else "interrupted"
        )
        state = self.get_state(request_id)
        status = str(state["status"])
        if status == "accepted":
            return state
        if status == "finalizing":
            self.recover_finalizing(request_id, token=token, now=now)
            return self.get_state(request_id)
        if status in {"failed", "interrupted", "cancelled"}:
            return state
        if status != "pending":
            raise SoftwareProductRuntimeError("software proof cannot be interrupted")

        with self._connect() as connection:
            row = connection.execute(
                "SELECT job_id, workflow_id FROM software_product_proofs WHERE request_id=?",
                (request_id,),
            ).fetchone()
        if row is None:
            raise SoftwareProductRuntimeError("software proof request is unavailable")
        self._workflows.recover_expired_attempts(now=now)
        workflow_state = self._workflows.workflow_state(str(row["workflow_id"]))
        if not bool(workflow_state["terminal"]):
            self._workflows.cancel_workflow(
                str(row["workflow_id"]), reason=normalized_reason, now=now
            )
        try:
            current = self._control_plane.get_job(token, str(row["job_id"]))
            if current.state not in {JobState.COMPLETED, JobState.FAILED, JobState.CANCELLED}:
                self._control_plane.transition_job(
                    token,
                    str(row["job_id"]),
                    JobState.CANCELLED
                    if terminal_status == "cancelled"
                    else JobState.FAILED,
                    reason=normalized_reason,
                    now=now,
                )
        except Exception:
            pass
        payload = json.dumps({"reason": normalized_reason}, sort_keys=True)
        with self._connect() as connection:
            changed = connection.execute(
                "UPDATE software_product_proofs SET status=?, manifest_json=? "
                "WHERE request_id=? AND status='pending'",
                (terminal_status, payload, request_id),
            ).rowcount
            if changed == 1:
                connection.execute(
                    "INSERT OR IGNORE INTO software_product_closure VALUES "
                    "(?, ?, ?, ?)",
                    (request_id, terminal_status, normalized_reason, now.isoformat()),
                )
        if changed != 1:
            latest = self.get_state(request_id)
            if latest["status"] in {"accepted", "failed", "interrupted", "cancelled"}:
                return latest
            raise SoftwareProductRuntimeError("software interruption state was lost")
        return self.get_state(request_id)


def _failure_reason(error: Exception) -> str:
    message = " ".join(str(error).split())
    if not message:
        message = "software execution failed without an error message"
    return f"{type(error).__name__}: {message}"[:2048]
