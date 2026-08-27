"""Verified payment-event boundary for canonical ILAIOS commercial access.

Payment-provider signature verification remains adapter-owned. This module accepts
only events returned by a configured verifier and maps them into the existing
provider-neutral ``CommercialAccessStore``. It does not collect money, create a
second entitlement authority, or bypass Identity/tenant admission.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Mapping, Protocol, runtime_checkable

from services.commercial_access import CommercialAccessStore, CommercialEntitlement, EntitlementState


class CommercialPaymentEventError(PermissionError):
    """Raised when a payment event cannot be safely verified or applied."""


class PaymentLifecycle(str, Enum):
    SUBSCRIPTION_ACTIVE = "SUBSCRIPTION_ACTIVE"
    SUBSCRIPTION_SUSPENDED = "SUBSCRIPTION_SUSPENDED"
    SUBSCRIPTION_CANCELLED = "SUBSCRIPTION_CANCELLED"
    PAYMENT_FAILED = "PAYMENT_FAILED"
    REFUNDED = "REFUNDED"


@dataclass(frozen=True, slots=True)
class VerifiedPaymentEvent:
    event_id: str
    tenant_id: str
    user_id: str
    plan_id: str
    lifecycle: PaymentLifecycle
    valid_until: datetime | None
    paid_provider_allowed: bool
    provider_event_created_at: datetime

    def __post_init__(self) -> None:
        for name in ("event_id", "tenant_id", "user_id", "plan_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value or value != value.strip():
                raise CommercialPaymentEventError(f"{name} must be non-blank and trimmed")
        if not isinstance(self.lifecycle, PaymentLifecycle):
            raise CommercialPaymentEventError("lifecycle must be a PaymentLifecycle")
        for name, value in (
            ("provider_event_created_at", self.provider_event_created_at),
            ("valid_until", self.valid_until),
        ):
            if value is not None and value.tzinfo is None:
                raise CommercialPaymentEventError(f"{name} must be timezone-aware")
        if not isinstance(self.paid_provider_allowed, bool):
            raise CommercialPaymentEventError("paid_provider_allowed must be boolean")


@runtime_checkable
class PaymentEventVerifier(Protocol):
    """Provider adapter contract that authenticates one raw webhook event."""

    def verify(
        self,
        *,
        raw_body: bytes,
        headers: Mapping[str, str],
        now: datetime,
    ) -> VerifiedPaymentEvent: ...


class CommercialPaymentEventProcessor:
    """Apply authenticated payment lifecycle events to canonical entitlement state."""

    def __init__(
        self,
        *,
        verifier: PaymentEventVerifier,
        commercial_access: CommercialAccessStore,
    ) -> None:
        if not isinstance(verifier, PaymentEventVerifier):
            raise CommercialPaymentEventError("payment verifier capability is required")
        self._verifier = verifier
        self._commercial_access = commercial_access

    def ingest(
        self,
        *,
        raw_body: bytes,
        headers: Mapping[str, str],
        now: datetime,
    ) -> CommercialEntitlement:
        if not isinstance(raw_body, bytes) or not raw_body:
            raise CommercialPaymentEventError("raw webhook body must be non-empty bytes")
        if not isinstance(headers, Mapping):
            raise CommercialPaymentEventError("webhook headers must be a mapping")
        if not isinstance(now, datetime) or now.tzinfo is None:
            raise CommercialPaymentEventError("now must be timezone-aware")

        event = self._verifier.verify(raw_body=raw_body, headers=headers, now=now)
        if not isinstance(event, VerifiedPaymentEvent):
            raise CommercialPaymentEventError("payment verifier returned invalid evidence")
        if event.provider_event_created_at > now:
            raise CommercialPaymentEventError("payment event timestamp is in the future")

        state = _entitlement_state(event.lifecycle)
        paid_provider_allowed = (
            event.paid_provider_allowed if state is EntitlementState.ACTIVE else False
        )
        return self._commercial_access.apply_entitlement(
            event_id=event.event_id,
            tenant_id=event.tenant_id,
            user_id=event.user_id,
            plan_id=event.plan_id,
            state=state,
            valid_until=event.valid_until,
            paid_provider_allowed=paid_provider_allowed,
            now=now,
        )


def _entitlement_state(lifecycle: PaymentLifecycle) -> EntitlementState:
    if lifecycle is PaymentLifecycle.SUBSCRIPTION_ACTIVE:
        return EntitlementState.ACTIVE
    if lifecycle in (PaymentLifecycle.SUBSCRIPTION_SUSPENDED, PaymentLifecycle.PAYMENT_FAILED):
        return EntitlementState.SUSPENDED
    if lifecycle in (PaymentLifecycle.SUBSCRIPTION_CANCELLED, PaymentLifecycle.REFUNDED):
        return EntitlementState.CANCELLED
    raise CommercialPaymentEventError("unsupported payment lifecycle")


__all__ = [
    "CommercialPaymentEventError",
    "CommercialPaymentEventProcessor",
    "PaymentEventVerifier",
    "PaymentLifecycle",
    "VerifiedPaymentEvent",
]
