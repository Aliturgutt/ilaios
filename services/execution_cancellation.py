"""Authenticated cancellation and terminal resource cleanup for the canonical coordinator.

This module is deliberately a thin composition layer. It does not own execution
state and does not create a second runtime: state transitions, closure and evidence
remain authoritative in ``ExecutionCoordinator`` while adapter-specific interruption
is delegated through the coordinator's verified adapter registry.
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any, cast

from services.execution_coordinator import (
    ExecutionCoordinator,
    ExecutionCoordinatorError,
    ExecutionState,
)
from services.runtime import SchedulingError

_CANCELLABLE = frozenset(
    {
        ExecutionState.PENDING_APPROVAL,
        ExecutionState.ADMITTED,
        ExecutionState.QUEUED,
        ExecutionState.EXECUTING,
        ExecutionState.VERIFYING,
        ExecutionState.FAILED_RETRYABLE,
        ExecutionState.BLOCKED,
    }
)
_TERMINAL = frozenset(
    {
        ExecutionState.ACCEPTED,
        ExecutionState.PARTIAL,
        ExecutionState.CANCELLED,
        ExecutionState.FAILED_TERMINAL,
        ExecutionState.DENIED,
        ExecutionState.INTERRUPTED,
    }
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
    """Cancel one owned request without overwriting verified acceptance."""
    if now.tzinfo is None:
        raise ExecutionCoordinatorError("cancellation time must be timezone-aware")
    normalized = " ".join(reason.split())
    if not normalized:
        raise ExecutionCoordinatorError("cancellation reason is required")
    if len(normalized) > 2048:
        raise ExecutionCoordinatorError("cancellation reason exceeds limit")

    execution = coordinator.get(
        request_id,
        principal_id=principal_id,
        tenant_id=tenant_id,
    )
    state = ExecutionState(str(execution["execution_status"]))
    if state is ExecutionState.CANCELLED:
        return execution
    if state in _TERMINAL:
        raise ExecutionCoordinatorError(
            f"terminal execution cannot be cancelled from {state.value}"
        )
    if state not in _CANCELLABLE:
        raise ExecutionCoordinatorError("execution request is not cancellable")

    adapters = cast(dict[str, Any], getattr(coordinator, "_adapters"))
    capability_id = str(execution["capability_id"])
    adapter = adapters.get(capability_id)

    if adapter is not None:
        adapter_state = cast(dict[str, object], adapter.state(request_id))
        product_status = str(adapter_state.get("status", ""))
        if product_status == "finalizing":
            manifest = cast(
                dict[str, object],
                adapter.recover_finalizing(request_id, token=token, now=now),
            )
            if manifest.get("accepted") is True:
                raise ExecutionCoordinatorError(
                    "execution reached verified finalization before cancellation"
                )
        if product_status == "accepted":
            raise ExecutionCoordinatorError("accepted execution cannot be cancelled")

    transition = cast(Any, getattr(coordinator, "_transition"))
    transition(
        request_id,
        state,
        ExecutionState.CANCELLING,
        now,
        {"reason": normalized},
    )
    try:
        if adapter is not None:
            descriptor = getattr(adapter, "descriptor")
            if not bool(getattr(descriptor, "supports_cancellation", False)):
                raise ExecutionCoordinatorError(
                    "selected verified adapter does not support cancellation"
                )
            interrupted = cast(
                dict[str, object],
                adapter.interrupt(
                    request_id,
                    token=token,
                    now=now,
                    reason=f"user cancellation: {normalized}",
                ),
            )
            product_status = str(interrupted.get("status", ""))
            if product_status == "accepted":
                transition(
                    request_id,
                    ExecutionState.CANCELLING,
                    ExecutionState.ACCEPTED,
                    now,
                    {"reason": "adapter finalized before cancellation"},
                )
                raise ExecutionCoordinatorError(
                    "execution reached verified acceptance before cancellation"
                )
            if product_status not in {"interrupted", "cancelled", "failed"}:
                raise ExecutionCoordinatorError(
                    "adapter cancellation did not reach a durable terminal state"
                )

        grants = cast(Any, getattr(coordinator, "_grants"))
        try:
            grants.revoke(_grant_id(request_id), now=now)
        except Exception:
            pass
        cleanup_terminal_resources(coordinator)

        transition(
            request_id,
            ExecutionState.CANCELLING,
            ExecutionState.CANCELLED,
            now,
            {"reason": normalized},
        )
        record_closure = cast(Any, getattr(coordinator, "_record_closure"))
        record_closure(
            request_id,
            ExecutionState.CANCELLED,
            normalized,
            now,
        )
        record_evidence = cast(Any, getattr(coordinator, "_record_evidence"))
        record_evidence(request_id, ExecutionState.CANCELLED, now)
    except Exception as error:
        latest = coordinator.get(
            request_id,
            principal_id=principal_id,
            tenant_id=tenant_id,
        )
        latest_state = ExecutionState(str(latest["execution_status"]))
        if latest_state is ExecutionState.CANCELLING:
            fail = cast(Any, getattr(coordinator, "_fail"))
            fail(
                request_id,
                ExecutionState.CANCELLING,
                ExecutionState.FAILED_TERMINAL,
                now,
                {
                    "error_code": "CANCELLATION_FAILED",
                    "error_class": type(error).__name__,
                    "retryable": False,
                    "safe_message": "Cancellation could not close subordinate resources safely.",
                    "failed_stage": "cancellation",
                    "attempt": int(latest.get("attempt", 0)),
                    "evidence_id": None,
                },
            )
        raise

    return coordinator.get(
        request_id,
        principal_id=principal_id,
        tenant_id=tenant_id,
    )


def cleanup_terminal_resources(coordinator: ExecutionCoordinator) -> int:
    """Best-effort cleanup of request-owned workers exposed by verified adapters."""
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
    """Return low-cardinality coordinator lifecycle counters."""
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


def _grant_id(request_id: str) -> str:
    digest = hashlib.sha256(request_id.encode("utf-8")).hexdigest()[:24]
    return f"grant-{digest}"
