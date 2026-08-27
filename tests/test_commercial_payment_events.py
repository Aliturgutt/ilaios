"""Verified payment-event ingestion into canonical commercial entitlement state."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Mapping

import pytest

from services.commercial_access import CommercialAccessStore, CommercialEntitlement, EntitlementState
from services.commercial_payment_events import (
    CommercialPaymentEventError,
    CommercialPaymentEventProcessor,
    PaymentLifecycle,
    VerifiedPaymentEvent,
)
from src.video_automation.managed_credit_store import ManagedCreditLedgerStore


class _Verifier:
    def __init__(self, event: VerifiedPaymentEvent) -> None:
        self.event = event
        self.calls = 0

    def verify(
        self,
        *,
        raw_body: bytes,
        headers: Mapping[str, str],
        now: datetime,
    ) -> VerifiedPaymentEvent:
        assert raw_body == b"signed-webhook"
        assert headers["X-Signature"] == "verified-by-adapter"
        assert now.tzinfo is not None
        self.calls += 1
        return self.event


def _store(tmp_path: Path) -> CommercialAccessStore:
    credits = ManagedCreditLedgerStore(tmp_path / "credits")
    return CommercialAccessStore(tmp_path / "commercial", credits)


def _event(now: datetime, *, lifecycle: PaymentLifecycle, event_id: str = "pay-1") -> VerifiedPaymentEvent:
    return VerifiedPaymentEvent(
        event_id=event_id,
        tenant_id="tenant-1",
        user_id="user-1",
        plan_id="pro",
        lifecycle=lifecycle,
        valid_until=now + timedelta(days=30),
        paid_provider_allowed=True,
        provider_event_created_at=now - timedelta(seconds=1),
    )


def _ingest(
    processor: CommercialPaymentEventProcessor,
    now: datetime,
) -> CommercialEntitlement:
    return processor.ingest(
        raw_body=b"signed-webhook",
        headers={"X-Signature": "verified-by-adapter"},
        now=now,
    )


def test_verified_active_subscription_applies_canonical_entitlement(tmp_path: Path) -> None:
    now = datetime(2026, 8, 27, tzinfo=timezone.utc)
    verifier = _Verifier(_event(now, lifecycle=PaymentLifecycle.SUBSCRIPTION_ACTIVE))
    store = _store(tmp_path)
    processor = CommercialPaymentEventProcessor(verifier=verifier, commercial_access=store)

    entitlement = _ingest(processor, now)

    assert entitlement.state is EntitlementState.ACTIVE
    assert entitlement.paid_provider_allowed is True
    assert store.get_entitlement(tenant_id="tenant-1", user_id="user-1") == entitlement
    assert verifier.calls == 1


def test_replayed_verified_event_is_idempotent(tmp_path: Path) -> None:
    now = datetime(2026, 8, 27, tzinfo=timezone.utc)
    verifier = _Verifier(_event(now, lifecycle=PaymentLifecycle.SUBSCRIPTION_ACTIVE))
    processor = CommercialPaymentEventProcessor(
        verifier=verifier,
        commercial_access=_store(tmp_path),
    )

    first = _ingest(processor, now)
    repeated = _ingest(processor, now)

    assert repeated == first
    assert repeated.version == 1


def test_same_event_id_with_changed_payment_content_fails_closed(tmp_path: Path) -> None:
    now = datetime(2026, 8, 27, tzinfo=timezone.utc)
    store = _store(tmp_path)
    active_verifier = _Verifier(_event(now, lifecycle=PaymentLifecycle.SUBSCRIPTION_ACTIVE))
    _ingest(
        CommercialPaymentEventProcessor(verifier=active_verifier, commercial_access=store),
        now,
    )
    conflicting = _Verifier(
        _event(now, lifecycle=PaymentLifecycle.SUBSCRIPTION_CANCELLED)
    )

    with pytest.raises(PermissionError, match="conflicts"):
        _ingest(
            CommercialPaymentEventProcessor(verifier=conflicting, commercial_access=store),
            now,
        )


def test_failed_payment_suspends_and_revokes_paid_provider_access(tmp_path: Path) -> None:
    now = datetime(2026, 8, 27, tzinfo=timezone.utc)
    verifier = _Verifier(_event(now, lifecycle=PaymentLifecycle.PAYMENT_FAILED))
    processor = CommercialPaymentEventProcessor(
        verifier=verifier,
        commercial_access=_store(tmp_path),
    )

    entitlement = _ingest(processor, now)

    assert entitlement.state is EntitlementState.SUSPENDED
    assert entitlement.paid_provider_allowed is False


def test_refund_cancels_entitlement(tmp_path: Path) -> None:
    now = datetime(2026, 8, 27, tzinfo=timezone.utc)
    verifier = _Verifier(_event(now, lifecycle=PaymentLifecycle.REFUNDED))
    processor = CommercialPaymentEventProcessor(
        verifier=verifier,
        commercial_access=_store(tmp_path),
    )

    entitlement = _ingest(processor, now)

    assert entitlement.state is EntitlementState.CANCELLED
    assert entitlement.paid_provider_allowed is False


def test_invalid_verifier_result_and_future_event_fail_closed(tmp_path: Path) -> None:
    now = datetime(2026, 8, 27, tzinfo=timezone.utc)

    class _BadVerifier:
        def verify(
            self,
            *,
            raw_body: bytes,
            headers: Mapping[str, str],
            now: datetime,
        ) -> VerifiedPaymentEvent:
            return "not-evidence"  # type: ignore[return-value]

    processor = CommercialPaymentEventProcessor(
        verifier=_BadVerifier(),
        commercial_access=_store(tmp_path / "bad"),
    )
    with pytest.raises(CommercialPaymentEventError, match="invalid evidence"):
        _ingest(processor, now)

    future = VerifiedPaymentEvent(
        event_id="pay-future",
        tenant_id="tenant-1",
        user_id="user-1",
        plan_id="pro",
        lifecycle=PaymentLifecycle.SUBSCRIPTION_ACTIVE,
        valid_until=now + timedelta(days=30),
        paid_provider_allowed=True,
        provider_event_created_at=now + timedelta(seconds=1),
    )
    future_processor = CommercialPaymentEventProcessor(
        verifier=_Verifier(future),
        commercial_access=_store(tmp_path / "future"),
    )
    with pytest.raises(CommercialPaymentEventError, match="future"):
        _ingest(future_processor, now)


def test_empty_raw_body_is_rejected_before_provider_verifier(tmp_path: Path) -> None:
    now = datetime(2026, 8, 27, tzinfo=timezone.utc)
    verifier = _Verifier(_event(now, lifecycle=PaymentLifecycle.SUBSCRIPTION_ACTIVE))
    processor = CommercialPaymentEventProcessor(
        verifier=verifier,
        commercial_access=_store(tmp_path),
    )

    with pytest.raises(CommercialPaymentEventError, match="non-empty bytes"):
        processor.ingest(raw_body=b"", headers={}, now=now)
    assert verifier.calls == 0
