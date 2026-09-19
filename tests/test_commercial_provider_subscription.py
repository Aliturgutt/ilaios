from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from services.commercial_access import (
    CommercialAccessError,
    CommercialAccessStore,
    ProviderSubscriptionState,
)
from services.commercial_webhook import VerifiedCommercialWebhookEvent
from services.control_plane.migrations import migrate_database
from services.identity_commercial_access import IdentityBoundCommercialAccess
from src.video_automation.managed_credit_store import ManagedCreditLedgerStore

NOW = datetime(2026, 8, 27, 2, 0, tzinfo=timezone.utc)


def _identity_bound(tmp_path: Path) -> tuple[IdentityBoundCommercialAccess, CommercialAccessStore]:
    database = tmp_path / "control-plane.sqlite3"
    migrate_database(database)
    stamp = NOW.isoformat()
    with sqlite3.connect(database) as connection:
        connection.execute(
            "INSERT INTO identity_tenants (tenant_id,status,created_at,updated_at) "
            "VALUES ('tenant-1','ACTIVE',?,?),('tenant-2','ACTIVE',?,?)",
            (stamp, stamp, stamp, stamp),
        )
        connection.execute(
            "INSERT INTO identity_users (user_id,enabled,created_at,updated_at) "
            "VALUES ('user-1',1,?,?),('user-2',1,?,?)",
            (stamp, stamp, stamp, stamp),
        )
        connection.execute(
            "INSERT INTO identity_memberships "
            "(tenant_id,user_id,role,status,is_primary,created_at,updated_at) "
            "VALUES ('tenant-1','user-1','OWNER','ACTIVE',1,?,?),"
            "('tenant-2','user-2','OWNER','ACTIVE',1,?,?)",
            (stamp, stamp, stamp, stamp),
        )
    commercial = CommercialAccessStore(
        tmp_path / "commercial", ManagedCreditLedgerStore(tmp_path / "credits")
    )
    return IdentityBoundCommercialAccess(database, commercial), commercial


def _event(
    event_id: str,
    event_type: str,
    *,
    subscription_id: str = "sub-provider-1",
    occurred_at: datetime = NOW + timedelta(minutes=1),
    payload_sha256: str | None = None,
) -> VerifiedCommercialWebhookEvent:
    return VerifiedCommercialWebhookEvent(
        event_id=event_id,
        event_type=event_type,
        provider_subscription_id=subscription_id,
        occurred_at=occurred_at,
        payload_sha256=payload_sha256 or (event_id.encode("utf-8").hex().ljust(64, "0")[:64]),
        signature_timestamp=occurred_at,
    )


def test_trusted_binding_maps_provider_id_to_canonical_identity(tmp_path: Path) -> None:
    access, commercial = _identity_bound(tmp_path)

    created = access.create_provider_subscription_binding(
        provider_subscription_id="sub-provider-1",
        tenant_id="tenant-1",
        user_id="user-1",
        plan_id="pro",
        now=NOW,
    )
    repeated = access.create_provider_subscription_binding(
        provider_subscription_id="sub-provider-1",
        tenant_id="tenant-1",
        user_id="user-1",
        plan_id="pro",
        now=NOW + timedelta(seconds=1),
    )

    assert repeated == created
    assert created.state is ProviderSubscriptionState.PENDING
    with pytest.raises(CommercialAccessError, match="does not exist"):
        commercial.get_entitlement(tenant_id="tenant-1", user_id="user-1")


def test_provider_subscription_collision_and_cross_tenant_binding_fail_closed(
    tmp_path: Path,
) -> None:
    access, _ = _identity_bound(tmp_path)
    access.create_provider_subscription_binding(
        provider_subscription_id="sub-provider-1",
        tenant_id="tenant-1",
        user_id="user-1",
        plan_id="pro",
        now=NOW,
    )

    with pytest.raises(CommercialAccessError, match="conflicts"):
        access.create_provider_subscription_binding(
            provider_subscription_id="sub-provider-1",
            tenant_id="tenant-2",
            user_id="user-2",
            plan_id="enterprise",
            now=NOW,
        )
    with pytest.raises(CommercialAccessError, match="does not exist"):
        access.create_provider_subscription_binding(
            provider_subscription_id="sub-provider-2",
            tenant_id="tenant-2",
            user_id="user-1",
            plan_id="pro",
            now=NOW,
        )


def test_verified_lifecycle_events_are_idempotent_and_do_not_mint_entitlement(
    tmp_path: Path,
) -> None:
    access, commercial = _identity_bound(tmp_path)
    access.create_provider_subscription_binding(
        provider_subscription_id="sub-provider-1",
        tenant_id="tenant-1",
        user_id="user-1",
        plan_id="pro",
        now=NOW,
    )
    activated = _event("evt-1", "subscription.activated")

    first = access.apply_verified_provider_event(event=activated, now=NOW + timedelta(minutes=1))
    repeated = access.apply_verified_provider_event(
        event=activated, now=NOW + timedelta(minutes=2)
    )

    assert first == repeated
    assert first.state is ProviderSubscriptionState.ACTIVE
    with pytest.raises(CommercialAccessError, match="does not exist"):
        commercial.get_entitlement(tenant_id="tenant-1", user_id="user-1")


def test_lifecycle_mapping_suspends_and_cancels_without_account_authority(
    tmp_path: Path,
) -> None:
    access, _ = _identity_bound(tmp_path)
    access.create_provider_subscription_binding(
        provider_subscription_id="sub-provider-1",
        tenant_id="tenant-1",
        user_id="user-1",
        plan_id="pro",
        now=NOW,
    )

    active = access.apply_verified_provider_event(
        event=_event("evt-active", "subscription.activated"),
        now=NOW + timedelta(minutes=1),
    )
    suspended = access.apply_verified_provider_event(
        event=_event(
            "evt-failed",
            "payment.failed",
            occurred_at=NOW + timedelta(minutes=2),
        ),
        now=NOW + timedelta(minutes=2),
    )
    cancelled = access.apply_verified_provider_event(
        event=_event(
            "evt-cancel",
            "subscription.cancelled",
            occurred_at=NOW + timedelta(minutes=3),
        ),
        now=NOW + timedelta(minutes=3),
    )

    assert active.state is ProviderSubscriptionState.ACTIVE
    assert suspended.state is ProviderSubscriptionState.SUSPENDED
    assert cancelled.state is ProviderSubscriptionState.CANCELLED
    assert cancelled.tenant_id == "tenant-1"
    assert cancelled.user_id == "user-1"
    assert cancelled.plan_id == "pro"


def test_unknown_out_of_order_and_conflicting_replay_fail_closed(tmp_path: Path) -> None:
    access, _ = _identity_bound(tmp_path)
    with pytest.raises(CommercialAccessError, match="does not exist"):
        access.apply_verified_provider_event(
            event=_event("evt-unknown", "subscription.activated"),
            now=NOW + timedelta(minutes=1),
        )

    access.create_provider_subscription_binding(
        provider_subscription_id="sub-provider-1",
        tenant_id="tenant-1",
        user_id="user-1",
        plan_id="pro",
        now=NOW,
    )
    event = _event("evt-1", "subscription.activated", occurred_at=NOW + timedelta(minutes=2))
    access.apply_verified_provider_event(event=event, now=NOW + timedelta(minutes=2))

    with pytest.raises(CommercialAccessError, match="out of order"):
        access.apply_verified_provider_event(
            event=_event(
                "evt-old",
                "subscription.suspended",
                occurred_at=NOW + timedelta(minutes=1),
            ),
            now=NOW + timedelta(minutes=3),
        )
    with pytest.raises(CommercialAccessError, match="conflicts"):
        access.apply_verified_provider_event(
            event=_event(
                "evt-1",
                "subscription.activated",
                payload_sha256="f" * 64,
                occurred_at=NOW + timedelta(minutes=2),
            ),
            now=NOW + timedelta(minutes=3),
        )


def test_unverified_object_is_rejected_without_state_mutation(tmp_path: Path) -> None:
    access, commercial = _identity_bound(tmp_path)
    access.create_provider_subscription_binding(
        provider_subscription_id="sub-provider-1",
        tenant_id="tenant-1",
        user_id="user-1",
        plan_id="pro",
        now=NOW,
    )

    class FakeEvent:
        provider_subscription_id = "sub-provider-1"

    with pytest.raises(CommercialAccessError, match="cryptographically verified"):
        access.apply_verified_provider_event(event=FakeEvent(), now=NOW + timedelta(minutes=1))
    assert commercial.get_provider_subscription_binding(
        provider_subscription_id="sub-provider-1"
    ).state is ProviderSubscriptionState.PENDING
