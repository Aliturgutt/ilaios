"""Durable security and financial gates on the real runtime execution path."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast

from services.runtime import GovernedRuntime

from .gates import (
    FinancialLedger,
    GateError,
    HumanApprovalStore,
    PricingRegistry,
    SecurityFinanceGate,
    WorkRequest,
    redact_sensitive,
)

_SENSITIVE_KEYS = {"api_key", "authorization", "password", "secret", "token"}
_REFERENCE_PREFIXES = ("env://", "kms://", "vault://")


class GovernedRuntimeGateway:
    """Persist work intent and enforce DLP, HITL, and credits before execution."""

    def __init__(
        self,
        database_path: Path,
        runtime: GovernedRuntime,
        *,
        hard_cap_minor: int,
    ) -> None:
        self._database_path = database_path
        self._runtime = runtime
        self._approvals = HumanApprovalStore(database_path)
        self._pricing = PricingRegistry({"runtime_execution": 10})
        self._ledger = FinancialLedger(database_path, hard_cap_minor=hard_cap_minor)
        self._gate = SecurityFinanceGate(self._approvals, self._pricing, self._ledger)
        database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(
                "CREATE TABLE IF NOT EXISTS secret_references ("
                "secret_id TEXT PRIMARY KEY, reference TEXT UNIQUE NOT NULL, "
                "registered_at TEXT NOT NULL);"
                "CREATE TABLE IF NOT EXISTS governed_work ("
                "request_id TEXT PRIMARY KEY, requester_id TEXT NOT NULL, "
                "agent_id TEXT NOT NULL, skill_id TEXT NOT NULL, "
                "capability TEXT NOT NULL, payload_json TEXT NOT NULL, "
                "secret_ids_json TEXT NOT NULL, status TEXT NOT NULL, "
                "result_json TEXT);"
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def register_secret_reference(self, secret_id: str, reference: str) -> None:
        if (
            not secret_id
            or not reference.startswith(_REFERENCE_PREFIXES)
            or any(character.isspace() for character in reference)
        ):
            raise GateError("a valid opaque secret reference is required")
        with self._connect() as connection:
            try:
                connection.execute(
                    "INSERT INTO secret_references VALUES (?, ?, ?)",
                    (secret_id, reference, datetime.now(timezone.utc).isoformat()),
                )
            except sqlite3.IntegrityError as error:
                raise GateError("secret reference already exists") from error

    def submit(
        self,
        request_id: str,
        requester_id: str,
        agent_id: str,
        skill_id: str,
        capability: str,
        payload: dict[str, Any],
        secret_ids: tuple[str, ...],
    ) -> dict[str, object]:
        if not all((request_id, requester_id, agent_id, skill_id, capability)):
            raise GateError("governed work identifiers are required")
        self._reject_inline_secrets(payload)
        with self._connect() as connection:
            registered = {
                str(row["secret_id"])
                for row in connection.execute(
                    "SELECT secret_id FROM secret_references"
                ).fetchall()
            }
            found = set(secret_ids) & registered
            if found != set(secret_ids):
                raise GateError("work references an unknown secret boundary")
            try:
                connection.execute(
                    "INSERT INTO governed_work VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', NULL)",
                    (
                        request_id,
                        requester_id,
                        agent_id,
                        skill_id,
                        capability,
                        json.dumps(payload, sort_keys=True, separators=(",", ":")),
                        json.dumps(secret_ids),
                    ),
                )
            except sqlite3.IntegrityError as error:
                raise GateError("governed work request already exists") from error
        return {
            "request_id": request_id,
            "risk": "high",
            "meter": "runtime_execution",
            "quoted_minor": self._pricing.quote("runtime_execution", 1),
            "status": "pending_approval",
        }

    def decide(self, request_id: str, approver: str, decision: str) -> None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT requester_id, status FROM governed_work WHERE request_id = ?",
                (request_id,),
            ).fetchone()
        if row is None:
            raise GateError("unknown governed work request")
        if not approver or approver == row["requester_id"]:
            raise GateError("independent human approver is required")
        if row["status"] != "pending":
            raise GateError("governed work is no longer pending")
        if decision not in {"approved", "denied"}:
            raise GateError("approval decision must be approved or denied")
        self._approvals.decide(
            request_id, approved=decision == "approved", approver=approver
        )

    def execute(self, request_id: str) -> dict[str, object]:
        amount = self.authorize_billable(request_id)
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM governed_work WHERE request_id = ?", (request_id,)
            ).fetchone()
        if row is None:  # pragma: no cover - protected by authorize_billable
            raise GateError("unknown governed work request")
        payload = cast(dict[str, Any], json.loads(row["payload_json"]))
        try:
            result = self._runtime.execute(
                str(row["agent_id"]),
                str(row["skill_id"]),
                str(row["capability"]),
                payload,
            )
        except Exception:
            self.reconcile_billable(request_id, actual_minor=0, status="failed")
            raise
        safe_result = cast(dict[str, object], redact_sensitive(result))
        self.reconcile_billable(
            request_id, actual_minor=amount, status="executed", result=safe_result
        )
        return {
            **safe_result,
            "request_id": request_id,
            "metered_units": 1,
            "reserved_minor": amount,
            "actual_minor": amount,
        }

    def authorize_billable(self, request_id: str) -> int:
        """Reserve one server-metered execution after durable HITL approval."""
        with self._connect() as connection:
            row = connection.execute(
                "SELECT status FROM governed_work WHERE request_id = ?", (request_id,)
            ).fetchone()
        if row is None:
            raise GateError("unknown governed work request")
        if row["status"] != "pending":
            raise GateError("governed work cannot execute more than once")
        return self._gate.authorize(
            WorkRequest(request_id, "high", "runtime_execution", 1)
        )

    def reconcile_billable(
        self,
        request_id: str,
        *,
        actual_minor: int,
        status: str,
        result: dict[str, object] | None = None,
    ) -> None:
        if status not in {"executed", "failed"}:
            raise GateError("invalid governed work terminal status")
        self._ledger.reconcile(request_id, actual_minor)
        with self._connect() as connection:
            connection.execute(
                "UPDATE governed_work SET status = ?, result_json = ? WHERE request_id = ?",
                (
                    status,
                    None if result is None else json.dumps(result, sort_keys=True),
                    request_id,
                ),
            )

    def state(self) -> dict[str, object]:
        with self._connect() as connection:
            work = [
                {
                    "request_id": row["request_id"],
                    "requester_id": row["requester_id"],
                    "status": row["status"],
                }
                for row in connection.execute(
                    "SELECT request_id, requester_id, status FROM governed_work "
                    "ORDER BY request_id"
                ).fetchall()
            ]
            references = [
                {"secret_id": row["secret_id"], "reference": row["reference"]}
                for row in connection.execute(
                    "SELECT secret_id, reference FROM secret_references ORDER BY secret_id"
                ).fetchall()
            ]
        return {
            "work": work,
            "secret_references": references,
            "ledger": self._ledger.state(),
        }

    @classmethod
    def _reject_inline_secrets(cls, value: object) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                if str(key).lower() in _SENSITIVE_KEYS:
                    raise GateError("DLP rejected inline secret material")
                cls._reject_inline_secrets(item)
        elif isinstance(value, list):
            for item in value:
                cls._reject_inline_secrets(item)
