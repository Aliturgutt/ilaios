"""Bind commercial entitlement admission to canonical ILAIOS identity persistence.

This composition layer does not create a second billing, identity, credit, or audit
authority. It reuses ``CommercialAccessStore`` for entitlement/credit behavior and
reads the canonical control-plane identity tables only to fail closed when the
requested user/tenant membership is not currently active.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

from services.commercial_access import (
    CommercialAccessError,
    CommercialAccessStore,
    CommercialEntitlement,
    EntitlementState,
    ProviderSubscriptionBinding,
)
from services.commercial_webhook import VerifiedCommercialWebhookEvent
from services.control_plane.migrations import migrate_database
from src.video_automation.managed_credits import (
    CreditAuthorizationOutcome,
    CreditSettlementOutcome,
    ManagedCreditAccount,
    ProviderCostQuote,
)


class IdentityBoundCommercialAccess:
    """Fail-closed composition of canonical identity and commercial access."""

    def __init__(self, identity_database: Path, commercial: CommercialAccessStore) -> None:
        self._identity_database = identity_database
        self._commercial = commercial
        if migrate_database(identity_database) < 9:
            raise CommercialAccessError("commercial identity schema is unavailable")

    def create_provider_subscription_binding(
        self,
        *,
        provider_subscription_id: str,
        tenant_id: str,
        user_id: str,
        plan_id: str,
        now: datetime,
    ) -> ProviderSubscriptionBinding:
        """Create a trusted binding only for an active canonical membership."""

        self._require_active_identity(tenant_id=tenant_id, user_id=user_id)
        return self._commercial.create_provider_subscription_binding(
            provider_subscription_id=provider_subscription_id,
            tenant_id=tenant_id,
            user_id=user_id,
            plan_id=plan_id,
            now=now,
        )

    def apply_verified_provider_event(
        self, *, event: object, now: datetime
    ) -> ProviderSubscriptionBinding:
        """Apply verified provider state without allowing webhook account selection."""

        if not isinstance(event, VerifiedCommercialWebhookEvent):
            raise CommercialAccessError("provider event must be cryptographically verified")
        binding = self._commercial.get_provider_subscription_binding(
            provider_subscription_id=event.provider_subscription_id
        )
        self._require_active_identity(tenant_id=binding.tenant_id, user_id=binding.user_id)
        return self._commercial.apply_verified_provider_event(event=event, now=now)

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
        """Apply entitlement only to an active canonical tenant membership."""

        self._require_active_identity(tenant_id=tenant_id, user_id=user_id)
        return self._commercial.apply_entitlement(
            event_id=event_id,
            tenant_id=tenant_id,
            user_id=user_id,
            plan_id=plan_id,
            state=state,
            valid_until=valid_until,
            paid_provider_allowed=paid_provider_allowed,
            now=now,
        )

    def require_access(
        self,
        *,
        tenant_id: str,
        user_id: str,
        now: datetime,
        paid_provider: bool = False,
    ) -> CommercialEntitlement:
        """Revalidate identity before every commercial admission decision."""

        self._require_active_identity(tenant_id=tenant_id, user_id=user_id)
        return self._commercial.require_access(
            tenant_id=tenant_id,
            user_id=user_id,
            now=now,
            paid_provider=paid_provider,
        )

    def seed_credit_account(self, account: ManagedCreditAccount) -> ManagedCreditAccount:
        """Prevent canonical credit accounts for inactive or foreign identities."""

        self._require_active_identity(tenant_id=account.tenant_id, user_id=account.user_id)
        return self._commercial.seed_credit_account(account)

    def reserve_provider_spend(
        self,
        *,
        tenant_id: str,
        user_id: str,
        now: datetime,
        request_id: str,
        routing_decision_id: str,
        quote: ProviderCostQuote,
    ) -> CreditAuthorizationOutcome:
        """Revalidate identity immediately before governed paid-provider reservation."""

        self._require_active_identity(tenant_id=tenant_id, user_id=user_id)
        return self._commercial.reserve_provider_spend(
            tenant_id=tenant_id,
            user_id=user_id,
            now=now,
            request_id=request_id,
            routing_decision_id=routing_decision_id,
            quote=quote,
        )

    def settle_provider_spend(
        self,
        *,
        authorization_id: str,
        actual_cost_microusd: int,
        provider_job_id: str,
    ) -> CreditSettlementOutcome:
        """Delegate settlement so in-flight spend can close after identity changes."""

        return self._commercial.settle_provider_spend(
            authorization_id=authorization_id,
            actual_cost_microusd=actual_cost_microusd,
            provider_job_id=provider_job_id,
        )

    def release_provider_spend(self, *, authorization_id: str) -> ManagedCreditAccount:
        """Delegate reservation release to the canonical managed-credit authority."""

        return self._commercial.release_provider_spend(authorization_id=authorization_id)

    def _require_active_identity(self, *, tenant_id: str, user_id: str) -> None:
        tenant = tenant_id.strip()
        user = user_id.strip()
        if not tenant or not user:
            raise CommercialAccessError("canonical user and tenant are required")
        with sqlite3.connect(self._identity_database) as connection:
            row = connection.execute(
                "SELECT u.enabled, t.status, m.status "
                "FROM identity_users AS u "
                "JOIN identity_memberships AS m ON m.user_id = u.user_id "
                "JOIN identity_tenants AS t ON t.tenant_id = m.tenant_id "
                "WHERE u.user_id = ? AND m.tenant_id = ?",
                (user, tenant),
            ).fetchone()
        if row is None:
            raise CommercialAccessError("canonical identity membership does not exist")
        if not bool(row[0]) or row[1] != "ACTIVE" or row[2] != "ACTIVE":
            raise CommercialAccessError("canonical identity membership is not active")
