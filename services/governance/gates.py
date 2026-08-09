"""Fail-closed security, HITL, metering, and credit gates."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol


class GateError(PermissionError):
    """Raised when governed work cannot cross a mandatory gate."""


class KeyManagementService(Protocol):
    """External key boundary; key material never enters the vault."""

    def encrypt(self, plaintext: bytes, *, context: str) -> bytes: ...

    def decrypt(self, ciphertext: bytes, *, context: str) -> bytes: ...


class SecretVault:
    def __init__(self, kms: KeyManagementService) -> None:
        self._kms = kms
        self._ciphertexts: dict[str, bytes] = {}

    def put(self, secret_id: str, plaintext: bytes) -> None:
        if not secret_id or not plaintext:
            raise GateError("secret id and plaintext are required")
        self._ciphertexts[secret_id] = self._kms.encrypt(
            plaintext, context=f"secret:{secret_id}"
        )

    def reveal(self, secret_id: str) -> bytes:
        try:
            ciphertext = self._ciphertexts[secret_id]
        except KeyError as error:
            raise GateError("unknown secret") from error
        return self._kms.decrypt(ciphertext, context=f"secret:{secret_id}")


def redact_sensitive(value: object) -> object:
    sensitive = {"api_key", "authorization", "password", "secret", "token"}
    if isinstance(value, dict):
        return {
            str(key): "[REDACTED]"
            if str(key).lower() in sensitive
            else redact_sensitive(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_sensitive(item) for item in value]
    return value


class HumanApprovalStore:
    """Durable human decisions; absence or denial always blocks."""

    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path
        database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS approvals ("
                "request_id TEXT PRIMARY KEY, status TEXT NOT NULL, "
                "approver TEXT NOT NULL, decided_at TEXT NOT NULL)"
            )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._database_path)

    def decide(self, request_id: str, *, approved: bool, approver: str) -> None:
        if not approver:
            raise GateError("human approver is required")
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO approvals VALUES (?, ?, ?, ?) "
                "ON CONFLICT(request_id) DO UPDATE SET status=excluded.status, "
                "approver=excluded.approver, decided_at=excluded.decided_at",
                (
                    request_id,
                    "approved" if approved else "denied",
                    approver,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )

    def is_approved(self, request_id: str) -> bool:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT status FROM approvals WHERE request_id = ?", (request_id,)
            ).fetchone()
        return row is not None and row[0] == "approved"


class PricingRegistry:
    def __init__(self, prices_minor: dict[str, int]) -> None:
        if any(price < 0 for price in prices_minor.values()):
            raise GateError("prices cannot be negative")
        self._prices = dict(prices_minor)

    def quote(self, meter: str, units: int) -> int:
        if units < 0 or meter not in self._prices:
            raise GateError("invalid meter or units")
        return self._prices[meter] * units


class FinancialLedger:
    """Durable reservation ledger with an account hard cap."""

    def __init__(self, database_path: Path, *, hard_cap_minor: int) -> None:
        if hard_cap_minor < 0:
            raise GateError("hard cap cannot be negative")
        self._database_path = database_path
        self._hard_cap = hard_cap_minor
        database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS ledger ("
                "reservation_id TEXT PRIMARY KEY, reserved_minor INTEGER NOT NULL, "
                "actual_minor INTEGER, status TEXT NOT NULL)"
            )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._database_path)

    def reserve(self, reservation_id: str, amount_minor: int) -> None:
        if amount_minor < 0:
            raise GateError("reservation cannot be negative")
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            used = connection.execute(
                "SELECT COALESCE(SUM(COALESCE(actual_minor, reserved_minor)), 0) "
                "FROM ledger"
            ).fetchone()[0]
            if used + amount_minor > self._hard_cap:
                raise GateError("financial hard cap exceeded")
            try:
                connection.execute(
                    "INSERT INTO ledger VALUES (?, ?, NULL, 'reserved')",
                    (reservation_id, amount_minor),
                )
            except sqlite3.IntegrityError as error:
                raise GateError("financial reservation already exists") from error

    def reconcile(self, reservation_id: str, actual_minor: int) -> None:
        if actual_minor < 0:
            raise GateError("actual charge cannot be negative")
        with self._connect() as connection:
            row = connection.execute(
                "SELECT reserved_minor FROM ledger WHERE reservation_id = ?",
                (reservation_id,),
            ).fetchone()
            if row is None or actual_minor > row[0]:
                raise GateError("actual charge exceeds reservation")
            connection.execute(
                "UPDATE ledger SET actual_minor = ?, status = 'reconciled' "
                "WHERE reservation_id = ?",
                (actual_minor, reservation_id),
            )

    def state(self) -> list[dict[str, int | str | None]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT reservation_id, reserved_minor, actual_minor, status "
                "FROM ledger ORDER BY reservation_id"
            ).fetchall()
        return [
            {
                "reservation_id": str(row[0]),
                "reserved_minor": int(row[1]),
                "actual_minor": None if row[2] is None else int(row[2]),
                "status": str(row[3]),
            }
            for row in rows
        ]


@dataclass(frozen=True, slots=True)
class WorkRequest:
    request_id: str
    risk: str
    billable_meter: str | None = None
    units: int = 0


class SecurityFinanceGate:
    def __init__(
        self,
        approvals: HumanApprovalStore,
        pricing: PricingRegistry,
        ledger: FinancialLedger,
    ) -> None:
        self._approvals = approvals
        self._pricing = pricing
        self._ledger = ledger

    def authorize(self, request: WorkRequest) -> int:
        if request.risk not in {"low", "medium", "high"}:
            raise GateError("unknown risk classification")
        if request.risk == "high" and not self._approvals.is_approved(
            request.request_id
        ):
            raise GateError("high-risk work requires durable human approval")
        if request.billable_meter is not None:
            amount = self._pricing.quote(request.billable_meter, request.units)
            self._ledger.reserve(request.request_id, amount)
            return amount
        return 0
