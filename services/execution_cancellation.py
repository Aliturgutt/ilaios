"""Thin authenticated cancellation helper around the canonical coordinator.

Execution state, adapter interruption, grant revocation, closure and evidence remain
owned by ``ExecutionCoordinator.cancel``. This module only returns the resulting
owner-scoped state and performs best-effort cleanup of idle request workers.
"""

from __future__ import annotations

from datetime import datetime
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
    """Best-effort removal of idle workers exposed by registered runtimes."""
    adapters = cast(dict[str, Any], getattr(coordinator, "_adapters"))
    removed = 0
    seen_schedulers: set[int] = set()
    for adapter in adapters.values():
        runtime = getattr(adapter, "_runtime", None)
        scheduler = getattr(runtime, "_scheduler", None)
        if scheduler is None or id(scheduler) in seen_schedulers:
            continue
        seen_schedulers.add(id(scheduler))
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
            if not any(
                marker in worker_id
                for marker in ("video-worker-", "web-worker-", "software-worker-")
            ):
                continue
            try:
                if scheduler.unregister(worker_id):
                    removed += 1
            except SchedulingError as error:
                if "with lease" not in str(error):
                    raise
    return removed


def cancellation_metrics(coordinator: ExecutionCoordinator) -> dict[str, int]:
    """Expose low-cardinality cancellation/lifecycle counts."""
    metrics = coordinator.metrics()
    states = cast(dict[str, int], metrics.get("states", {}))
    return {
        "cancelled": int(metrics.get("cancelled", 0)),
        "accepted": int(metrics.get("accepted", 0)),
        "failed": int(metrics.get("failed", 0)),
        "executing": int(states.get(ExecutionState.EXECUTING.value, 0)),
        "cancelling": int(states.get(ExecutionState.CANCELLING.value, 0)),
        "retryable": int(states.get(ExecutionState.FAILED_RETRYABLE.value, 0)),
    }
