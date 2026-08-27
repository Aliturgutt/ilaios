"""Server-owned commercial subscription binding for verified webhook events.

This module composes the existing signed webhook verifier with canonical ILAIOS
commercial entitlement authority. Provider webhook payloads never select canonical
user, tenant, or plan identity. A durable server-side binding created from a trusted
checkout/admin boundary maps one provider subscription identifier to canonical
ILAIOS identity before any entitlement mutation can occur.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Protocol, runtime_checkable

from services.commercial_access import CommercialAccessError, CommercialEntitlement, EntitlementState
from services.commercial_webhook import CommercialWebhookVerifier, VerifiedCommercialWebhookEvent


_SCHEMA = """
CREATE TABLE IF NOT EXISTS commercial_subscription_bindings (
 provider_subscription_id TEXT PRIMARY KEY,
 tenant_id TEXT NOT NULL,
 user_id TEXT NOT NULL,
 plan_id TEXT NOT NULL,
 created_at TEXT NOT NULL
);
"""


@dataclass(frozen=True, slots=True)
class CommercialSubscriptionBinding:
    provider_subscription_id: str
    tenant_id: str
    user_id: str
    plan_id: str

    def __post_init__(self) -> None:
        for name in ("provider_subscription_id", "tenant_id", "user_id", "plan_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value or value != value.strip():
                raise CommercialAccessError(f"{name} must be non-blank and trimmed")


@runtime_checkable
class CommercialEntitlementAuthority(Protocol):
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
    ) -> CommercialEntitlement: ...


class CommercialSubscriptionBindingStore:
    """Durably map external subscription IDs to server-owned canonical identity."""

    def __init__(self, root: Path) -> None:
        root.mkdir(parents=True, exist_ok=True)
        self._database = root / "commercial_subscription_bindings.sqlite3"
        with self._connect() as connection:
            connection.executescript(_SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def bind(
        self,
        *,
        provider_subscription_id: str,
        tenant_id: str,
        user_id: str,
        plan_id: str,
        now: datetime,
    ) -> CommercialSubscriptionBinding:
        binding = CommercialSubscriptionBinding(
            provider_subscription_id=provider_subscription_id,
            tenant_id=tenant_id,
            user_id=user_id,
            plan_id=plan_id,
        )
        _require_time("now", now)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                "SELECT provider_subscription_id,tenant_id,user_id,plan_id "
                "FROM commercial_subscription_bindings WHERE provider_subscription_id = ?",
                (binding.provider_subscription_id,),
            ).fetchone()
            if existing is not None:
                current = _binding_from_row(existing)
                if current != binding:
                    raise CommercialAccessError(
                        "provider subscription is already bound to different canonical identity"
                    )
                return current
            connection.execute(
                "INSERT INTO commercial_subscription_bindings "
                "(provider_subscription_id,tenant_id,user_id,plan_id,created_at) "
                "VALUES (?,?,?,?,?)",
                (
                    binding.provider_subscription_id,
                    binding.tenant_id,
                    binding.user_id,
                    binding.plan_id,
                    now.isoformat(),
                ),
            )
        return binding

    def resolve(self, *, provider_subscription_id: str) -> CommercialSubscriptionBinding:
        _require_text("provider_subscription_id", provider_subscription_id)
        with self._connect() as connection:
            row = connection.execute(
                "SELECT provider_subscription_id,tenant_id,user_id,plan_id "
                "FROM commercial_subscription_bindings WHERE provider_subscription_id = ?",
                (provider_subscription_id,),
            ).fetchone()
        if row is None:
            raise CommercialAccessError("provider subscription is not bound to canonical identity")
        return _binding_from_row(row)


class CommercialWebhookEntitlementProcessor:
    """Verify one provider event, resolve canonical binding, then apply entitlement."""

    def __init__(
        self,
        *,
        verifier: CommercialWebhookVerifier,
        bindings: CommercialSubscriptionBindingStore,
        commercial_access: CommercialEntitlementAuthority,
    ) -> None:
        if not isinstance(verifier, CommercialWebhookVerifier):
            raise CommercialAccessError("commercial webhook verifier is required")
        if not isinstance(commercial_access, CommercialEntitlementAuthority):
            raise CommercialAccessError("commercial entitlement authority is required")
        self._verifier = verifier
        self._bindings = bindings
        self._commercial_access = commercial_access

    def ingest(
        self,
        *,
        raw_body: bytes,
        signature_header: str,
        now: datetime,
    ) -> CommercialEntitlement:
        _require_time("now", now)
        event = self._verifier.verify(
            raw_body=raw_body,
            signature_header=signature_header,
            now=now,
        )
        if not isinstance(event, VerifiedCommercialWebhookEvent):
            raise CommercialAccessError("commercial webhook verifier returned invalid evidence")
        if event.occurred_at > now:
            raise CommercialAccessError("commercial webhook event occurred_at is in the future")

        binding = self._bindings.resolve(
            provider_subscription_id=event.provider_subscription_id
        )
        state = _entitlement_state(event.event_type)
        paid_provider_allowed = state is EntitlementState.ACTIVE
        event_id = f"commercial:{event.provider_subscription_id}:{event.event_id}"
        return self._commercial_access.apply_entitlement(
            event_id=event_id,
            tenant_id=binding.tenant_id,
            user_id=binding.user_id,
            plan_id=binding.plan_id,
            state=state,
            valid_until=None,
            paid_provider_allowed=paid_provider_allowed,
            now=now,
        )


def _entitlement_state(event_type: str) -> EntitlementState:
    if event_type in {"subscription.activated", "subscription.renewed"}:
        return EntitlementState.ACTIVE
    if event_type in {"subscription.suspended", "payment.failed"}:
        return EntitlementState.SUSPENDED
    if event_type in {"subscription.cancelled", "payment.refunded"}:
        return EntitlementState.CANCELLED
    raise CommercialAccessError("commercial webhook event type is unsupported")


def _binding_from_row(row: sqlite3.Row) -> CommercialSubscriptionBinding:
    return CommercialSubscriptionBinding(
        provider_subscription_id=str(row["provider_subscription_id"]),
        tenant_id=str(row["tenant_id"]),
        user_id=str(row["user_id"]),
        plan_id=str(row["plan_id"]),
    )


def _require_text(name: str, value: str) -> None:
    if not isinstance(value, str) or not value or value != value.strip():
        raise CommercialAccessError(f"{name} must be non-blank and trimmed")


def _require_time(name: str, value: datetime) -> None:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise CommercialAccessError(f"{name} must be timezone-aware")


__all__ = [
    "CommercialEntitlementAuthority",
    "CommercialSubscriptionBinding",
    "CommercialSubscriptionBindingStore",
    "CommercialWebhookEntitlementProcessor",
]
