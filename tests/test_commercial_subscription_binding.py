from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from services.commercial_access import CommercialAccessError, CommercialEntitlement, EntitlementState
from services.commercial_subscription_binding import (
    CommercialSubscriptionBindingStore,
    CommercialWebhookEntitlementProcessor,
)
from services.commercial_webhook import CommercialWebhookVerifier


class _RecordingCommercialAccess:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def apply_entitlement(
        self,
        *,
        event_id: str,
        tenant_id: str,
        user_id: str,
        plan_id: str,
        state: EntitlementState,
        valid_until: datetime | None,
        paid_provider_allowed: bool,
        now: datetime,
    ) -> CommercialEntitlement:
        self.calls.append(
            {
                "event_id": event_id,
                "tenant_id": tenant_id,
                "user_id": user_id,
                "plan_id": plan_id,
                "state": state,
                "valid_until": valid_until,
                "paid_provider_allowed": paid_provider_allowed,
                "now": now,
            }
        )
        return CommercialEntitlement(
            tenant_id=tenant_id,
            user_id=user_id,
            plan_id=plan_id,
            state=state,
            valid_until=valid_until,
            paid_provider_allowed=paid_provider_allowed,
            version=len(self.calls),
        )


def _signed_event(
    *,
    secret: bytes,
    now: datetime,
    event_id: str = "evt-1",
    event_type: str = "subscription.activated",
    provider_subscription_id: str = "sub-1",
    occurred_at: datetime | None = None,
) -> tuple[bytes, str]:
    event_time = now if occurred_at is None else occurred_at
    body = json.dumps(
        {
            "event_id": event_id,
            "event_type": event_type,
            "provider_subscription_id": provider_subscription_id,
            "occurred_at": event_time.isoformat(),
        },
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    timestamp = int(now.timestamp())
    signature = hmac.new(
        secret,
        str(timestamp).encode("ascii") + b"." + body,
        hashlib.sha256,
    ).hexdigest()
    return body, f"t={timestamp},v1={signature}"


def test_subscription_binding_is_idempotent_and_rejects_takeover(tmp_path: Path) -> None:
    store = CommercialSubscriptionBindingStore(tmp_path)
    now = datetime(2026, 8, 27, 1, 0, tzinfo=timezone.utc)

    first = store.bind(
        provider_subscription_id="sub-1",
        tenant_id="tenant-1",
        user_id="user-1",
        plan_id="pro",
        now=now,
    )
    replay = store.bind(
        provider_subscription_id="sub-1",
        tenant_id="tenant-1",
        user_id="user-1",
        plan_id="pro",
        now=now,
    )
    assert replay == first

    with pytest.raises(CommercialAccessError, match="different canonical identity"):
        store.bind(
            provider_subscription_id="sub-1",
            tenant_id="tenant-2",
            user_id="user-2",
            plan_id="enterprise",
            now=now,
        )


def test_signed_provider_event_uses_server_owned_canonical_binding(tmp_path: Path) -> None:
    secret = b"s" * 32
    now = datetime(2026, 8, 27, 1, 0, tzinfo=timezone.utc)
    bindings = CommercialSubscriptionBindingStore(tmp_path)
    bindings.bind(
        provider_subscription_id="sub-1",
        tenant_id="tenant-1",
        user_id="user-1",
        plan_id="pro",
        now=now,
    )
    access = _RecordingCommercialAccess()
    processor = CommercialWebhookEntitlementProcessor(
        verifier=CommercialWebhookVerifier(secret),
        bindings=bindings,
        commercial_access=access,
    )
    body, signature = _signed_event(secret=secret, now=now)

    entitlement = processor.ingest(raw_body=body, signature_header=signature, now=now)

    assert entitlement.tenant_id == "tenant-1"
    assert entitlement.user_id == "user-1"
    assert entitlement.plan_id == "pro"
    assert entitlement.state is EntitlementState.ACTIVE
    assert entitlement.paid_provider_allowed is True
    assert access.calls[0]["event_id"] == "commercial:sub-1:evt-1"


def test_unbound_subscription_is_denied_before_entitlement_mutation(tmp_path: Path) -> None:
    secret = b"s" * 32
    now = datetime(2026, 8, 27, 1, 0, tzinfo=timezone.utc)
    access = _RecordingCommercialAccess()
    processor = CommercialWebhookEntitlementProcessor(
        verifier=CommercialWebhookVerifier(secret),
        bindings=CommercialSubscriptionBindingStore(tmp_path),
        commercial_access=access,
    )
    body, signature = _signed_event(secret=secret, now=now, provider_subscription_id="unknown")

    with pytest.raises(CommercialAccessError, match="not bound"):
        processor.ingest(raw_body=body, signature_header=signature, now=now)
    assert access.calls == []


@pytest.mark.parametrize(
    ("event_type", "expected_state"),
    [
        ("subscription.suspended", EntitlementState.SUSPENDED),
        ("payment.failed", EntitlementState.SUSPENDED),
        ("subscription.cancelled", EntitlementState.CANCELLED),
        ("payment.refunded", EntitlementState.CANCELLED),
    ],
)
def test_non_active_lifecycle_revokes_paid_provider_access(
    tmp_path: Path,
    event_type: str,
    expected_state: EntitlementState,
) -> None:
    secret = b"s" * 32
    now = datetime(2026, 8, 27, 1, 0, tzinfo=timezone.utc)
    bindings = CommercialSubscriptionBindingStore(tmp_path)
    bindings.bind(
        provider_subscription_id="sub-1",
        tenant_id="tenant-1",
        user_id="user-1",
        plan_id="pro",
        now=now,
    )
    access = _RecordingCommercialAccess()
    processor = CommercialWebhookEntitlementProcessor(
        verifier=CommercialWebhookVerifier(secret),
        bindings=bindings,
        commercial_access=access,
    )
    body, signature = _signed_event(secret=secret, now=now, event_type=event_type)

    entitlement = processor.ingest(raw_body=body, signature_header=signature, now=now)

    assert entitlement.state is expected_state
    assert entitlement.paid_provider_allowed is False


def test_future_provider_event_is_denied(tmp_path: Path) -> None:
    secret = b"s" * 32
    now = datetime(2026, 8, 27, 1, 0, tzinfo=timezone.utc)
    bindings = CommercialSubscriptionBindingStore(tmp_path)
    bindings.bind(
        provider_subscription_id="sub-1",
        tenant_id="tenant-1",
        user_id="user-1",
        plan_id="pro",
        now=now,
    )
    access = _RecordingCommercialAccess()
    processor = CommercialWebhookEntitlementProcessor(
        verifier=CommercialWebhookVerifier(secret),
        bindings=bindings,
        commercial_access=access,
    )
    body, signature = _signed_event(
        secret=secret,
        now=now,
        occurred_at=now + timedelta(seconds=1),
    )

    with pytest.raises(CommercialAccessError, match="future"):
        processor.ingest(raw_body=body, signature_header=signature, now=now)
    assert access.calls == []
