from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from services.commercial_access import (
    CommercialAccessError,
    CommercialAccessStore,
    EntitlementState,
    ProviderSubscriptionState,
)
from services.commercial_webhook import VerifiedCommercialWebhookEvent
from services.control_plane.migrations import migrate_database
from services.identity_commercial_access import IdentityBoundCommercialAccess
from src.video_automation.managed_credit_store import ManagedCreditLedgerStore

NOW = datetime(2026, 8, 27, 5, 0, tzinfo=timezone.utc)


def _access(tmp_path: Path) -> tuple[IdentityBoundCommercialAccess, CommercialAccessStore, Path]:
    database = tmp_path / "control-plane.sqlite3"
    migrate_database(database)
    stamp = NOW.isoformat()
    with sqlite3.connect(database) as connection:
        connection.execute(
            "INSERT INTO identity_tenants (tenant_id,status,created_at,updated_at) "
            "VALUES ('tenant-1','ACTIVE',?,?)",
            (stamp, stamp),
        )
        connection.execute(
            "INSERT INTO identity_users (user_id,enabled,created_at,updated_at) "
            "VALUES ('user-1',1,?,?)",
            (stamp, stamp),
        )
        connection.execute(
            "INSERT INTO identity_memberships "
            "(tenant_id,user_id,role,status,is_primary,created_at,updated_at) "
            "VALUES ('tenant-1','user-1','OWNER','ACTIVE',1,?,?)",
            (stamp, stamp),
        )
    commercial = CommercialAccessStore(
        tmp_path / "commercial", ManagedCreditLedgerStore(tmp_path / "credits")
    )
    return IdentityBoundCommercialAccess(database, commercial), commercial, database


def _event(
    event_id: str,
    event_type: str,
    minute: int,
    *,
    billing_period_end: datetime | None = None,
) -> VerifiedCommercialWebhookEvent:
    occurred_at = NOW + timedelta(minutes=minute)
    return VerifiedCommercialWebhookEvent(
        event_id=event_id,
        event_type=event_type,
        provider_subscription_id="sub-provider-1",
        occurred_at=occurred_at,
        payload_sha256=event_id.encode("utf-8").hex().ljust(64, "0")[:64],
        signature_timestamp=occurred_at,
        billing_period_end=billing_period_end,
    )


def _bind_and_grant(
    access: IdentityBoundCommercialAccess,
    *,
    now: datetime = NOW,
) -> None:
    access.create_provider_subscription_binding(
        provider_subscription_id="sub-provider-1",
        tenant_id="tenant-1",
        user_id="user-1",
        plan_id="pro",
        now=now,
    )
    access.apply_entitlement(
        event_id="grant-1",
        tenant_id="tenant-1",
        user_id="user-1",
        plan_id="pro",
        state=EntitlementState.ACTIVE,
        valid_until=NOW + timedelta(days=30),
        paid_provider_allowed=True,
        now=now,
    )


def test_active_provider_event_without_period_fails_before_state_mutation(tmp_path: Path) -> None:
    access, commercial, _ = _access(tmp_path)
    access.create_provider_subscription_binding(
        provider_subscription_id="sub-provider-1",
        tenant_id="tenant-1",
        user_id="user-1",
        plan_id="pro",
        now=NOW,
    )

    with pytest.raises(CommercialAccessError, match="billing period"):
        access.reconcile_verified_provider_entitlement(
            event=_event("evt-active", "subscription.activated", 1),
            now=NOW + timedelta(minutes=1),
        )

    binding = commercial.get_provider_subscription_binding(
        provider_subscription_id="sub-provider-1"
    )
    assert binding.state is ProviderSubscriptionState.PENDING
    with pytest.raises(CommercialAccessError, match="does not exist"):
        commercial.get_entitlement(tenant_id="tenant-1", user_id="user-1")


def test_active_provider_event_grants_bounded_base_entitlement(tmp_path: Path) -> None:
    access, commercial, _ = _access(tmp_path)
    access.create_provider_subscription_binding(
        provider_subscription_id="sub-provider-1",
        tenant_id="tenant-1",
        user_id="user-1",
        plan_id="pro",
        now=NOW,
    )
    period_end = NOW + timedelta(days=30)

    binding, entitlement = access.reconcile_verified_provider_entitlement(
        event=_event(
            "evt-active",
            "subscription.activated",
            1,
            billing_period_end=period_end,
        ),
        now=NOW + timedelta(minutes=1),
    )

    assert binding.state is ProviderSubscriptionState.ACTIVE
    assert entitlement is not None
    assert entitlement.state is EntitlementState.ACTIVE
    assert entitlement.plan_id == "pro"
    assert entitlement.valid_until == period_end
    assert entitlement.paid_provider_allowed is False
    assert commercial.require_access(
        tenant_id="tenant-1",
        user_id="user-1",
        now=NOW + timedelta(days=1),
    ) == entitlement
    with pytest.raises(CommercialAccessError, match="does not authorize paid providers"):
        commercial.require_access(
            tenant_id="tenant-1",
            user_id="user-1",
            now=NOW + timedelta(days=1),
            paid_provider=True,
        )


def test_positive_period_must_be_current_and_bounded(tmp_path: Path) -> None:
    access, commercial, _ = _access(tmp_path)
    access.create_provider_subscription_binding(
        provider_subscription_id="sub-provider-1",
        tenant_id="tenant-1",
        user_id="user-1",
        plan_id="pro",
        now=NOW,
    )
    invalid_periods = (
        NOW,
        NOW + timedelta(days=401),
    )
    for index, period_end in enumerate(invalid_periods):
        with pytest.raises(CommercialAccessError, match="billing period"):
            access.reconcile_verified_provider_entitlement(
                event=_event(
                    f"evt-invalid-{index}",
                    "subscription.activated",
                    1,
                    billing_period_end=period_end,
                ),
                now=NOW + timedelta(minutes=1),
            )
    binding = commercial.get_provider_subscription_binding(
        provider_subscription_id="sub-provider-1"
    )
    assert binding.state is ProviderSubscriptionState.PENDING


def test_positive_event_does_not_reactivate_disabled_identity(tmp_path: Path) -> None:
    access, commercial, database = _access(tmp_path)
    access.create_provider_subscription_binding(
        provider_subscription_id="sub-provider-1",
        tenant_id="tenant-1",
        user_id="user-1",
        plan_id="pro",
        now=NOW,
    )
    with sqlite3.connect(database) as connection:
        connection.execute("UPDATE identity_users SET enabled = 0 WHERE user_id = 'user-1'")

    with pytest.raises(CommercialAccessError, match="membership is not active"):
        access.reconcile_verified_provider_entitlement(
            event=_event(
                "evt-active",
                "subscription.activated",
                1,
                billing_period_end=NOW + timedelta(days=30),
            ),
            now=NOW + timedelta(minutes=1),
        )

    binding = commercial.get_provider_subscription_binding(
        provider_subscription_id="sub-provider-1"
    )
    assert binding.state is ProviderSubscriptionState.ACTIVE
    with pytest.raises(CommercialAccessError, match="does not exist"):
        commercial.get_entitlement(tenant_id="tenant-1", user_id="user-1")


def test_failed_payment_suspends_existing_entitlement_and_disables_paid_provider(
    tmp_path: Path,
) -> None:
    access, commercial, _ = _access(tmp_path)
    _bind_and_grant(access)

    binding, entitlement = access.reconcile_verified_provider_entitlement(
        event=_event("evt-failed", "payment.failed", 1),
        now=NOW + timedelta(minutes=1),
    )

    assert binding.state is ProviderSubscriptionState.SUSPENDED
    assert entitlement is not None
    assert entitlement.state is EntitlementState.SUSPENDED
    assert entitlement.paid_provider_allowed is False
    with pytest.raises(CommercialAccessError, match="not active"):
        commercial.require_access(
            tenant_id="tenant-1",
            user_id="user-1",
            now=NOW + timedelta(minutes=2),
            paid_provider=True,
        )


def test_refund_cancels_entitlement_even_after_identity_is_disabled(tmp_path: Path) -> None:
    access, commercial, database = _access(tmp_path)
    _bind_and_grant(access)
    with sqlite3.connect(database) as connection:
        connection.execute("UPDATE identity_users SET enabled = 0 WHERE user_id = 'user-1'")

    binding, entitlement = access.reconcile_verified_provider_entitlement(
        event=_event("evt-refund", "payment.refunded", 1),
        now=NOW + timedelta(minutes=1),
    )

    assert binding.state is ProviderSubscriptionState.CANCELLED
    assert entitlement is not None
    assert entitlement.state is EntitlementState.CANCELLED
    assert entitlement.paid_provider_allowed is False
    stored = commercial.get_entitlement(tenant_id="tenant-1", user_id="user-1")
    assert stored.state is EntitlementState.CANCELLED


def test_reconciliation_replay_is_idempotent(tmp_path: Path) -> None:
    access, _, _ = _access(tmp_path)
    _bind_and_grant(access)
    event = _event("evt-cancel", "subscription.cancelled", 1)

    _, first = access.reconcile_verified_provider_entitlement(
        event=event,
        now=NOW + timedelta(minutes=1),
    )
    _, replayed = access.reconcile_verified_provider_entitlement(
        event=event,
        now=NOW + timedelta(minutes=2),
    )

    assert first is not None
    assert replayed == first
    assert replayed.version == 2


def test_positive_reconciliation_replay_is_idempotent(tmp_path: Path) -> None:
    access, _, _ = _access(tmp_path)
    access.create_provider_subscription_binding(
        provider_subscription_id="sub-provider-1",
        tenant_id="tenant-1",
        user_id="user-1",
        plan_id="pro",
        now=NOW,
    )
    event = _event(
        "evt-active",
        "subscription.activated",
        1,
        billing_period_end=NOW + timedelta(days=30),
    )

    _, first = access.reconcile_verified_provider_entitlement(
        event=event,
        now=NOW + timedelta(minutes=1),
    )
    _, replayed = access.reconcile_verified_provider_entitlement(
        event=event,
        now=NOW + timedelta(minutes=2),
    )

    assert first is not None
    assert replayed == first
    assert replayed.version == 1


def test_unverified_object_cannot_mutate_entitlement(tmp_path: Path) -> None:
    access, commercial, _ = _access(tmp_path)
    _bind_and_grant(access)

    class FakeEvent:
        event_id = "evt-fake"

    with pytest.raises(CommercialAccessError, match="cryptographically verified"):
        access.reconcile_verified_provider_entitlement(
            event=FakeEvent(),
            now=NOW + timedelta(minutes=1),
        )
    stored = commercial.get_entitlement(tenant_id="tenant-1", user_id="user-1")
    assert stored.state is EntitlementState.ACTIVE
    assert stored.paid_provider_allowed is True
