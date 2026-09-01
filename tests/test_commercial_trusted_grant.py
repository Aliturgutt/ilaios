from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from services.commercial_access import (
    MAX_TRUSTED_GRANT_DURATION,
    CommercialAccessError,
    CommercialAccessStore,
    EntitlementState,
)
from services.control_plane.migrations import migrate_database
from services.identity_commercial_access import IdentityBoundCommercialAccess
from src.video_automation.managed_credit_store import ManagedCreditLedgerStore

NOW = datetime(2026, 8, 28, 4, 30, tzinfo=timezone.utc)


def _identity_bound(tmp_path: Path) -> tuple[IdentityBoundCommercialAccess, CommercialAccessStore, Path]:
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
    return IdentityBoundCommercialAccess(database, commercial), commercial, database


def _bind(access: IdentityBoundCommercialAccess) -> None:
    access.create_provider_subscription_binding(
        provider_subscription_id="sub-provider-1",
        tenant_id="tenant-1",
        user_id="user-1",
        plan_id="pro",
        now=NOW,
    )


def test_trusted_grant_uses_binding_coordinates_and_does_not_mint_entitlement(
    tmp_path: Path,
) -> None:
    access, commercial, _ = _identity_bound(tmp_path)
    _bind(access)
    grant = access.create_trusted_grant(
        grant_id="grant-1",
        provider_subscription_id="sub-provider-1",
        period_start=NOW,
        period_end=NOW + timedelta(days=30),
        paid_provider_allowed=False,
        now=NOW,
    )
    assert grant.tenant_id == "tenant-1"
    assert grant.user_id == "user-1"
    assert grant.plan_id == "pro"
    assert grant.provider_subscription_id == "sub-provider-1"
    assert grant.version == 1
    assert grant.paid_provider_allowed is False
    assert commercial.get_trusted_grant(grant_id="grant-1") == grant
    with pytest.raises(CommercialAccessError, match="does not exist"):
        commercial.get_entitlement(tenant_id="tenant-1", user_id="user-1")


def test_grant_id_is_idempotent_and_conflicting_policy_fails_closed(tmp_path: Path) -> None:
    access, _, _ = _identity_bound(tmp_path)
    _bind(access)
    first = access.create_trusted_grant(
        grant_id="grant-1",
        provider_subscription_id="sub-provider-1",
        period_start=NOW,
        period_end=NOW + timedelta(days=30),
        paid_provider_allowed=False,
        now=NOW,
    )
    repeated = access.create_trusted_grant(
        grant_id="grant-1",
        provider_subscription_id="sub-provider-1",
        period_start=NOW,
        period_end=NOW + timedelta(days=30),
        paid_provider_allowed=False,
        now=NOW + timedelta(minutes=1),
    )
    assert repeated == first
    with pytest.raises(CommercialAccessError, match="conflicts"):
        access.create_trusted_grant(
            grant_id="grant-1",
            provider_subscription_id="sub-provider-1",
            period_start=NOW,
            period_end=NOW + timedelta(days=31),
            paid_provider_allowed=False,
            now=NOW,
        )


def test_unknown_subscription_and_inactive_identity_fail_closed(tmp_path: Path) -> None:
    access, _, database = _identity_bound(tmp_path)
    with pytest.raises(CommercialAccessError, match="binding does not exist"):
        access.create_trusted_grant(
            grant_id="grant-unknown",
            provider_subscription_id="sub-missing",
            period_start=NOW,
            period_end=NOW + timedelta(days=30),
            paid_provider_allowed=False,
            now=NOW,
        )
    _bind(access)
    with sqlite3.connect(database) as connection:
        connection.execute("UPDATE identity_users SET enabled = 0 WHERE user_id = 'user-1'")
    with pytest.raises(CommercialAccessError, match="not active"):
        access.create_trusted_grant(
            grant_id="grant-disabled",
            provider_subscription_id="sub-provider-1",
            period_start=NOW,
            period_end=NOW + timedelta(days=30),
            paid_provider_allowed=False,
            now=NOW,
        )


def test_invalid_expired_inverted_and_overlong_periods_fail_closed(tmp_path: Path) -> None:
    access, _, _ = _identity_bound(tmp_path)
    _bind(access)
    with pytest.raises(CommercialAccessError, match="end after"):
        access.create_trusted_grant(
            grant_id="grant-inverted",
            provider_subscription_id="sub-provider-1",
            period_start=NOW + timedelta(days=2),
            period_end=NOW + timedelta(days=1),
            paid_provider_allowed=False,
            now=NOW,
        )
    with pytest.raises(CommercialAccessError, match="already expired"):
        access.create_trusted_grant(
            grant_id="grant-expired",
            provider_subscription_id="sub-provider-1",
            period_start=NOW - timedelta(days=30),
            period_end=NOW,
            paid_provider_allowed=False,
            now=NOW,
        )
    with pytest.raises(CommercialAccessError, match="policy maximum"):
        access.create_trusted_grant(
            grant_id="grant-overlong",
            provider_subscription_id="sub-provider-1",
            period_start=NOW,
            period_end=NOW + MAX_TRUSTED_GRANT_DURATION + timedelta(seconds=1),
            paid_provider_allowed=False,
            now=NOW,
        )


def test_client_or_webhook_cannot_select_account_plan_authority(tmp_path: Path) -> None:
    access, _, _ = _identity_bound(tmp_path)
    _bind(access)
    with pytest.raises(TypeError):
        access.create_trusted_grant(  # type: ignore[call-arg]
            grant_id="grant-smuggle",
            provider_subscription_id="sub-provider-1",
            tenant_id="tenant-2",
            user_id="user-2",
            plan_id="enterprise",
            period_start=NOW,
            period_end=NOW + timedelta(days=30),
            paid_provider_allowed=False,
            now=NOW,
        )


def test_grant_creation_does_not_change_existing_entitlement(tmp_path: Path) -> None:
    access, commercial, _ = _identity_bound(tmp_path)
    _bind(access)
    before = access.apply_entitlement(
        event_id="admin-seed",
        tenant_id="tenant-1",
        user_id="user-1",
        plan_id="legacy",
        state=EntitlementState.SUSPENDED,
        valid_until=None,
        paid_provider_allowed=False,
        now=NOW,
    )
    access.create_trusted_grant(
        grant_id="grant-1",
        provider_subscription_id="sub-provider-1",
        period_start=NOW,
        period_end=NOW + timedelta(days=30),
        paid_provider_allowed=True,
        now=NOW,
    )
    after = commercial.get_entitlement(tenant_id="tenant-1", user_id="user-1")
    assert after == before
