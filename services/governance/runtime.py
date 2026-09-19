"""Durable security and financial gates on the real runtime execution path."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast

from services.runtime import GovernedRuntime

from .cost_projection import CostProjectionError, project_explicit_costs
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
_RISK_CLASSES = frozenset({"low", "medium", "high"})
_ADMISSION_KEY = "_ilaios_admission"
_ADMISSION_SCHEMA_VERSION = 1


class GovernedRuntimeGateway:
    """Persist work intent and enforce DLP, HITL, admission, and credits."""

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
        *,
        risk: str = "high",
    ) -> dict[str, object]:
        if not all((request_id, requester_id, agent_id, skill_id, capability)):
            raise GateError("governed work identifiers are required")
        if risk not in _RISK_CLASSES:
            raise GateError("unknown risk classification")
        self._reject_inline_secrets(payload)
        admission = _new_admission(risk)
        stored_metadata = json.dumps(
            {_ADMISSION_KEY: admission}, sort_keys=True, separators=(",", ":")
        )
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
                    "INSERT INTO governed_work VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?)",
                    (
                        request_id,
                        requester_id,
                        agent_id,
                        skill_id,
                        capability,
                        json.dumps(payload, sort_keys=True, separators=(",", ":")),
                        json.dumps(secret_ids),
                        stored_metadata,
                    ),
                )
            except sqlite3.IntegrityError as error:
                raise GateError("governed work request already exists") from error
        approval_required = bool(admission["human_approval_required"])
        return {
            "request_id": request_id,
            "risk": risk,
            "meter": "runtime_execution",
            "quoted_minor": self._pricing.quote("runtime_execution", 1),
            "status": "pending_approval" if approval_required else "admitted",
            "admission_decision": admission["admission_decision"],
            "human_approval_required": approval_required,
        }

    def decide(self, request_id: str, approver: str, decision: str) -> None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT requester_id, status, result_json FROM governed_work "
                "WHERE request_id = ?",
                (request_id,),
            ).fetchone()
        if row is None:
            raise GateError("unknown governed work request")
        admission = _read_admission(row["result_json"])
        if not bool(admission["human_approval_required"]):
            raise GateError("governed work does not require human approval")
        if not approver or approver == row["requester_id"]:
            raise GateError("independent human approver is required")
        if row["status"] != "pending":
            raise GateError("governed work is no longer pending")
        if decision not in {"approved", "denied"}:
            raise GateError("approval decision must be approved or denied")
        self._approvals.decide(
            request_id, approved=decision == "approved", approver=approver
        )
        if decision == "denied":
            with self._connect() as connection:
                connection.execute(
                    "UPDATE governed_work SET status = 'denied' WHERE request_id = ?",
                    (request_id,),
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
        """Reserve server-metered execution using persisted admission risk."""
        with self._connect() as connection:
            row = connection.execute(
                "SELECT status, result_json FROM governed_work WHERE request_id = ?",
                (request_id,),
            ).fetchone()
        if row is None:
            raise GateError("unknown governed work request")
        if row["status"] != "pending":
            raise GateError("governed work cannot execute more than once")
        admission = _read_admission(row["result_json"])
        risk = str(admission["risk"])
        decision = str(admission["admission_decision"])
        if risk in {"low", "medium"} and decision != "ALLOW":
            raise GateError("governed work lacks executable admission")
        if risk == "high" and decision != "REQUIRE_APPROVAL":
            raise GateError("high-risk work has invalid admission state")
        return self._gate.authorize(
            WorkRequest(request_id, risk, "runtime_execution", 1)
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
        admission = self._persisted_admission(request_id)
        stored_result: dict[str, object] = {_ADMISSION_KEY: admission}
        if result is not None:
            stored_result["result"] = result
        self._ledger.reconcile(request_id, actual_minor)
        with self._connect() as connection:
            connection.execute(
                "UPDATE governed_work SET status = ?, result_json = ? WHERE request_id = ?",
                (status, json.dumps(stored_result, sort_keys=True), request_id),
            )

    def state(self) -> dict[str, object]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT request_id, requester_id, status, result_json "
                "FROM governed_work ORDER BY request_id"
            ).fetchall()
            work = [
                {
                    "request_id": row["request_id"],
                    "requester_id": row["requester_id"],
                    "status": row["status"],
                }
                for row in rows
            ]
            admissions = [
                {
                    "request_id": row["request_id"],
                    **_public_admission(_read_admission(row["result_json"])),
                }
                for row in rows
            ]
            references = [
                {"secret_id": row["secret_id"], "reference": row["reference"]}
                for row in connection.execute(
                    "SELECT secret_id, reference FROM secret_references ORDER BY secret_id"
                ).fetchall()
            ]
        try:
            costs = project_explicit_costs(
                (str(row["request_id"]), row["result_json"]) for row in rows
            )
        except CostProjectionError as error:
            raise GateError("governed cost telemetry is malformed") from error
        return {
            "work": work,
            "admissions": admissions,
            "secret_references": references,
            "ledger": self._ledger.state(),
            "costs": costs,
        }

    def admission_snapshot(self, request_id: str) -> dict[str, object]:
        """Return the persisted server-authoritative admission for evidence."""
        admission = self._persisted_admission(request_id)
        approval_proven = self._approvals.is_approved(request_id)
        risk = str(admission["risk"])
        decision = str(admission["admission_decision"])
        required = bool(admission["human_approval_required"])
        admitted = (risk in {"low", "medium"} and decision == "ALLOW") or (
            risk == "high" and decision == "REQUIRE_APPROVAL" and approval_proven
        )
        return {
            "risk": risk,
            "admission_decision": decision,
            "human_approval_required": required,
            "approval_proven": approval_proven,
            "admission_proven": admitted,
        }

    def admission_proven(self, request_id: str) -> bool:
        return bool(self.admission_snapshot(request_id)["admission_proven"])

    def approval_proven(self, request_id: str) -> bool:
        """Read durable human approval without implying it is always required."""
        return self._approvals.is_approved(request_id)

    def _persisted_admission(self, request_id: str) -> dict[str, object]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT result_json FROM governed_work WHERE request_id = ?",
                (request_id,),
            ).fetchone()
        if row is None:
            raise GateError("governed admission is unavailable")
        return _read_admission(row["result_json"])

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


def _new_admission(risk: str) -> dict[str, object]:
    approval_required = risk == "high"
    return {
        "schema_version": _ADMISSION_SCHEMA_VERSION,
        "risk": risk,
        "admission_decision": "REQUIRE_APPROVAL" if approval_required else "ALLOW",
        "human_approval_required": approval_required,
        "admitted_at": datetime.now(timezone.utc).isoformat(),
    }


def _legacy_admission() -> dict[str, object]:
    return {
        "schema_version": 0,
        "risk": "high",
        "admission_decision": "REQUIRE_APPROVAL",
        "human_approval_required": True,
        "admitted_at": None,
    }


def _read_admission(raw: object) -> dict[str, object]:
    if raw is None:
        return _legacy_admission()
    try:
        value = json.loads(str(raw))
    except (TypeError, ValueError, json.JSONDecodeError) as error:
        raise GateError("stored governed admission is malformed") from error
    if not isinstance(value, dict):
        raise GateError("stored governed admission is malformed")
    candidate = value.get(_ADMISSION_KEY)
    if candidate is None:
        return _legacy_admission()
    if not isinstance(candidate, dict):
        raise GateError("stored governed admission is malformed")
    version = candidate.get("schema_version")
    risk = candidate.get("risk")
    decision = candidate.get("admission_decision")
    required = candidate.get("human_approval_required")
    admitted_at = candidate.get("admitted_at")
    if version != _ADMISSION_SCHEMA_VERSION:
        raise GateError("stored governed admission schema is unsupported")
    if risk not in _RISK_CLASSES:
        raise GateError("stored governed admission risk is invalid")
    expected_required = risk == "high"
    expected_decision = "REQUIRE_APPROVAL" if expected_required else "ALLOW"
    if required is not expected_required or decision != expected_decision:
        raise GateError("stored governed admission policy is inconsistent")
    if not isinstance(admitted_at, str) or not admitted_at:
        raise GateError("stored governed admission timestamp is invalid")
    return {
        "schema_version": version,
        "risk": risk,
        "admission_decision": decision,
        "human_approval_required": required,
        "admitted_at": admitted_at,
    }


def _public_admission(admission: dict[str, object]) -> dict[str, object]:
    return {
        "risk": admission["risk"],
        "admission_decision": admission["admission_decision"],
        "human_approval_required": admission["human_approval_required"],
    }
