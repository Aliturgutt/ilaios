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
from datetime import datetime
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
"""


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
        return connection

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
        """Apply one idempotent external/admin entitlement event.

        ``event_id`` is deliberately provider-neutral. A future payment adapter may
        pass a verified webhook/event identity, while an administrative grant may
        pass its own audited identity. Reusing an event with different content is
        rejected.
        """

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
                "SELECT payload_sha256, snapshot_json "
                "FROM commercial_entitlement_events WHERE event_id = ?",
                (event_id,),
            ).fetchone()
            if existing_event is not None:
                if str(existing_event["payload_sha256"]) != payload_sha256:
                    raise CommercialAccessError(
                        "entitlement event_id conflicts with different content"
                    )
                return _entitlement_from_json(str(existing_event["snapshot_json"]))

            current = connection.execute(
                "SELECT version FROM commercial_entitlements "
                "WHERE tenant_id = ? AND user_id = ?",
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
                "(tenant_id,user_id,plan_id,state,valid_until,paid_provider_allowed,"
                "version,updated_at) VALUES (?,?,?,?,?,?,?,?) "
                "ON CONFLICT(tenant_id,user_id) DO UPDATE SET "
                "plan_id=excluded.plan_id,state=excluded.state,"
                "valid_until=excluded.valid_until,"
                "paid_provider_allowed=excluded.paid_provider_allowed,"
                "version=excluded.version,updated_at=excluded.updated_at",
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
                (
                    event_id,
                    tenant_id,
                    user_id,
                    payload_sha256,
                    snapshot,
                    updated_at,
                ),
            )
        return entitlement

    def get_entitlement(self, *, tenant_id: str, user_id: str) -> CommercialEntitlement:
        _require_text("tenant_id", tenant_id)
        _require_text("user_id", user_id)
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM commercial_entitlements "
                "WHERE tenant_id = ? AND user_id = ?",
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
            raise CommercialAccessError(
                "commercial entitlement does not authorize paid providers"
            )
        return entitlement

    def seed_credit_account(self, account: ManagedCreditAccount) -> ManagedCreditAccount:
        """Delegate account creation to the existing managed-credit authority."""

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
        """Require commercial access, then reserve through the canonical ledger."""

        self.require_access(
            tenant_id=tenant_id,
            user_id=user_id,
            now=now,
            paid_provider=True,
        )
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
        """Settle in-flight spend even if entitlement later changes state."""

        try:
            return self._credits.settle(
                authorization_id=authorization_id,
                actual_cost_microusd=actual_cost_microusd,
                provider_job_id=provider_job_id,
            )
        except ManagedCreditError as error:
            raise CommercialAccessError(str(error)) from error

    def release_provider_spend(self, *, authorization_id: str) -> ManagedCreditAccount:
        """Release an unused reservation through the canonical ledger."""

        try:
            return self._credits.release(authorization_id=authorization_id)
        except ManagedCreditError as error:
            raise CommercialAccessError(str(error)) from error


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
]
