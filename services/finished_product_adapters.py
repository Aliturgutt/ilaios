"""Canonical finished-product adapter contract and verified adapter registry.

Adapters are bounded orchestration boundaries over existing factory runtimes. They
never become a second Core, coordinator, scheduler, governance authority, or
factory. Only adapters whose descriptor carries the verified finished-product
maturity may be registered as executable.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from services.capability_registry import CAPABILITIES
from services.integrations.product_runtime import DurableVideoProductRuntime


VERIFIED_FINISHED_PRODUCT_ADAPTER = "VERIFIED_FINISHED_PRODUCT_ADAPTER"
_CANONICAL_CAPABILITY_IDS = frozenset(item.capability_id for item in CAPABILITIES)


class FinishedProductAdapterError(RuntimeError):
    """Raised when an adapter or registry violates a canonical safety invariant."""


@dataclass(frozen=True, slots=True)
class AdapterGrantRequirements:
    """Bounded execution-grant requirements declared by a verified adapter."""

    worker_id: str
    actions: frozenset[str]
    ttl_seconds: int
    max_side_effects: int
    max_resources: int

    def __post_init__(self) -> None:
        if not self.worker_id or not self.actions:
            raise FinishedProductAdapterError("adapter grant identity/actions are required")
        if self.ttl_seconds < 1:
            raise FinishedProductAdapterError("adapter grant ttl must be positive")
        if self.max_side_effects < 0 or self.max_resources < 0:
            raise FinishedProductAdapterError("adapter grant bounds must be non-negative")


@dataclass(frozen=True, slots=True)
class FinishedProductAdapterDescriptor:
    """Stable metadata used by the coordinator without factory-specific branching."""

    adapter_id: str
    capability_id: str
    version: str
    maturity: str
    grant: AdapterGrantRequirements
    supports_cancellation: bool
    supports_retry_repair: bool
    supports_deadline: bool

    def __post_init__(self) -> None:
        if not self.adapter_id or not self.version:
            raise FinishedProductAdapterError("adapter id and version are required")
        if self.capability_id not in _CANONICAL_CAPABILITY_IDS:
            raise FinishedProductAdapterError("adapter capability is not canonical")
        if self.maturity != VERIFIED_FINISHED_PRODUCT_ADAPTER:
            raise FinishedProductAdapterError(
                "only verified finished-product adapters may be executable"
            )


class FinishedProductAdapter(Protocol):
    """Canonical bounded bridge from coordinator lifecycle to a factory runtime."""

    @property
    def descriptor(self) -> FinishedProductAdapterDescriptor:
        """Return stable adapter identity, maturity, and bounded grant requirements."""
        ...

    def prepare(
        self,
        request_id: str,
        objective: str,
        *,
        token: str,
        principal_id: str,
        tenant_id: str,
        now: datetime,
    ) -> dict[str, object]:
        """Prepare/admit existing factory execution without performing side effects."""
        ...

    def execute(
        self,
        request_id: str,
        grant_id: str,
        *,
        token: str,
        now: datetime,
    ) -> dict[str, object]:
        """Execute the existing factory runtime under a coordinator-issued grant."""
        ...

    def resume(
        self,
        request_id: str,
        grant_id: str,
        *,
        token: str,
        now: datetime,
    ) -> dict[str, object]:
        """Resume/execute a prepared request according to adapter semantics."""
        ...


class FinishedProductAdapterRegistry:
    """Fail-closed registry of exactly the adapters proven executable today."""

    def __init__(self, adapters: tuple[FinishedProductAdapter, ...]) -> None:
        by_capability: dict[str, FinishedProductAdapter] = {}
        adapter_ids: set[str] = set()
        for adapter in adapters:
            descriptor = adapter.descriptor
            if descriptor.adapter_id in adapter_ids:
                raise FinishedProductAdapterError("adapter IDs must be globally unique")
            if descriptor.capability_id in by_capability:
                raise FinishedProductAdapterError(
                    "a capability may have only one authoritative executable adapter"
                )
            adapter_ids.add(descriptor.adapter_id)
            by_capability[descriptor.capability_id] = adapter
        self._by_capability = by_capability

    def resolve(
        self, capability_id: str, *, adapter_id: str | None = None
    ) -> FinishedProductAdapter | None:
        """Resolve only an exact canonical capability/adapter pair, otherwise fail closed."""

        if capability_id not in _CANONICAL_CAPABILITY_IDS:
            return None
        adapter = self._by_capability.get(capability_id)
        if adapter is None:
            return None
        if adapter_id is not None and adapter.descriptor.adapter_id != adapter_id:
            return None
        return adapter

    def descriptors(self) -> tuple[FinishedProductAdapterDescriptor, ...]:
        """Return deterministic executable-registry metadata for audit/tests."""

        return tuple(
            self._by_capability[key].descriptor for key in sorted(self._by_capability)
        )


class VideoFinishedProductAdapter:
    """Verified adapter over the existing durable Video product runtime."""

    _DESCRIPTOR = FinishedProductAdapterDescriptor(
        adapter_id="video.product-runtime.v1",
        capability_id="ilaios.capability.video-media-factory",
        version="1.0",
        maturity=VERIFIED_FINISHED_PRODUCT_ADAPTER,
        grant=AdapterGrantRequirements(
            worker_id="worker-video",
            actions=frozenset({"video.execute"}),
            ttl_seconds=600,
            max_side_effects=1,
            max_resources=1,
        ),
        supports_cancellation=False,
        supports_retry_repair=False,
        supports_deadline=True,
    )

    def __init__(self, runtime: DurableVideoProductRuntime) -> None:
        self._runtime = runtime

    @property
    def descriptor(self) -> FinishedProductAdapterDescriptor:
        return self._DESCRIPTOR

    def prepare(
        self,
        request_id: str,
        objective: str,
        *,
        token: str,
        principal_id: str,
        tenant_id: str,
        now: datetime,
    ) -> dict[str, object]:
        return self._runtime.prepare(
            request_id,
            objective,
            token=token,
            now=now,
            requester_id=principal_id,
            tenant_id=tenant_id,
            defer_lease=True,
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

    def resume(
        self,
        request_id: str,
        grant_id: str,
        *,
        token: str,
        now: datetime,
    ) -> dict[str, object]:
        return self.execute(request_id, grant_id, token=token, now=now)
