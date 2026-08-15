"""Contract tests for the canonical finished-product adapter registry."""

from __future__ import annotations

from datetime import datetime

import pytest

from services.finished_product_adapters import (
    VERIFIED_FINISHED_PRODUCT_ADAPTER,
    AdapterGrantRequirements,
    FinishedProductAdapterDescriptor,
    FinishedProductAdapterError,
    FinishedProductAdapterRegistry,
)


class _StubAdapter:
    def __init__(self, descriptor: FinishedProductAdapterDescriptor) -> None:
        self._descriptor = descriptor

    @property
    def descriptor(self) -> FinishedProductAdapterDescriptor:
        return self._descriptor

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
        return {"request_id": request_id, "objective": objective}

    def execute(
        self,
        request_id: str,
        grant_id: str,
        *,
        token: str,
        now: datetime,
    ) -> dict[str, object]:
        return {"request_id": request_id, "grant_id": grant_id, "accepted": True}

    def resume(
        self,
        request_id: str,
        grant_id: str,
        *,
        token: str,
        now: datetime,
    ) -> dict[str, object]:
        return self.execute(request_id, grant_id, token=token, now=now)


def _descriptor(
    capability_id: str = "ilaios.capability.video-media-factory",
    adapter_id: str = "test.adapter.v1",
) -> FinishedProductAdapterDescriptor:
    return FinishedProductAdapterDescriptor(
        adapter_id=adapter_id,
        capability_id=capability_id,
        version="1.0",
        maturity=VERIFIED_FINISHED_PRODUCT_ADAPTER,
        grant=AdapterGrantRequirements(
            worker_id="worker-test",
            actions=frozenset({"test.execute"}),
            ttl_seconds=60,
            max_side_effects=1,
            max_resources=1,
        ),
        supports_cancellation=False,
        supports_retry_repair=False,
        supports_deadline=True,
    )


def test_registry_resolves_only_exact_verified_adapter() -> None:
    adapter = _StubAdapter(_descriptor())
    registry = FinishedProductAdapterRegistry((adapter,))

    assert registry.resolve("ilaios.capability.video-media-factory") is adapter
    assert (
        registry.resolve(
            "ilaios.capability.video-media-factory", adapter_id="test.adapter.v1"
        )
        is adapter
    )
    assert (
        registry.resolve(
            "ilaios.capability.video-media-factory", adapter_id="tampered.adapter.v1"
        )
        is None
    )
    assert registry.resolve("ilaios.capability.web-factory") is None
    assert registry.resolve("ilaios.capability.not-real") is None


def test_registry_rejects_duplicate_authority() -> None:
    first = _StubAdapter(_descriptor(adapter_id="first.v1"))
    second = _StubAdapter(_descriptor(adapter_id="second.v1"))

    with pytest.raises(FinishedProductAdapterError, match="only one authoritative"):
        FinishedProductAdapterRegistry((first, second))


def test_descriptor_rejects_unknown_or_unverified_capability() -> None:
    with pytest.raises(FinishedProductAdapterError, match="not canonical"):
        _descriptor(capability_id="ilaios.capability.fake")

    with pytest.raises(FinishedProductAdapterError, match="only verified"):
        FinishedProductAdapterDescriptor(
            adapter_id="review-only.v1",
            capability_id="ilaios.capability.web-factory",
            version="1.0",
            maturity="REVIEW_ONLY",
            grant=AdapterGrantRequirements(
                worker_id="worker-test",
                actions=frozenset({"test.execute"}),
                ttl_seconds=60,
                max_side_effects=0,
                max_resources=1,
            ),
            supports_cancellation=False,
            supports_retry_repair=False,
            supports_deadline=False,
        )
