from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from services.commercial_access import CommercialAccessError, CommercialAccessStore, ProviderSubscriptionState
from services.commercial_webhook import VerifiedCommercialWebhookEvent
from services.control_plane.migrations import migrate_database
from services.identity_commercial_access import IdentityBoundCommercialAccess
from src.video_automation.managed_credit_store import ManagedCreditLedgerStore


NOW = datetime(2026, 8, 28, 6, 0, tzinfo=timezone.utc)


def test_positive_event_cannot_activate_a_later_trusted_grant(tmp_path: Path) -> None:
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
    access = IdentityBoundCommercialAccess(database, commercial)
    access.create_provider_subscription_binding(
        provider_subscription_id="sub-provider-1",
        tenant_id="tenant-1",
        user_id="user-1",
        plan_id="pro",
        now=NOW,
    )
    access.create_trusted_grant(
        grant_id="grant-later-period",
        provider_subscription_id="sub-provider-1",
        period_start=NOW + timedelta(hours=1),
        period_end=NOW + timedelta(days=30),
        paid_provider_allowed=False,
        now=NOW,
    )

    event = VerifiedCommercialWebhookEvent(
        event_id="evt-before-grant-period",
        event_type="subscription.activated",
        provider_subscription_id="sub-provider-1",
        occurred_at=NOW + timedelta(minutes=30),
        payload_sha256="a" * 64,
        signature_timestamp=NOW + timedelta(minutes=30),
    )

    with pytest.raises(CommercialAccessError, match="predates trusted grant period"):
        access.activate_from_trusted_grant(
            event=event,
            now=NOW + timedelta(hours=2),
        )

    binding = commercial.get_provider_subscription_binding(
        provider_subscription_id="sub-provider-1"
    )
    assert binding.state is ProviderSubscriptionState.PENDING
    with pytest.raises(CommercialAccessError, match="does not exist"):
        commercial.get_entitlement(tenant_id="tenant-1", user_id="user-1")
