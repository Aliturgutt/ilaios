"""Provider-neutral commercial entitlement boundary for ILAIOS.

This module owns subscription/entitlement state only. Provider pricing, credit
reservation, settlement, and duplicate-spend protection remain authoritative in
the existing managed-credit ledger. Payment collection is an external adapter
concern and cannot mint entitlement without an explicit durable event.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path

from src.video_automation.managed_credit_store import ManagedCreditLedgerStore
from src.video_automation.managed_credits import (
    CreditAuthorizationOutcome,
    CreditSettlementOutcome,
    ManagedCreditAccount,
    ManagedCreditError,
    ProviderCostQuote,
)


class CommercialAccessError(PermissionError):
    """Raised when commercial access cannot be proven or safely mutated."""


class EntitlementState(str, Enum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    CANCELLED = "CANCELLED"


class ProviderSubscriptionState(str, Enum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    CANCELLED = "CANCELLED"


MAX_TRUSTED_GRANT_DURATION = timedelta(days=370)


@dataclass(frozen=True, slots=True)
class CommercialEntitlement:
    tenant_id: str
    user_id: str
    plan_id: str
    state: EntitlementState
    valid_until: datetime | None
    paid_provider_allowed: bool
    version: int

    def __post_init__(self) -> None:
        for name in ("tenant_id", "user_id", "plan_id"):
            _require_text(name, getattr(self, name))
        if self.valid_until is not None and self.valid_until.tzinfo is None:
            raise CommercialAccessError("valid_until must be timezone-aware")
        if self.version < 1:
            raise CommercialAccessError("entitlement version must be positive")


@dataclass(frozen=True, slots=True)
class ProviderSubscriptionBinding:
    provider_subscription_id: str
    tenant_id: str
    user_id: str
    plan_id: str
    state: ProviderSubscriptionState
    created_at: datetime
    updated_at: datetime
    last_provider_event_at: datetime | None

    def __post_init__(self) -> None:
        for name in ("provider_subscription_id", "tenant_id", "user_id", "plan_id"):
            _require_text(name, getattr(self, name))
        _require_time("created_at", self.created_at)
        _require_time("updated_at", self.updated_at)
        if self.last_provider_event_at is not None:
            _require_time("last_provider_event_at", self.last_provider_event_at)
        if not isinstance(self.state, ProviderSubscriptionState):
            raise CommercialAccessError("provider subscription state is invalid")


@dataclass(frozen=True, slots=True)
class TrustedCommercialGrant:
    """Server-owned positive-entitlement policy evidence.

    Canonical account/plan coordinates are copied from the already-trusted provider
    subscription binding. Webhook/client payloads are never accepted as grant
    coordinate or validity authority.
    """

    grant_id: str
    version: int
    provider_subscription_id: str
    tenant_id: str
    user_id: str
    plan_id: str
    period_start: datetime
    period_end: datetime
    paid_provider_allowed: bool
    created_at: datetime

    def __post_init__(self) -> None:
        for name in (
            "grant_id",
            "provider_subscription_id",
            "tenant_id",
            "user_id",
            "plan_id",
        ):
            _require_text(name, getattr(self, name))
        if self.version < 1:
            raise CommercialAccessError("trusted grant version must be positive")
        _require_time("period_start", self.period_start)
        _require_time("period_end", self.period_end)
        _require_time("created_at", self.created_at)
        if not isinstance(self.paid_provider_allowed, bool):
            raise CommercialAccessError("paid_provider_allowed must be boolean")


_SCHEMA = """
CREATE TABLE IF NOT EXISTS commercial_entitlements (
 tenant_id TEXT NOT NULL,
 user_id TEXT NOT NULL,
 plan_id TEXT NOT NULL,
 state TEXT NOT NULL,
 valid_until TEXT,
 paid_provider_allowed INTEGER NOT NULL CHECK (paid_provider_allowed IN (0, 1)),
 version INTEGER NOT NULL CHECK (version >= 1),
 updated_at TEXT NOT NULL,
 PRIMARY KEY (tenant_id, user_id)
);
CREATE TABLE IF NOT EXISTS commercial_entitlement_events (
 event_id TEXT PRIMARY KEY,
 tenant_id TEXT NOT NULL,
 user_id TEXT NOT NULL,
 payload_sha256 TEXT NOT NULL,
 snapshot_json TEXT NOT NULL,
 applied_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS commercial_provider_subscriptions (
 provider_subscription_id TEXT PRIMARY KEY,
 tenant_id TEXT NOT NULL,
 user_id TEXT NOT NULL,
 plan_id TEXT NOT NULL,
 state TEXT NOT NULL,
 created_at TEXT NOT NULL,
 updated_at TEXT NOT NULL,
 last_provider_event_at TEXT
);
CREATE TABLE IF NOT EXISTS commercial_provider_events (
 provider_event_id TEXT PRIMARY KEY,
 provider_subscription_id TEXT NOT NULL,
 event_type TEXT NOT NULL,
 payload_sha256 TEXT NOT NULL,
 snapshot_json TEXT NOT NULL,
 applied_at TEXT NOT NULL,
 FOREIGN KEY(provider_subscription_id)
   REFERENCES commercial_provider_subscriptions(provider_subscription_id)
);
CREATE TABLE IF NOT EXISTS commercial_trusted_grants (
 grant_id TEXT PRIMARY KEY,
 version INTEGER NOT NULL CHECK (version >= 1),
 provider_subscription_id TEXT NOT NULL,
 tenant_id TEXT NOT NULL,
 user_id TEXT NOT NULL,
 plan_id TEXT NOT NULL,
 period_start TEXT NOT NULL,
 period_end TEXT NOT NULL,
 paid_provider_allowed INTEGER NOT NULL CHECK (paid_provider_allowed IN (0, 1)),
 payload_sha256 TEXT NOT NULL,
 created_at TEXT NOT NULL,
 FOREIGN KEY(provider_subscription_id)
   REFERENCES commercial_provider_subscriptions(provider_subscription_id)
);
CREATE INDEX IF NOT EXISTS commercial_trusted_grants_subscription_idx
 ON commercial_trusted_grants(provider_subscription_id, period_end);
"""

_PROVIDER_EVENT_STATES = {
    "subscription.activated": ProviderSubscriptionState.ACTIVE,
    "subscription.renewed": ProviderSubscriptionState.ACTIVE,
    "subscription.suspended": ProviderSubscriptionState.SUSPENDED,
    "payment.failed": ProviderSubscriptionState.SUSPENDED,
    "subscription.cancelled": ProviderSubscriptionState.CANCELLED,
    "payment.refunded": ProviderSubscriptionState.CANCELLED,
}


class CommercialAccessStore:
    """Durable entitlement admission composed with the canonical credit ledger."""

    def __init__(self, root: Path, credits: ManagedCreditLedgerStore) -> None:
        root.mkdir(parents=True, exist_ok=True)
        self._database = root / "commercial_access.sqlite3"
        self._credits = credits
        with self._connect() as connection:
            connection.executescript(_SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def create_provider_subscription_binding(
        self,
        *,
        provider_subscription_id: str,
        tenant_id: str,
        user_id: str,
        plan_id: str,
        now: datetime,
    ) -> ProviderSubscriptionBinding:
        for name, value in (
            ("provider_subscription_id", provider_subscription_id),
            ("tenant_id", tenant_id),
            ("user_id", user_id),
            ("plan_id", plan_id),
        ):
            _require_text(name, value)
        _require_time("now", now)
        candidate = ProviderSubscriptionBinding(
            provider_subscription_id=provider_subscription_id,
            tenant_id=tenant_id,
            user_id=user_id,
            plan_id=plan_id,
            state=ProviderSubscriptionState.PENDING,
            created_at=now,
            updated_at=now,
            last_provider_event_at=None,
        )
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                "SELECT * FROM commercial_provider_subscriptions WHERE provider_subscription_id = ?",
                (provider_subscription_id,),
            ).fetchone()
            if existing is not None:
                stored = _provider_binding_from_row(existing)
                if (
                    stored.tenant_id != tenant_id
                    or stored.user_id != user_id
                    or stored.plan_id != plan_id
                ):
                    raise CommercialAccessError(
                        "provider subscription conflicts with canonical binding"
                    )
                return stored
            connection.execute(
                "INSERT INTO commercial_provider_subscriptions "
                "(provider_subscription_id,tenant_id,user_id,plan_id,state,created_at,updated_at,last_provider_event_at) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (
                    candidate.provider_subscription_id,
                    candidate.tenant_id,
                    candidate.user_id,
                    candidate.plan_id,
                    candidate.state.value,
                    candidate.created_at.isoformat(),
                    candidate.updated_at.isoformat(),
                    None,
                ),
            )
        return candidate

    def get_provider_subscription_binding(
        self, *, provider_subscription_id: str
    ) -> ProviderSubscriptionBinding:
        _require_text("provider_subscription_id", provider_subscription_id)
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM commercial_provider_subscriptions WHERE provider_subscription_id = ?",
                (provider_subscription_id,),
            ).fetchone()
        if row is None:
            raise CommercialAccessError("provider subscription binding does not exist")
        return _provider_binding_from_row(row)

    def create_trusted_grant(
        self,
        *,
        grant_id: str,
        provider_subscription_id: str,
        period_start: datetime,
        period_end: datetime,
        paid_provider_allowed: bool,
        now: datetime,
    ) -> TrustedCommercialGrant:
        """Persist server-owned policy evidence without mutating entitlement.

        Canonical tenant/user/plan are loaded exclusively from the existing trusted
        provider-subscription binding. This API intentionally exposes no parameters
        that allow webhook/client callers to select those coordinates.
        """

        _require_text("grant_id", grant_id)
        _require_text("provider_subscription_id", provider_subscription_id)
        _require_time("period_start", period_start)
        _require_time("period_end", period_end)
        _require_time("now", now)
        if not isinstance(paid_provider_allowed, bool):
            raise CommercialAccessError("paid_provider_allowed must be boolean")
        if period_end <= period_start:
            raise CommercialAccessError("trusted grant period must end after it starts")
        if period_end <= now:
            raise CommercialAccessError("trusted grant period is already expired")
        if period_end - period_start > MAX_TRUSTED_GRANT_DURATION:
            raise CommercialAccessError("trusted grant period exceeds policy maximum")

        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            binding_row = connection.execute(
                "SELECT * FROM commercial_provider_subscriptions WHERE provider_subscription_id = ?",
                (provider_subscription_id,),
            ).fetchone()
            if binding_row is None:
                raise CommercialAccessError("provider subscription binding does not exist")
            binding = _provider_binding_from_row(binding_row)
            payload = _trusted_grant_payload(
                provider_subscription_id=provider_subscription_id,
                tenant_id=binding.tenant_id,
                user_id=binding.user_id,
                plan_id=binding.plan_id,
                period_start=period_start,
                period_end=period_end,
                paid_provider_allowed=paid_provider_allowed,
            )
            payload_sha256 = hashlib.sha256(payload.encode("utf-8")).hexdigest()
            existing = connection.execute(
                "SELECT * FROM commercial_trusted_grants WHERE grant_id = ?",
                (grant_id,),
            ).fetchone()
            if existing is not None:
                if str(existing["payload_sha256"]) != payload_sha256:
                    raise CommercialAccessError(
                        "trusted grant_id conflicts with different policy content"
                    )
                return _trusted_grant_from_row(existing)
            grant = TrustedCommercialGrant(
                grant_id=grant_id,
                version=1,
                provider_subscription_id=provider_subscription_id,
                tenant_id=binding.tenant_id,
                user_id=binding.user_id,
                plan_id=binding.plan_id,
                period_start=period_start,
                period_end=period_end,
                paid_provider_allowed=paid_provider_allowed,
                created_at=now,
            )
            connection.execute(
                "INSERT INTO commercial_trusted_grants "
                "(grant_id,version,provider_subscription_id,tenant_id,user_id,plan_id,period_start,period_end,"
                "paid_provider_allowed,payload_sha256,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (
                    grant.grant_id,
                    grant.version,
                    grant.provider_subscription_id,
                    grant.tenant_id,
                    grant.user_id,
                    grant.plan_id,
                    grant.period_start.isoformat(),
                    grant.period_end.isoformat(),
                    int(grant.paid_provider_allowed),
                    payload_sha256,
                    grant.created_at.isoformat(),
                ),
            )
        return grant

    def get_trusted_grant(self, *, grant_id: str) -> TrustedCommercialGrant:
        _require_text("grant_id", grant_id)
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM commercial_trusted_grants WHERE grant_id = ?",
                (grant_id,),
            ).fetchone()
        if row is None:
            raise CommercialAccessError("trusted commercial grant does not exist")
        return _trusted_grant_from_row(row)

    def resolve_trusted_grant(
        self, *, provider_subscription_id: str, now: datetime
    ) -> TrustedCommercialGrant:
        """Resolve exactly one current server-owned grant for a trusted subscription.

        The positive projection caller cannot select a grant ID, billing period, plan,
        or paid-provider policy. Multiple overlapping current grants are ambiguous and
        therefore fail closed instead of allowing caller-controlled policy selection.
        """

        _require_text("provider_subscription_id", provider_subscription_id)
        _require_time("now", now)
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM commercial_trusted_grants WHERE provider_subscription_id = ?",
                (provider_subscription_id,),
            ).fetchall()
        matches = [
            grant
            for grant in (_trusted_grant_from_row(row) for row in rows)
            if grant.period_start <= now < grant.period_end
        ]
        if not matches:
            raise CommercialAccessError("current trusted commercial grant does not exist")
        if len(matches) != 1:
            raise CommercialAccessError("current trusted commercial grant is ambiguous")
        return matches[0]

    def apply_verified_provider_event(
        self, *, event: object, now: datetime
    ) -> ProviderSubscriptionBinding:
        from services.commercial_webhook import VerifiedCommercialWebhookEvent

        if not isinstance(event, VerifiedCommercialWebhookEvent):
            raise CommercialAccessError("provider event must be cryptographically verified")
        _require_time("now", now)
        state = _PROVIDER_EVENT_STATES.get(event.event_type)
        if state is None:
            raise CommercialAccessError("provider subscription event type is unsupported")
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing_event = connection.execute(
                "SELECT payload_sha256, provider_subscription_id, event_type, snapshot_json "
                "FROM commercial_provider_events WHERE provider_event_id = ?",
                (event.event_id,),
            ).fetchone()
            if existing_event is not None:
                if (
                    str(existing_event["payload_sha256"]) != event.payload_sha256
                    or str(existing_event["provider_subscription_id"])
                    != event.provider_subscription_id
                    or str(existing_event["event_type"]) != event.event_type
                ):
                    raise CommercialAccessError(
                        "provider event_id conflicts with different verified content"
                    )
                return _provider_binding_from_json(str(existing_event["snapshot_json"]))
            row = connection.execute(
                "SELECT * FROM commercial_provider_subscriptions WHERE provider_subscription_id = ?",
                (event.provider_subscription_id,),
            ).fetchone()
            if row is None:
                raise CommercialAccessError("provider subscription binding does not exist")
            binding = _provider_binding_from_row(row)
            if (
                binding.last_provider_event_at is not None
                and event.occurred_at <= binding.last_provider_event_at
            ):
                raise CommercialAccessError("provider subscription event is out of order")
            updated = ProviderSubscriptionBinding(
                provider_subscription_id=binding.provider_subscription_id,
                tenant_id=binding.tenant_id,
                user_id=binding.user_id,
                plan_id=binding.plan_id,
                state=state,
                created_at=binding.created_at,
                updated_at=now,
                last_provider_event_at=event.occurred_at,
            )
            connection.execute(
                "UPDATE commercial_provider_subscriptions SET state = ?, updated_at = ?, "
                "last_provider_event_at = ? WHERE provider_subscription_id = ?",
                (
                    updated.state.value,
                    updated.updated_at.isoformat(),
                    event.occurred_at.isoformat(),
                    updated.provider_subscription_id,
                ),
            )
            snapshot = _provider_binding_json(updated)
            connection.execute(
                "INSERT INTO commercial_provider_events "
                "(provider_event_id,provider_subscription_id,event_type,payload_sha256,snapshot_json,applied_at) "
                "VALUES (?,?,?,?,?,?)",
                (
                    event.event_id,
                    event.provider_subscription_id,
                    event.event_type,
                    event.payload_sha256,
                    snapshot,
                    now.isoformat(),
                ),
            )
        return updated

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
        _require_text("event_id", event_id)
        for name, value in (
            ("tenant_id", tenant_id),
            ("user_id", user_id),
            ("plan_id", plan_id),
        ):
            _require_text(name, value)
        _require_time("now", now)
        if valid_until is not None:
            _require_time("valid_until", valid_until)
        if not isinstance(state, EntitlementState):
            raise CommercialAccessError("state must be an EntitlementState")
        if not isinstance(paid_provider_allowed, bool):
            raise CommercialAccessError("paid_provider_allowed must be boolean")
        payload = _event_payload(
            tenant_id=tenant_id,
            user_id=user_id,
            plan_id=plan_id,
            state=state,
            valid_until=valid_until,
            paid_provider_allowed=paid_provider_allowed,
        )
        payload_sha256 = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing_event = connection.execute(
                "SELECT payload_sha256, snapshot_json FROM commercial_entitlement_events WHERE event_id = ?",
                (event_id,),
            ).fetchone()
            if existing_event is not None:
                if str(existing_event["payload_sha256"]) != payload_sha256:
                    raise CommercialAccessError(
                        "entitlement event_id conflicts with different content"
                    )
                return _entitlement_from_json(str(existing_event["snapshot_json"]))
            current = connection.execute(
                "SELECT version FROM commercial_entitlements WHERE tenant_id = ? AND user_id = ?",
                (tenant_id, user_id),
            ).fetchone()
            version = 1 if current is None else int(current["version"]) + 1
            entitlement = CommercialEntitlement(
                tenant_id=tenant_id,
                user_id=user_id,
                plan_id=plan_id,
                state=state,
                valid_until=valid_until,
                paid_provider_allowed=paid_provider_allowed,
                version=version,
            )
            updated_at = now.isoformat()
            connection.execute(
                "INSERT INTO commercial_entitlements "
                "(tenant_id,user_id,plan_id,state,valid_until,paid_provider_allowed,version,updated_at) "
                "VALUES (?,?,?,?,?,?,?,?) ON CONFLICT(tenant_id,user_id) DO UPDATE SET "
                "plan_id=excluded.plan_id,state=excluded.state,valid_until=excluded.valid_until,"
                "paid_provider_allowed=excluded.paid_provider_allowed,version=excluded.version,updated_at=excluded.updated_at",
                (
                    tenant_id,
                    user_id,
                    plan_id,
                    state.value,
                    None if valid_until is None else valid_until.isoformat(),
                    int(paid_provider_allowed),
                    version,
                    updated_at,
                ),
            )
            snapshot = _entitlement_json(entitlement)
            connection.execute(
                "INSERT INTO commercial_entitlement_events VALUES (?,?,?,?,?,?)",
                (event_id, tenant_id, user_id, payload_sha256, snapshot, updated_at),
            )
        return entitlement

    def get_entitlement(self, *, tenant_id: str, user_id: str) -> CommercialEntitlement:
        _require_text("tenant_id", tenant_id)
        _require_text("user_id", user_id)
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM commercial_entitlements WHERE tenant_id = ? AND user_id = ?",
                (tenant_id, user_id),
            ).fetchone()
        if row is None:
            raise CommercialAccessError("commercial entitlement does not exist")
        return _entitlement_from_row(row)

    def require_access(
        self,
        *,
        tenant_id: str,
        user_id: str,
        now: datetime,
        paid_provider: bool = False,
    ) -> CommercialEntitlement:
        _require_time("now", now)
        entitlement = self.get_entitlement(tenant_id=tenant_id, user_id=user_id)
        if entitlement.state is not EntitlementState.ACTIVE:
            raise CommercialAccessError("commercial entitlement is not active")
        if entitlement.valid_until is not None and now >= entitlement.valid_until:
            raise CommercialAccessError("commercial entitlement is expired")
        if paid_provider and not entitlement.paid_provider_allowed:
            raise CommercialAccessError("commercial entitlement does not authorize paid providers")
        return entitlement

    def seed_credit_account(self, account: ManagedCreditAccount) -> ManagedCreditAccount:
        return self._credits.seed_account(account)

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
        self.require_access(tenant_id=tenant_id, user_id=user_id, now=now, paid_provider=True)
        try:
            account = self._credits.get_account(tenant_id=tenant_id, user_id=user_id)
            return self._credits.reserve(
                account=account,
                request_id=request_id,
                routing_decision_id=routing_decision_id,
                quote=quote,
            )
        except ManagedCreditError as error:
            raise CommercialAccessError(str(error)) from error

    def settle_provider_spend(
        self,
        *,
        authorization_id: str,
        actual_cost_microusd: int,
        provider_job_id: str,
    ) -> CreditSettlementOutcome:
        try:
            return self._credits.settle(
                authorization_id=authorization_id,
                actual_cost_microusd=actual_cost_microusd,
                provider_job_id=provider_job_id,
            )
        except ManagedCreditError as error:
            raise CommercialAccessError(str(error)) from error

    def release_provider_spend(self, *, authorization_id: str) -> ManagedCreditAccount:
        try:
            return self._credits.release(authorization_id=authorization_id)
        except ManagedCreditError as error:
            raise CommercialAccessError(str(error)) from error


def _trusted_grant_payload(
    *,
    provider_subscription_id: str,
    tenant_id: str,
    user_id: str,
    plan_id: str,
    period_start: datetime,
    period_end: datetime,
    paid_provider_allowed: bool,
) -> str:
    return json.dumps(
        {
            "provider_subscription_id": provider_subscription_id,
            "tenant_id": tenant_id,
            "user_id": user_id,
            "plan_id": plan_id,
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "paid_provider_allowed": paid_provider_allowed,
        },
        sort_keys=True,
        separators=(",", ":"),
    )


def _trusted_grant_from_row(row: sqlite3.Row) -> TrustedCommercialGrant:
    return TrustedCommercialGrant(
        grant_id=str(row["grant_id"]),
        version=int(row["version"]),
        provider_subscription_id=str(row["provider_subscription_id"]),
        tenant_id=str(row["tenant_id"]),
        user_id=str(row["user_id"]),
        plan_id=str(row["plan_id"]),
        period_start=datetime.fromisoformat(str(row["period_start"])),
        period_end=datetime.fromisoformat(str(row["period_end"])),
        paid_provider_allowed=bool(row["paid_provider_allowed"]),
        created_at=datetime.fromisoformat(str(row["created_at"])),
    )


def _event_payload(
    *,
    tenant_id: str,
    user_id: str,
    plan_id: str,
    state: EntitlementState,
    valid_until: datetime | None,
    paid_provider_allowed: bool,
) -> str:
    return json.dumps(
        {
            "tenant_id": tenant_id,
            "user_id": user_id,
            "plan_id": plan_id,
            "state": state.value,
            "valid_until": None if valid_until is None else valid_until.isoformat(),
            "paid_provider_allowed": paid_provider_allowed,
        },
        sort_keys=True,
        separators=(",", ":"),
    )


def _provider_binding_json(binding: ProviderSubscriptionBinding) -> str:
    return json.dumps(
        {
            "provider_subscription_id": binding.provider_subscription_id,
            "tenant_id": binding.tenant_id,
            "user_id": binding.user_id,
            "plan_id": binding.plan_id,
            "state": binding.state.value,
            "created_at": binding.created_at.isoformat(),
            "updated_at": binding.updated_at.isoformat(),
            "last_provider_event_at": (
                None
                if binding.last_provider_event_at is None
                else binding.last_provider_event_at.isoformat()
            ),
        },
        sort_keys=True,
        separators=(",", ":"),
    )


def _provider_binding_from_json(value: str) -> ProviderSubscriptionBinding:
    payload = json.loads(value)
    if not isinstance(payload, dict):
        raise CommercialAccessError("stored provider subscription snapshot is malformed")
    last_event = payload.get("last_provider_event_at")
    return ProviderSubscriptionBinding(
        provider_subscription_id=str(payload["provider_subscription_id"]),
        tenant_id=str(payload["tenant_id"]),
        user_id=str(payload["user_id"]),
        plan_id=str(payload["plan_id"]),
        state=ProviderSubscriptionState(str(payload["state"])),
        created_at=datetime.fromisoformat(str(payload["created_at"])),
        updated_at=datetime.fromisoformat(str(payload["updated_at"])),
        last_provider_event_at=(
            None if last_event is None else datetime.fromisoformat(str(last_event))
        ),
    )


def _provider_binding_from_row(row: sqlite3.Row) -> ProviderSubscriptionBinding:
    last_event = row["last_provider_event_at"]
    return ProviderSubscriptionBinding(
        provider_subscription_id=str(row["provider_subscription_id"]),
        tenant_id=str(row["tenant_id"]),
        user_id=str(row["user_id"]),
        plan_id=str(row["plan_id"]),
        state=ProviderSubscriptionState(str(row["state"])),
        created_at=datetime.fromisoformat(str(row["created_at"])),
        updated_at=datetime.fromisoformat(str(row["updated_at"])),
        last_provider_event_at=(
            None if last_event is None else datetime.fromisoformat(str(last_event))
        ),
    )


def _entitlement_json(entitlement: CommercialEntitlement) -> str:
    payload = asdict(entitlement)
    payload["state"] = entitlement.state.value
    payload["valid_until"] = (
        None if entitlement.valid_until is None else entitlement.valid_until.isoformat()
    )
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _entitlement_from_json(value: str) -> CommercialEntitlement:
    payload = json.loads(value)
    if not isinstance(payload, dict):
        raise CommercialAccessError("stored entitlement snapshot is malformed")
    valid_until = payload.get("valid_until")
    return CommercialEntitlement(
        tenant_id=str(payload["tenant_id"]),
        user_id=str(payload["user_id"]),
        plan_id=str(payload["plan_id"]),
        state=EntitlementState(str(payload["state"])),
        valid_until=None if valid_until is None else datetime.fromisoformat(str(valid_until)),
        paid_provider_allowed=bool(payload["paid_provider_allowed"]),
        version=int(payload["version"]),
    )


def _entitlement_from_row(row: sqlite3.Row) -> CommercialEntitlement:
    valid_until = row["valid_until"]
    return CommercialEntitlement(
        tenant_id=str(row["tenant_id"]),
        user_id=str(row["user_id"]),
        plan_id=str(row["plan_id"]),
        state=EntitlementState(str(row["state"])),
        valid_until=None if valid_until is None else datetime.fromisoformat(str(valid_until)),
        paid_provider_allowed=bool(row["paid_provider_allowed"]),
        version=int(row["version"]),
    )


def _require_text(name: str, value: str) -> None:
    if not isinstance(value, str) or not value or value != value.strip():
        raise CommercialAccessError(f"{name} must be non-blank and trimmed")


def _require_time(name: str, value: datetime) -> None:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise CommercialAccessError(f"{name} must be timezone-aware")


__all__ = [
    "CommercialAccessError",
    "CommercialAccessStore",
    "CommercialEntitlement",
    "EntitlementState",
    "MAX_TRUSTED_GRANT_DURATION",
    "ProviderSubscriptionBinding",
    "ProviderSubscriptionState",
    "TrustedCommercialGrant",
]
