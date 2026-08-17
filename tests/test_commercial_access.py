"""Commercial entitlement admission over the canonical managed-credit ledger."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from services.commercial_access import (
    CommercialAccessError,
    CommercialAccessStore,
    CommercialEntitlement,
    EntitlementState,
)
from src.video_automation.managed_credit_store import ManagedCreditLedgerStore
from src.video_automation.managed_credits import ManagedCreditAccount, ProviderCostQuote


def _store(tmp_path: Path) -> tuple[CommercialAccessStore, ManagedCreditLedgerStore]:
    credits = ManagedCreditLedgerStore(tmp_path / "credits")
    return CommercialAccessStore(tmp_path / "commercial", credits), credits


def _activate(
    store: CommercialAccessStore,
    now: datetime,
    *,
    paid_provider_allowed: bool = False,
    event_id: str = "evt-active-1",
) -> CommercialEntitlement:
    return store.apply_entitlement(
        event_id=event_id,
        tenant_id="tenant-1",
        user_id="user-1",
        plan_id="pro",
        state=EntitlementState.ACTIVE,
        valid_until=now + timedelta(days=30),
        paid_provider_allowed=paid_provider_allowed,
        now=now,
    )


def test_missing_entitlement_fails_closed(tmp_path: Path) -> None:
    store, _ = _store(tmp_path)
    now = datetime(2026, 8, 17, tzinfo=timezone.utc)

    with pytest.raises(CommercialAccessError, match="does not exist"):
        store.require_access(tenant_id="tenant-1", user_id="user-1", now=now)


def test_active_entitlement_allows_non_paid_access(tmp_path: Path) -> None:
    store, _ = _store(tmp_path)
    now = datetime(2026, 8, 17, tzinfo=timezone.utc)
    entitlement = _activate(store, now)

    admitted = store.require_access(
        tenant_id="tenant-1",
        user_id="user-1",
        now=now + timedelta(seconds=1),
    )

    assert admitted == entitlement
    assert admitted.version == 1


def test_entitlement_event_is_idempotent_and_conflicts_fail(tmp_path: Path) -> None:
    store, _ = _store(tmp_path)
    now = datetime(2026, 8, 17, tzinfo=timezone.utc)
    first = _activate(store, now)
    repeated = _activate(store, now)

    assert repeated == first
    with pytest.raises(CommercialAccessError, match="conflicts"):
        store.apply_entitlement(
            event_id="evt-active-1",
            tenant_id="tenant-1",
            user_id="user-1",
            plan_id="enterprise",
            state=EntitlementState.ACTIVE,
            valid_until=now + timedelta(days=30),
            paid_provider_allowed=True,
            now=now,
        )


def test_suspended_cancelled_and_expired_entitlements_are_denied(
    tmp_path: Path,
) -> None:
    store, _ = _store(tmp_path)
    now = datetime(2026, 8, 17, tzinfo=timezone.utc)
    _activate(store, now)

    store.apply_entitlement(
        event_id="evt-suspend",
        tenant_id="tenant-1",
        user_id="user-1",
        plan_id="pro",
        state=EntitlementState.SUSPENDED,
        valid_until=now + timedelta(days=30),
        paid_provider_allowed=False,
        now=now + timedelta(minutes=1),
    )
    with pytest.raises(CommercialAccessError, match="not active"):
        store.require_access(tenant_id="tenant-1", user_id="user-1", now=now)

    store.apply_entitlement(
        event_id="evt-cancel",
        tenant_id="tenant-1",
        user_id="user-1",
        plan_id="pro",
        state=EntitlementState.CANCELLED,
        valid_until=now + timedelta(days=30),
        paid_provider_allowed=False,
        now=now + timedelta(minutes=2),
    )
    with pytest.raises(CommercialAccessError, match="not active"):
        store.require_access(tenant_id="tenant-1", user_id="user-1", now=now)

    store.apply_entitlement(
        event_id="evt-expired",
        tenant_id="tenant-1",
        user_id="user-1",
        plan_id="pro",
        state=EntitlementState.ACTIVE,
        valid_until=now - timedelta(seconds=1),
        paid_provider_allowed=False,
        now=now + timedelta(minutes=3),
    )
    with pytest.raises(CommercialAccessError, match="expired"):
        store.require_access(tenant_id="tenant-1", user_id="user-1", now=now)


def test_paid_provider_requires_entitlement_permission(tmp_path: Path) -> None:
    store, _ = _store(tmp_path)
    now = datetime(2026, 8, 17, tzinfo=timezone.utc)
    _activate(store, now, paid_provider_allowed=False)

    with pytest.raises(CommercialAccessError, match="does not authorize paid providers"):
        store.require_access(
            tenant_id="tenant-1",
            user_id="user-1",
            now=now,
            paid_provider=True,
        )


def test_paid_provider_reserve_settle_uses_canonical_credit_ledger(
    tmp_path: Path,
) -> None:
    store, credits = _store(tmp_path)
    now = datetime(2026, 8, 17, tzinfo=timezone.utc)
    _activate(store, now, paid_provider_allowed=True)
    store.seed_credit_account(
        ManagedCreditAccount(
            tenant_id="tenant-1",
            user_id="user-1",
            available_microusd=1_000_000,
        )
    )
    quote = ProviderCostQuote(
        provider_name="provider-a",
        model_id="model-a",
        estimated_cost_microusd=200_000,
        max_cost_microusd=300_000,
    )

    reserved = store.reserve_provider_spend(
        tenant_id="tenant-1",
        user_id="user-1",
        now=now,
        request_id="request-1",
        routing_decision_id="route-1",
        quote=quote,
    )
    repeated = store.reserve_provider_spend(
        tenant_id="tenant-1",
        user_id="user-1",
        now=now,
        request_id="request-1",
        routing_decision_id="route-1",
        quote=quote,
    )

    assert repeated.authorization.authorization_id == reserved.authorization.authorization_id
    account = credits.get_account(tenant_id="tenant-1", user_id="user-1")
    assert account.available_microusd == 700_000
    assert account.reserved_microusd == 300_000

    settled = store.settle_provider_spend(
        authorization_id=reserved.authorization.authorization_id,
        actual_cost_microusd=125_000,
        provider_job_id="provider-job-1",
    )
    assert settled.account.available_microusd == 875_000
    assert settled.account.reserved_microusd == 0


def test_insufficient_credit_fails_closed(tmp_path: Path) -> None:
    store, _ = _store(tmp_path)
    now = datetime(2026, 8, 17, tzinfo=timezone.utc)
    _activate(store, now, paid_provider_allowed=True)
    store.seed_credit_account(
        ManagedCreditAccount(
            tenant_id="tenant-1",
            user_id="user-1",
            available_microusd=10,
        )
    )

    with pytest.raises(CommercialAccessError, match="insufficient"):
        store.reserve_provider_spend(
            tenant_id="tenant-1",
            user_id="user-1",
            now=now,
            request_id="request-expensive",
            routing_decision_id="route-expensive",
            quote=ProviderCostQuote(
                provider_name="provider-a",
                model_id="model-a",
                estimated_cost_microusd=20,
                max_cost_microusd=30,
            ),
        )


def test_unused_provider_reservation_can_be_released(tmp_path: Path) -> None:
    store, credits = _store(tmp_path)
    now = datetime(2026, 8, 17, tzinfo=timezone.utc)
    _activate(store, now, paid_provider_allowed=True)
    store.seed_credit_account(
        ManagedCreditAccount(
            tenant_id="tenant-1",
            user_id="user-1",
            available_microusd=100,
        )
    )
    reserved = store.reserve_provider_spend(
        tenant_id="tenant-1",
        user_id="user-1",
        now=now,
        request_id="request-release",
        routing_decision_id="route-release",
        quote=ProviderCostQuote("provider-a", "model-a", 20, 40),
    )

    released = store.release_provider_spend(
        authorization_id=reserved.authorization.authorization_id
    )

    assert released.available_microusd == 100
    assert released.reserved_microusd == 0
    assert credits.get_account(tenant_id="tenant-1", user_id="user-1") == released
