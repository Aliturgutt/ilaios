"""Canonical finished-product adapter registration for ExecutionCoordinator.

Registration extends the one coordinator in place. It does not create another
runtime, router, scheduler or governance authority. Only adapters whose concrete
runtime is supplied by the composition root are promoted to executable maturity.
"""

from __future__ import annotations

from datetime import datetime
from typing import cast

import services.execution_coordinator as coordinator_module
from services.control_plane import BudgetEnvelope, DataClass
from services.execution_coordinator import (
    AdapterDescriptor,
    CapabilityMaturity,
    ExecutionAdapter,
    ExecutionCoordinator,
    ExecutionCoordinatorError,
)
from services.integrations.web_product_runtime import DurableWebProductRuntime

_WEB = "ilaios.capability.web-factory"


class WebExecutionAdapter:
    """ExecutionAdapter contract over the proven Web product runtime."""

    descriptor = AdapterDescriptor(
        "web.product-runtime.v1",
        _WEB,
        CapabilityMaturity.VERIFIED_FINISHED_PRODUCT_ADAPTER,
        worker_subject="worker-web",
        action="web.build",
        supports_cancellation=True,
    )

    def __init__(self, runtime: DurableWebProductRuntime) -> None:
        self._runtime = runtime

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
        return self._runtime.prepare(
            request_id,
            objective,
            token=token,
            now=now,
            requester_id=principal_id,
            tenant_id=tenant_id,
            risk=risk,
            data_class=data_class,
            budget=budget,
        )

    def execute(
        self,
        request_id: str,
        grant_id: str,
        *,
        token: str,
        now: datetime,
    ) -> dict[str, object]:
        return self._runtime.execute(request_id, grant_id, token=token, now=now)

    def accepted_result(self, request_id: str) -> dict[str, object]:
        return self._runtime.get_manifest(request_id)

    def state(self, request_id: str) -> dict[str, object]:
        return self._runtime.get_state(request_id)

    def recover_finalizing(
        self,
        request_id: str,
        *,
        token: str,
        now: datetime,
    ) -> dict[str, object]:
        return self._runtime.recover_finalizing(request_id, token=token, now=now)

    def interrupt(
        self,
        request_id: str,
        *,
        token: str,
        now: datetime,
        reason: str,
    ) -> dict[str, object]:
        return self._runtime.interrupt(
            request_id,
            token=token,
            now=now,
            reason=reason,
        )


def register_verified_adapter(
    coordinator: ExecutionCoordinator,
    adapter: ExecutionAdapter,
) -> None:
    """Promote one concrete verified adapter into the canonical registry."""
    descriptor = adapter.descriptor
    if descriptor.maturity is not CapabilityMaturity.VERIFIED_FINISHED_PRODUCT_ADAPTER:
        raise ExecutionCoordinatorError(
            "only verified finished-product adapters may be registered"
        )
    if not descriptor.adapter_id or not descriptor.worker_subject or not descriptor.action:
        raise ExecutionCoordinatorError("verified adapter descriptor is incomplete")
    known = cast(set[str] | frozenset[str], coordinator_module._KNOWN_CAPABILITY_IDS)
    if descriptor.capability_id not in known:
        raise ExecutionCoordinatorError("adapter capability is not canonical")
    adapters = cast(dict[str, ExecutionAdapter], getattr(coordinator, "_adapters"))
    existing = adapters.get(descriptor.capability_id)
    if existing is not None and existing.descriptor.adapter_id != descriptor.adapter_id:
        raise ExecutionCoordinatorError(
            "canonical capability already has a different verified adapter"
        )
    coordinator_module._ADAPTER_DESCRIPTORS[descriptor.capability_id] = descriptor
    adapters[descriptor.capability_id] = adapter


def register_web_runtime(
    coordinator: ExecutionCoordinator,
    runtime: DurableWebProductRuntime,
) -> None:
    register_verified_adapter(coordinator, WebExecutionAdapter(runtime))


__all__ = [
    "WebExecutionAdapter",
    "register_verified_adapter",
    "register_web_runtime",
]
