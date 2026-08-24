from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from services.commercial_access import (
    CommercialAccessError,
    CommercialAccessStore,
    EntitlementState,
)
from services.control_plane.migrations import migrate_database
from services.identity_commercial_access import IdentityBoundCommercialAccess
from src.video_automation.managed_credit_store import ManagedCreditLedgerStore
from src.video_automation.managed_credits import ManagedCreditAccount, ProviderCostQuote

NOW = datetime(2026, 8, 24, 10, 30, tzinfo=timezone.utc)
NOW_TEXT = NOW.isoformat()


def _seed_identity(database: Path) -> None:
    migrate_database(database)
    with sqlite3.connect(database) as connection:
        connection.execute(
            "INSERT INTO identity_tenants (tenant_id, status, created_at, updated_at) "
            "VALUES ('tenant-1', 'ACTIVE', ?, ?), ('tenant-2', 'ACTIVE', ?, ?)",
            (NOW_TEXT, NOW_TEXT, NOW_TEXT, NOW_TEXT),
        )
        connection.execute(
            "INSERT INTO identity_users (user_id, enabled, created_at, updated_at) "
            "VALUES ('user-1', 1, ?, ?), ('user-2', 1, ?, ?)",
            (NOW_TEXT, NOW_TEXT, NOW_TEXT, NOW_TEXT),
        )
        connection.execute(
            "INSERT INTO identity_memberships "
            "(tenant_id, user_id, role, status, is_primary, created_at, updated_at) "
            "VALUES ('tenant-1', 'user-1', 'OWNER', 'ACTIVE', 1, ?, ?), "
            "('tenant-2', 'user-2', 'OWNER', 'ACTIVE', 1, ?, ?)",
            (NOW_TEXT, NOW_TEXT, NOW_TEXT, NOW_TEXT),
        )


def _store(tmp_path: Path) -> tuple[IdentityBoundCommercialAccess, CommercialAccessStore]:
    identity_database = tmp_path / "control-plane.sqlite3"
    _seed_identity(identity_database)
    credits = ManagedCreditLedgerStore(tmp_path / "credits")
    commercial = CommercialAccessStore(tmp_path / "commercial", credits)
    return IdentityBoundCommercialAccess(identity_database, commercial), commercial


def _activate(store: IdentityBoundCommercialAccess) -> None:
    store.apply_entitlement(
        event_id="evt-active",
        tenant_id="tenant-1",
        user_id="user-1",
        plan_id="pro",
        state=EntitlementState.ACTIVE,
        valid_until=NOW + timedelta(days=30),
        paid_provider_allowed=True,
        now=NOW,
    )


def test_active_canonical_membership_allows_entitlement_and_access(tmp_path: Path) -> None:
    store, _ = _store(tmp_path)
    _activate(store)

    entitlement = store.require_access(
        tenant_id="tenant-1",
        user_id="user-1",
        now=NOW + timedelta(seconds=1),
        paid_provider=True,
    )

    assert entitlement.tenant_id == "tenant-1"
    assert entitlement.user_id == "user-1"
    assert entitlement.state is EntitlementState.ACTIVE


def test_cross_tenant_or_missing_membership_cannot_receive_entitlement(tmp_path: Path) -> None:
    store, _ = _store(tmp_path)

    with pytest.raises(CommercialAccessError, match="does not exist"):
        store.apply_entitlement(
            event_id="evt-cross-tenant",
            tenant_id="tenant-2",
            user_id="user-1",
            plan_id="pro",
            state=EntitlementState.ACTIVE,
            valid_until=NOW + timedelta(days=30),
            paid_provider_allowed=False,
            now=NOW,
        )


def test_revoked_membership_invalidates_existing_entitlement(tmp_path: Path) -> None:
    store, commercial = _store(tmp_path)
    _activate(store)
    identity_database = tmp_path / "control-plane.sqlite3"
    with sqlite3.connect(identity_database) as connection:
        connection.execute(
            "UPDATE identity_memberships SET status='REVOKED', updated_at=? "
            "WHERE tenant_id='tenant-1' AND user_id='user-1'",
            (NOW_TEXT,),
        )

    with pytest.raises(CommercialAccessError, match="not active"):
        store.require_access(tenant_id="tenant-1", user_id="user-1", now=NOW)

    assert commercial.get_entitlement(
        tenant_id="tenant-1", user_id="user-1"
    ).state is EntitlementState.ACTIVE


def test_disabled_user_cannot_seed_credit_or_reserve_provider_spend(tmp_path: Path) -> None:
    store, _ = _store(tmp_path)
    _activate(store)
    identity_database = tmp_path / "control-plane.sqlite3"
    with sqlite3.connect(identity_database) as connection:
        connection.execute(
            "UPDATE identity_users SET enabled=0, updated_at=? WHERE user_id='user-1'",
            (NOW_TEXT,),
        )

    with pytest.raises(CommercialAccessError, match="not active"):
        store.seed_credit_account(
            ManagedCreditAccount(
                tenant_id="tenant-1",
                user_id="user-1",
                available_microusd=1_000_000,
            )
        )

    with pytest.raises(CommercialAccessError, match="not active"):
        store.reserve_provider_spend(
            tenant_id="tenant-1",
            user_id="user-1",
            now=NOW,
            request_id="request-disabled",
            routing_decision_id="route-disabled",
            quote=ProviderCostQuote("provider-a", "model-a", 10, 20),
        )


def test_inflight_settlement_remains_available_after_membership_revocation(tmp_path: Path) -> None:
    store, _ = _store(tmp_path)
    _activate(store)
    store.seed_credit_account(
        ManagedCreditAccount(
            tenant_id="tenant-1",
            user_id="user-1",
            available_microusd=1_000,
        )
    )
    reserved = store.reserve_provider_spend(
        tenant_id="tenant-1",
        user_id="user-1",
        now=NOW,
        request_id="request-1",
        routing_decision_id="route-1",
        quote=ProviderCostQuote("provider-a", "model-a", 100, 200),
    )
    identity_database = tmp_path / "control-plane.sqlite3"
    with sqlite3.connect(identity_database) as connection:
        connection.execute(
            "UPDATE identity_memberships SET status='REVOKED', updated_at=? "
            "WHERE tenant_id='tenant-1' AND user_id='user-1'",
            (NOW_TEXT,),
        )

    settled = store.settle_provider_spend(
        authorization_id=reserved.authorization.authorization_id,
        actual_cost_microusd=75,
        provider_job_id="provider-job-1",
    )

    assert settled.account.reserved_microusd == 0
    assert settled.account.available_microusd == 925
