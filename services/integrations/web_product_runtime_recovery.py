"""Recovery-safe terminal semantics for the canonical Web product runtime."""

from __future__ import annotations

from datetime import datetime

from src.video_automation.models import JobState

from .web_product_runtime import DurableWebProductRuntime, WebProductRuntimeError


class RecoverableWebProductRuntime(DurableWebProductRuntime):
    """Preserve explicit owner cancellation separately from stale interruption."""

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
