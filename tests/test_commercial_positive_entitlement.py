from __future__ import annotations

import inspect
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

NOW = datetime(2026, 8, 28, 6, 0, tzinfo=timezone.utc)


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
    event_type: str = "subscription.activated",
    *,
    minute: int = 1,
    provider_subscription_id: str = "sub-provider-1",
    payload_sha256: str | None = None,
) -> VerifiedCommercialWebhookEvent:
    occurred_at = NOW + timedelta(minutes=minute)
    return VerifiedCommercialWebhookEvent(
        event_id=event_id,
        event_type=event_type,
        provider_subscription_id=provider_subscription_id,
        occurred_at=occurred_at,
        payload_sha256=payload_sha256 or event_id.encode("utf-8").hex().ljust(64, "0")[:64],
        signature_timestamp=occurred_at,
    )


def _bind_and_grant(
    access: IdentityBoundCommercialAccess,
    *,
    grant_id: str = "grant-1",
    provider_subscription_id: str = "sub-provider-1",
    period_start: datetime = NOW,
    period_end: datetime = NOW + timedelta(days=30),
    paid_provider_allowed: bool = True,
) -> None:
    access.create_provider_subscription_binding(
        provider_subscription_id=provider_subscription_id,
        tenant_id="tenant-1",
        user_id="user-1",
        plan_id="pro",
        now=NOW,
    )
    access.create_trusted_grant(
        grant_id=grant_id,
        provider_subscription_id=provider_subscription_id,
        period_start=period_start,
        period_end=period_end,
        paid_provider_allowed=paid_provider_allowed,
        now=NOW,
    )


def test_positive_activation_uses_trusted_grant_authority(tmp_path: Path) -> None:
    access, commercial, _ = _access(tmp_path)
    period_end = NOW + timedelta(days=30)
    _bind_and_grant(access, period_end=period_end, paid_provider_allowed=True)

    binding, entitlement = access.activate_from_trusted_grant(
        event=_event("evt-active"),
        now=NOW + timedelta(minutes=1),
    )

    assert binding.state is ProviderSubscriptionState.ACTIVE
    assert entitlement.state is EntitlementState.ACTIVE
    assert entitlement.tenant_id == "tenant-1"
    assert entitlement.user_id == "user-1"
    assert entitlement.plan_id == "pro"
    assert entitlement.valid_until == period_end
    assert entitlement.paid_provider_allowed is True
    assert commercial.get_entitlement(tenant_id="tenant-1", user_id="user-1") == entitlement


def test_missing_current_grant_fails_before_positive_projection(tmp_path: Path) -> None:
    access, commercial, _ = _access(tmp_path)
    access.create_provider_subscription_binding(
        provider_subscription_id="sub-provider-1",
        tenant_id="tenant-1",
        user_id="user-1",
        plan_id="pro",
        now=NOW,
    )

    with pytest.raises(CommercialAccessError, match="current trusted commercial grant"):
        access.activate_from_trusted_grant(
            event=_event("evt-active"),
            now=NOW + timedelta(minutes=1),
        )

    binding = commercial.get_provider_subscription_binding(
        provider_subscription_id="sub-provider-1"
    )
    assert binding.state is ProviderSubscriptionState.PENDING
    with pytest.raises(CommercialAccessError, match="does not exist"):
        commercial.get_entitlement(tenant_id="tenant-1", user_id="user-1")


def test_not_yet_valid_and_expired_grants_fail_closed(tmp_path: Path) -> None:
    access, commercial, _ = _access(tmp_path)
    _bind_and_grant(
        access,
        period_start=NOW + timedelta(hours=1),
        period_end=NOW + timedelta(days=1),
    )

    with pytest.raises(CommercialAccessError, match="current trusted commercial grant"):
        access.activate_from_trusted_grant(
            event=_event("evt-too-early"),
            now=NOW + timedelta(minutes=1),
        )
    with pytest.raises(CommercialAccessError, match="current trusted commercial grant"):
        access.activate_from_trusted_grant(
            event=_event("evt-expired", minute=60 * 24 + 1),
            now=NOW + timedelta(days=1, minutes=1),
        )

    with pytest.raises(CommercialAccessError, match="does not exist"):
        commercial.get_entitlement(tenant_id="tenant-1", user_id="user-1")


def test_overlapping_current_grants_fail_closed_as_ambiguous(tmp_path: Path) -> None:
    access, commercial, _ = _access(tmp_path)
    _bind_and_grant(access, grant_id="grant-1")
    access.create_trusted_grant(
        grant_id="grant-2",
        provider_subscription_id="sub-provider-1",
        period_start=NOW,
        period_end=NOW + timedelta(days=10),
        paid_provider_allowed=False,
        now=NOW,
    )

    with pytest.raises(CommercialAccessError, match="ambiguous"):
        access.activate_from_trusted_grant(
            event=_event("evt-ambiguous"),
            now=NOW + timedelta(minutes=1),
        )

    binding = commercial.get_provider_subscription_binding(
        provider_subscription_id="sub-provider-1"
    )
    assert binding.state is ProviderSubscriptionState.PENDING
    with pytest.raises(CommercialAccessError, match="does not exist"):
        commercial.get_entitlement(tenant_id="tenant-1", user_id="user-1")


def test_inactive_identity_cannot_receive_active_entitlement(tmp_path: Path) -> None:
    access, commercial, database = _access(tmp_path)
    _bind_and_grant(access)
    with sqlite3.connect(database) as connection:
        connection.execute("UPDATE identity_users SET enabled = 0 WHERE user_id = 'user-1'")

    with pytest.raises(CommercialAccessError, match="membership is not active"):
        access.activate_from_trusted_grant(
            event=_event("evt-inactive"),
            now=NOW + timedelta(minutes=1),
        )

    binding = commercial.get_provider_subscription_binding(
        provider_subscription_id="sub-provider-1"
    )
    assert binding.state is ProviderSubscriptionState.ACTIVE
    with pytest.raises(CommercialAccessError, match="does not exist"):
        commercial.get_entitlement(tenant_id="tenant-1", user_id="user-1")


def test_event_for_ungranted_subscription_cannot_activate(tmp_path: Path) -> None:
    access, commercial, _ = _access(tmp_path)
    _bind_and_grant(access)
    access.create_provider_subscription_binding(
        provider_subscription_id="sub-provider-2",
        tenant_id="tenant-1",
        user_id="user-1",
        plan_id="pro",
        now=NOW,
    )

    with pytest.raises(CommercialAccessError, match="current trusted commercial grant"):
        access.activate_from_trusted_grant(
            event=_event("evt-wrong-sub", provider_subscription_id="sub-provider-2"),
            now=NOW + timedelta(minutes=1),
        )

    wrong_binding = commercial.get_provider_subscription_binding(
        provider_subscription_id="sub-provider-2"
    )
    assert wrong_binding.state is ProviderSubscriptionState.PENDING


def test_provider_event_lineage_is_idempotent_and_conflicts_fail_closed(tmp_path: Path) -> None:
    access, commercial, _ = _access(tmp_path)
    _bind_and_grant(access)
    event = _event("evt-replay")

    _, first = access.activate_from_trusted_grant(
        event=event,
        now=NOW + timedelta(minutes=1),
    )
    _, replayed = access.activate_from_trusted_grant(
        event=event,
        now=NOW + timedelta(minutes=2),
    )

    assert replayed == first
    assert replayed.version == 1

    conflicting = _event(
        "evt-replay",
        event_type="subscription.renewed",
        minute=3,
        payload_sha256="f" * 64,
    )
    with pytest.raises(CommercialAccessError, match="event_id conflicts"):
        access.activate_from_trusted_grant(
            event=conflicting,
            now=NOW + timedelta(minutes=3),
        )
    assert commercial.get_entitlement(tenant_id="tenant-1", user_id="user-1") == first


def test_out_of_order_activation_cannot_reverse_newer_cancellation(tmp_path: Path) -> None:
    access, commercial, _ = _access(tmp_path)
    _bind_and_grant(access)
    _, cancelled = access.reconcile_verified_provider_entitlement(
        event=_event("evt-cancel", "subscription.cancelled", minute=5),
        now=NOW + timedelta(minutes=5),
    )
    assert cancelled is not None
    assert cancelled.state is EntitlementState.CANCELLED

    with pytest.raises(CommercialAccessError, match="out of order"):
        access.activate_from_trusted_grant(
            event=_event("evt-old-active", minute=4),
            now=NOW + timedelta(minutes=6),
        )

    stored = commercial.get_entitlement(tenant_id="tenant-1", user_id="user-1")
    assert stored.state is EntitlementState.CANCELLED
    assert stored.paid_provider_allowed is False


def test_positive_projection_exposes_no_canonical_period_or_grant_caller_authority() -> None:
    parameters = inspect.signature(
        IdentityBoundCommercialAccess.activate_from_trusted_grant
    ).parameters

    assert "grant_id" not in parameters
    assert "tenant_id" not in parameters
    assert "user_id" not in parameters
    assert "plan_id" not in parameters
    assert "period_start" not in parameters
    assert "period_end" not in parameters
    assert "paid_provider_allowed" not in parameters


def test_paid_provider_policy_comes_only_from_trusted_grant(tmp_path: Path) -> None:
    access, _, _ = _access(tmp_path)
    _bind_and_grant(access, paid_provider_allowed=False)

    _, entitlement = access.activate_from_trusted_grant(
        event=_event("evt-free-policy"),
        now=NOW + timedelta(minutes=1),
    )

    assert entitlement.state is EntitlementState.ACTIVE
    assert entitlement.paid_provider_allowed is False


def test_future_provider_event_cannot_activate_entitlement(tmp_path: Path) -> None:
    access, commercial, _ = _access(tmp_path)
    _bind_and_grant(access)

    with pytest.raises(CommercialAccessError, match="cannot occur in the future"):
        access.activate_from_trusted_grant(
            event=_event("evt-future", minute=5),
            now=NOW + timedelta(minutes=1),
        )

    binding = commercial.get_provider_subscription_binding(
        provider_subscription_id="sub-provider-1"
    )
    assert binding.state is ProviderSubscriptionState.PENDING


def test_unverified_positive_event_cannot_activate_entitlement(tmp_path: Path) -> None:
    access, commercial, _ = _access(tmp_path)
    _bind_and_grant(access)

    class FakeEvent:
        event_type = "subscription.activated"

    with pytest.raises(CommercialAccessError, match="cryptographically verified"):
        access.activate_from_trusted_grant(
            event=FakeEvent(),
            now=NOW + timedelta(minutes=1),
        )
    with pytest.raises(CommercialAccessError, match="does not exist"):
        commercial.get_entitlement(tenant_id="tenant-1", user_id="user-1")
