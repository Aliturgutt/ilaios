"""Closure helpers for authenticated cancellation and terminal resource cleanup.

This module extends the canonical ExecutionCoordinator without creating another
execution authority. It only composes the coordinator's existing durable state,
product interruption, job state machine, grant policy, and scheduler cleanup.
"""

from __future__ import annotations

import hashlib
import sqlite3
from datetime import datetime
from typing import Any, cast

from services.execution_coordinator import (
    ExecutionCoordinator,
    ExecutionCoordinatorError,
)
from services.runtime import SchedulingError
from src.video_automation.models import JobState

_NONTERMINAL_CANCELLABLE = frozenset(
    {
        "ADMITTED",
        "APPROVED",
        "PENDING_APPROVAL",
        "BLOCKED_ADAPTER_UNAVAILABLE",
        "EXECUTING",
    }
)
_TERMINAL_STATUSES = frozenset(
    {"ACCEPTED", "FAILED", "DENIED", "INTERRUPTED", "CANCELLED"}
)
_PRODUCT_TERMINAL_STATUSES = (
    "accepted",
    "failed",
    "interrupted",
    "cancelled",
)


def cancel_execution(
    coordinator: ExecutionCoordinator,
    request_id: str,
    *,
    token: str,
    principal_id: str,
    tenant_id: str,
    reason: str,
    now: datetime,
) -> dict[str, object]:
    """Cancel one owned execution through existing fail-closed primitives.

    Cancellation is idempotent for an already-cancelled request. Verified
    acceptance and other terminal outcomes are never overwritten by cancellation.
    """
    if now.tzinfo is None:
        raise ExecutionCoordinatorError("cancellation time must be timezone-aware")
    if not reason or reason != reason.strip():
        raise ExecutionCoordinatorError("cancellation reason must be non-blank and trimmed")
    if len(reason) > 2048:
        raise ExecutionCoordinatorError("cancellation reason exceeds limit")

    execution = coordinator.get(request_id)
    if (
        execution.get("principal_id") != principal_id
        or execution.get("tenant_id") != tenant_id
    ):
        raise ExecutionCoordinatorError("cross-tenant execution cancellation denied")

    current_status = str(execution["execution_status"])
    if current_status == "CANCELLED":
        return execution
    if current_status in _TERMINAL_STATUSES:
        raise ExecutionCoordinatorError(
            f"terminal execution cannot be cancelled from {current_status}"
        )
    if current_status not in _NONTERMINAL_CANCELLABLE:
        raise ExecutionCoordinatorError("execution request is not cancellable")

    video = cast(Any, getattr(coordinator, "_video"))
    if execution.get("adapter_id") == "video.product-runtime.v1":
        product_state = cast(dict[str, object], video.get_state(request_id))
        product_status = str(product_state["status"])
        if product_status == "finalizing":
            # Finalizing means durable acceptance evidence already exists. Never
            # let a late cancellation overwrite a verified acceptance race.
            manifest = video.recover_finalizing(request_id, token=token, now=now)
            if manifest.get("accepted") is True:
                raise ExecutionCoordinatorError(
                    "execution reached verified finalization before cancellation"
                )
        elif product_status == "accepted":
            raise ExecutionCoordinatorError("accepted execution cannot be cancelled")
        elif product_status in {"failed", "interrupted", "cancelled"}:
            raise ExecutionCoordinatorError(
                f"product execution is already terminal: {product_status}"
            )

    database_path = cast(Any, getattr(coordinator, "_database_path"))
    with sqlite3.connect(database_path, timeout=10) as connection:
        connection.execute("BEGIN IMMEDIATE")
        changed = connection.execute(
            "UPDATE execution_requests SET status = 'CANCELLING', updated_at = ? "
            "WHERE request_id = ? AND status = ?",
            (now.isoformat(), request_id, current_status),
        ).rowcount
    if changed != 1:
        refreshed = coordinator.get(request_id)
        if refreshed.get("execution_status") == "CANCELLED":
            return refreshed
        raise ExecutionCoordinatorError("execution cancellation lost a concurrent race")

    try:
        if execution.get("adapter_id") == "video.product-runtime.v1":
            interrupted = cast(
                dict[str, object],
                video.interrupt(
                    request_id,
                    token=token,
                    now=now,
                    reason=f"user cancellation: {reason}",
                ),
            )
            if interrupted.get("status") not in {"interrupted", "cancelled"}:
                raise ExecutionCoordinatorError(
                    "product cancellation did not close durably"
                )
            _mark_product_cancelled(video, request_id, reason=reason, now=now)
        else:
            control = cast(Any, getattr(coordinator, "_control_plane"))
            job = control.get_job(token, str(execution["job_id"]))
            if job.state is JobState.PENDING:
                control.transition_job(
                    token,
                    str(execution["job_id"]),
                    JobState.CANCELLED,
                    reason="execution cancelled before adapter availability",
                    now=now,
                )
            elif job.state not in {JobState.CANCELLED, JobState.FAILED, JobState.COMPLETED}:
                control.transition_job(
                    token,
                    str(execution["job_id"]),
                    JobState.CANCELLED,
                    reason="execution cancelled",
                    now=now,
                )

        grants = cast(Any, getattr(coordinator, "_grants"))
        grants.revoke(_grant_id(request_id), now=now)
        cleanup_terminal_resources(coordinator)

        with sqlite3.connect(database_path, timeout=10) as connection:
            connection.execute("BEGIN IMMEDIATE")
            changed = connection.execute(
                "UPDATE execution_requests SET status = 'CANCELLED', updated_at = ? "
                "WHERE request_id = ? AND status = 'CANCELLING'",
                (now.isoformat(), request_id),
            ).rowcount
            if changed != 1:
                raise ExecutionCoordinatorError("execution cancellation state was lost")
            connection.execute(
                "INSERT OR IGNORE INTO execution_closure "
                "(request_id, terminal_status, reason, terminal_at, result_sha256) "
                "VALUES (?, 'CANCELLED', ?, ?, NULL)",
                (request_id, reason, now.isoformat()),
            )
    except Exception:
        with sqlite3.connect(database_path, timeout=10) as connection:
            connection.execute(
                "UPDATE execution_requests SET status = ?, updated_at = ? "
                "WHERE request_id = ? AND status = 'CANCELLING'",
                (current_status, now.isoformat(), request_id),
            )
        raise

    return coordinator.get(request_id)


def cleanup_terminal_resources(coordinator: ExecutionCoordinator) -> int:
    """Remove unleased request-owned workers for durably terminal product proofs."""
    video = cast(Any, getattr(coordinator, "_video"))
    product_database = cast(Any, getattr(video, "_database_path"))
    scheduler = cast(Any, getattr(video, "_scheduler"))
    placeholders = ",".join("?" for _ in _PRODUCT_TERMINAL_STATUSES)
    with sqlite3.connect(product_database, timeout=10) as connection:
        rows = connection.execute(
            f"SELECT worker_id FROM product_proofs WHERE status IN ({placeholders}) "
            "ORDER BY worker_id",
            _PRODUCT_TERMINAL_STATUSES,
        ).fetchall()

    removed = 0
    for row in rows:
        worker_id = str(row[0])
        try:
            if scheduler.unregister(worker_id):
                removed += 1
        except SchedulingError as error:
            if "with lease" not in str(error):
                raise
    return removed


def cancellation_metrics(coordinator: ExecutionCoordinator) -> dict[str, int]:
    """Expose low-cardinality durable coordinator closure counters."""
    database_path = cast(Any, getattr(coordinator, "_database_path"))
    with sqlite3.connect(database_path, timeout=10) as connection:
        terminal = {
            str(row[0]): int(row[1])
            for row in connection.execute(
                "SELECT terminal_status, COUNT(*) FROM execution_closure "
                "GROUP BY terminal_status"
            )
        }
        active = {
            str(row[0]): int(row[1])
            for row in connection.execute(
                "SELECT status, COUNT(*) FROM execution_requests "
                "GROUP BY status"
            )
        }
    return {
        "cancelled": terminal.get("CANCELLED", 0),
        "accepted": terminal.get("ACCEPTED", 0),
        "failed": terminal.get("FAILED", 0),
        "interrupted": terminal.get("INTERRUPTED", 0),
        "executing": active.get("EXECUTING", 0),
        "cancelling": active.get("CANCELLING", 0),
    }


def _mark_product_cancelled(
    video: Any,
    request_id: str,
    *,
    reason: str,
    now: datetime,
) -> None:
    database_path = cast(Any, getattr(video, "_database_path"))
    with sqlite3.connect(database_path, timeout=10) as connection:
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(
            "UPDATE product_proofs SET status = 'cancelled' "
            "WHERE request_id = ? AND status = 'interrupted'",
            (request_id,),
        )
        connection.execute(
            "UPDATE product_proof_closure "
            "SET terminal_status = 'cancelled', reason = ?, terminal_at = ? "
            "WHERE request_id = ? AND terminal_status = 'interrupted'",
            (reason, now.isoformat(), request_id),
        )


def _grant_id(request_id: str) -> str:
    digest = hashlib.sha256(request_id.encode("utf-8")).hexdigest()[:24]
    return f"grant-{digest}"
