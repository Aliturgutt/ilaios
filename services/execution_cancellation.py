"""Thin authenticated cancellation helper around the canonical coordinator.

Execution state, adapter interruption, grant revocation, closure and evidence remain
owned by ``ExecutionCoordinator.cancel``. This module only returns the resulting
owner-scoped state and performs best-effort cleanup of idle request workers.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, cast

from services.execution_coordinator import ExecutionCoordinator, ExecutionState
from services.runtime import SchedulingError


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
    """Delegate cancellation to the one canonical coordinator authority."""
    normalized = " ".join(reason.split())
    if not normalized:
        raise ValueError("cancellation reason is required")
    if len(normalized) > 2048:
        raise ValueError("cancellation reason exceeds limit")
    coordinator.cancel(
        request_id,
        token=token,
        actor_id=principal_id,
        tenant_id=tenant_id,
        now=now,
    )
    cleanup_terminal_resources(coordinator)
    return coordinator.get(
        request_id,
        principal_id=principal_id,
        tenant_id=tenant_id,
    )


def cleanup_terminal_resources(coordinator: ExecutionCoordinator) -> int:
    """Best-effort removal of idle workers owned by registered runtimes.

    Ownership is derived from each runtime's durable request table before any
    scheduler mutation. This avoids treating every generic ``worker-*`` entry in
    a shared scheduler as disposable while still recognizing the canonical Video
    runtime's ``worker-<request_id>`` identities.
    """
    adapters = cast(dict[str, Any], getattr(coordinator, "_adapters"))
    schedulers: dict[int, tuple[Any, set[str]]] = {}
    for adapter in adapters.values():
        runtime = getattr(adapter, "_runtime", None)
        scheduler = getattr(runtime, "_scheduler", None)
        if scheduler is None:
            continue
        key = id(scheduler)
        if key not in schedulers:
            schedulers[key] = (scheduler, set())
        schedulers[key][1].update(_runtime_owned_worker_ids(runtime))

    removed = 0
    for scheduler, owned_workers in schedulers.values():
        try:
            state = scheduler.state()
        except Exception:
            continue
        workers = cast(list[dict[str, object]], state.get("workers", []))
        leases = cast(list[dict[str, object]], state.get("leases", []))
        leased_workers = {str(item.get("worker_id")) for item in leases}
        for worker in workers:
            worker_id = str(worker.get("worker_id", ""))
            if not worker_id or worker_id in leased_workers:
                continue
            legacy_owned = any(
                marker in worker_id
                for marker in ("video-worker-", "web-worker-", "software-worker-")
            )
            if worker_id not in owned_workers and not legacy_owned:
                continue
            try:
                if scheduler.unregister(worker_id):
                    removed += 1
            except SchedulingError as error:
                if "with lease" not in str(error):
                    raise
    return removed


def _runtime_owned_worker_ids(runtime: Any) -> set[str]:
    """Read durable worker ownership without mutating runtime state."""
    database_path = getattr(runtime, "_database_path", None)
    if not isinstance(database_path, Path):
        return set()
    try:
        with sqlite3.connect(database_path) as connection:
            table = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='product_proofs'"
            ).fetchone()
            if table is None:
                return set()
            columns = {
                str(row[1])
                for row in connection.execute("PRAGMA table_info(product_proofs)").fetchall()
            }
            if "worker_id" not in columns:
                return set()
            return {
                str(row[0])
                for row in connection.execute(
                    "SELECT worker_id FROM product_proofs WHERE worker_id IS NOT NULL"
                ).fetchall()
                if row[0]
            }
    except sqlite3.Error:
        return set()


def cancellation_metrics(coordinator: ExecutionCoordinator) -> dict[str, int]:
    """Expose low-cardinality cancellation/lifecycle counts."""
    metrics = coordinator.metrics()
    states = cast(dict[str, int], metrics.get("states", {}))
    return {
        "cancelled": int(str(metrics.get("cancelled", 0))),
        "accepted": int(str(metrics.get("accepted", 0))),
        "failed": int(str(metrics.get("failed", 0))),
        "executing": int(states.get(ExecutionState.EXECUTING.value, 0)),
        "cancelling": int(states.get(ExecutionState.CANCELLING.value, 0)),
        "retryable": int(states.get(ExecutionState.FAILED_RETRYABLE.value, 0)),
    }
