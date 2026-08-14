"""Durable shared media credits and paid-provider side-effect safety."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

from .managed_credits import (
    CreditAuthorization,
    CreditAuthorizationOutcome,
    CreditSettlement,
    CreditSettlementOutcome,
    ManagedCreditAccount,
    ManagedCreditAuthorizer,
    ManagedCreditError,
    ProviderCostQuote,
)
from .models import ProviderRequest


class CreditAuthorizationState(str, Enum):
    RESERVED = "RESERVED"
    SETTLED = "SETTLED"
    RELEASED = "RELEASED"
    COST_POLICY_VIOLATION = "COST_POLICY_VIOLATION"


class ProviderSubmissionState(str, Enum):
    NOT_SUBMITTED = "NOT_SUBMITTED"
    SUBMITTING = "SUBMITTING"
    ACCEPTED = "ACCEPTED"
    AMBIGUOUS = "AMBIGUOUS"
    FAILED = "FAILED"
    COMPLETED = "COMPLETED"


class ReconciliationState(str, Enum):
    NOT_REQUIRED = "NOT_REQUIRED"
    PENDING = "PENDING"
    RECONCILED = "RECONCILED"


@dataclass(frozen=True, slots=True)
class PersistentCreditAuthorization:
    authorization: CreditAuthorization
    estimated_cost_microusd: int
    max_cost_microusd: int
    routing_decision_id: str
    state: CreditAuthorizationState
    provider_job_id: str | None = None
    actual_cost_microusd: int | None = None


@dataclass(frozen=True, slots=True)
class ProviderSideEffectRecord:
    request_id: str
    tenant_id: str
    user_id: str
    authorization_id: str
    routing_decision_id: str
    provider: str
    model: str
    payload_sha256: str
    submission_state: ProviderSubmissionState
    external_job_id: str | None
    submitted_at: str | None
    last_observed_status: str | None
    actual_cost_microusd: int | None
    artifact_reference: str | None
    reconciliation_state: ReconciliationState


_SCHEMA = """
CREATE TABLE IF NOT EXISTS credit_accounts (
 tenant_id TEXT NOT NULL, user_id TEXT NOT NULL,
 available_microusd INTEGER NOT NULL CHECK (available_microusd >= 0),
 reserved_microusd INTEGER NOT NULL CHECK (reserved_microusd >= 0),
 version INTEGER NOT NULL CHECK (version >= 1), PRIMARY KEY (tenant_id, user_id));
CREATE TABLE IF NOT EXISTS credit_authorizations (
 authorization_id TEXT PRIMARY KEY, request_id TEXT UNIQUE NOT NULL,
 tenant_id TEXT NOT NULL, user_id TEXT NOT NULL, provider_name TEXT NOT NULL,
 model_id TEXT NOT NULL, estimated_cost_microusd INTEGER NOT NULL,
 max_cost_microusd INTEGER NOT NULL, reserved_microusd INTEGER NOT NULL,
 account_version INTEGER NOT NULL, routing_decision_id TEXT NOT NULL,
 state TEXT NOT NULL, provider_job_id TEXT, actual_cost_microusd INTEGER,
 created_at TEXT NOT NULL, settled_at TEXT,
 FOREIGN KEY (tenant_id, user_id) REFERENCES credit_accounts (tenant_id, user_id));
CREATE TABLE IF NOT EXISTS provider_side_effects (
 request_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, user_id TEXT NOT NULL,
 authorization_id TEXT NOT NULL, routing_decision_id TEXT NOT NULL,
 provider TEXT NOT NULL, model TEXT NOT NULL, payload_sha256 TEXT NOT NULL,
 submission_state TEXT NOT NULL, external_job_id TEXT, submitted_at TEXT,
 last_observed_status TEXT, actual_cost_microusd INTEGER,
 artifact_reference TEXT, reconciliation_state TEXT NOT NULL,
 FOREIGN KEY (authorization_id) REFERENCES credit_authorizations (authorization_id));
"""


class ManagedCreditLedgerStore:
    """Persistent tenant/user balance, authorization, and settlement authority."""

    def __init__(self, root: Path) -> None:
        root.mkdir(parents=True, exist_ok=True)
        self._database = root / "managed_media_finops.sqlite3"
        with self._connect() as connection:
            connection.executescript(_SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def seed_account(self, account: ManagedCreditAccount) -> ManagedCreditAccount:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = self._account_row(connection, account.tenant_id, account.user_id)
            if row is not None:
                return _account(row)
            connection.execute(
                "INSERT INTO credit_accounts VALUES (?, ?, ?, ?, ?)",
                (
                    account.tenant_id,
                    account.user_id,
                    account.available_microusd,
                    account.reserved_microusd,
                    account.version,
                ),
            )
        return account

    def get_account(self, *, tenant_id: str, user_id: str) -> ManagedCreditAccount:
        with self._connect() as connection:
            row = self._account_row(connection, tenant_id, user_id)
        if row is None:
            raise ManagedCreditError("managed credit account does not exist")
        return _account(row)

    def reserve(
        self,
        *,
        account: ManagedCreditAccount,
        request_id: str,
        routing_decision_id: str,
        quote: ProviderCostQuote,
    ) -> CreditAuthorizationOutcome:
        _text("routing_decision_id", routing_decision_id)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = self._account_row(connection, account.tenant_id, account.user_id)
            if row is None:
                connection.execute(
                    "INSERT INTO credit_accounts VALUES (?, ?, ?, ?, ?)",
                    (
                        account.tenant_id,
                        account.user_id,
                        account.available_microusd,
                        account.reserved_microusd,
                        account.version,
                    ),
                )
                current = account
            else:
                current = _account(row)
            existing = connection.execute(
                "SELECT * FROM credit_authorizations WHERE request_id = ?",
                (request_id,),
            ).fetchone()
            if existing is not None:
                existing_row = _row(existing)
                _same_authorization(
                    existing_row, current, quote, routing_decision_id
                )
                return CreditAuthorizationOutcome(
                    current, _authorization(existing_row)
                )
            outcome = ManagedCreditAuthorizer().authorize(
                account=current, request_id=request_id, quote=quote
            )
            self._write_account(connection, outcome.account)
            auth = outcome.authorization
            connection.execute(
                "INSERT INTO credit_authorizations "
                "(authorization_id,request_id,tenant_id,user_id,provider_name,model_id,"
                "estimated_cost_microusd,max_cost_microusd,reserved_microusd,"
                "account_version,routing_decision_id,state,created_at) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    auth.authorization_id,
                    auth.request_id,
                    auth.tenant_id,
                    auth.user_id,
                    auth.provider_name,
                    auth.model_id,
                    quote.estimated_cost_microusd,
                    quote.max_cost_microusd,
                    auth.reserved_microusd,
                    auth.account_version,
                    routing_decision_id,
                    CreditAuthorizationState.RESERVED.value,
                    _now(),
                ),
            )
            return outcome

    def get_authorization(self, authorization_id: str) -> PersistentCreditAuthorization:
        with self._connect() as connection:
            value = connection.execute(
                "SELECT * FROM credit_authorizations WHERE authorization_id = ?",
                (authorization_id,),
            ).fetchone()
        if value is None:
            raise ManagedCreditError("credit authorization does not exist")
        return _persistent_authorization(_row(value))

    def settle(
        self,
        *,
        authorization_id: str,
        actual_cost_microusd: int,
        provider_job_id: str,
    ) -> CreditSettlementOutcome:
        _text("provider_job_id", provider_job_id)
        result: CreditSettlementOutcome | None = None
        violation = False
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            value = connection.execute(
                "SELECT * FROM credit_authorizations WHERE authorization_id = ?",
                (authorization_id,),
            ).fetchone()
            if value is None:
                raise ManagedCreditError("credit authorization does not exist")
            persistent = _persistent_authorization(_row(value))
            auth = persistent.authorization
            account_row = self._account_row(connection, auth.tenant_id, auth.user_id)
            if account_row is None:
                raise ManagedCreditError("managed credit account does not exist")
            account = _account(account_row)
            if persistent.state is CreditAuthorizationState.SETTLED:
                if (
                    persistent.actual_cost_microusd != actual_cost_microusd
                    or persistent.provider_job_id != provider_job_id
                ):
                    raise ManagedCreditError(
                        "authorization is already settled differently"
                    )
                released = auth.reserved_microusd - actual_cost_microusd
                return CreditSettlementOutcome(
                    account,
                    CreditSettlement(authorization_id, actual_cost_microusd, released),
                )
            if persistent.state is not CreditAuthorizationState.RESERVED:
                raise ManagedCreditError(
                    f"authorization cannot settle from state {persistent.state.value}"
                )
            if actual_cost_microusd > auth.reserved_microusd:
                connection.execute(
                    "UPDATE credit_authorizations SET state=?,provider_job_id=?,"
                    "actual_cost_microusd=?,settled_at=? WHERE authorization_id=?",
                    (
                        CreditAuthorizationState.COST_POLICY_VIOLATION.value,
                        provider_job_id,
                        actual_cost_microusd,
                        _now(),
                        authorization_id,
                    ),
                )
                violation = True
            else:
                result = ManagedCreditAuthorizer().settle(
                    account=account,
                    authorization=auth,
                    actual_cost_microusd=actual_cost_microusd,
                )
                self._write_account(connection, result.account)
                connection.execute(
                    "UPDATE credit_authorizations SET state=?,provider_job_id=?,"
                    "actual_cost_microusd=?,settled_at=? WHERE authorization_id=?",
                    (
                        CreditAuthorizationState.SETTLED.value,
                        provider_job_id,
                        actual_cost_microusd,
                        _now(),
                        authorization_id,
                    ),
                )
        if violation:
            raise ManagedCreditError("actual provider cost exceeded authorized maximum")
        if result is None:
            raise ManagedCreditError("settlement failed without a terminal state")
        return result

    def release(self, *, authorization_id: str) -> ManagedCreditAccount:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            value = connection.execute(
                "SELECT * FROM credit_authorizations WHERE authorization_id = ?",
                (authorization_id,),
            ).fetchone()
            if value is None:
                raise ManagedCreditError("credit authorization does not exist")
            persistent = _persistent_authorization(_row(value))
            auth = persistent.authorization
            account_row = self._account_row(connection, auth.tenant_id, auth.user_id)
            if account_row is None:
                raise ManagedCreditError("managed credit account does not exist")
            account = _account(account_row)
            if persistent.state is CreditAuthorizationState.RELEASED:
                return account
            if persistent.state is not CreditAuthorizationState.RESERVED:
                raise ManagedCreditError(
                    f"authorization cannot release from state {persistent.state.value}"
                )
            if account.reserved_microusd < auth.reserved_microusd:
                raise ManagedCreditError("reserved balance does not cover authorization")
            released = ManagedCreditAccount(
                tenant_id=account.tenant_id,
                user_id=account.user_id,
                available_microusd=account.available_microusd + auth.reserved_microusd,
                reserved_microusd=account.reserved_microusd - auth.reserved_microusd,
                version=account.version + 1,
            )
            self._write_account(connection, released)
            connection.execute(
                "UPDATE credit_authorizations SET state=?,settled_at=? "
                "WHERE authorization_id=?",
                (
                    CreditAuthorizationState.RELEASED.value,
                    _now(),
                    authorization_id,
                ),
            )
            return released

    @staticmethod
    def _account_row(
        connection: sqlite3.Connection, tenant_id: str, user_id: str
    ) -> sqlite3.Row | None:
        value = connection.execute(
            "SELECT * FROM credit_accounts WHERE tenant_id=? AND user_id=?",
            (tenant_id, user_id),
        ).fetchone()
        if value is None:
            return None
        return _row(value)

    @staticmethod
    def _write_account(
        connection: sqlite3.Connection, account: ManagedCreditAccount
    ) -> None:
        connection.execute(
            "UPDATE credit_accounts SET available_microusd=?,reserved_microusd=?,"
            "version=? WHERE tenant_id=? AND user_id=?",
            (
                account.available_microusd,
                account.reserved_microusd,
                account.version,
                account.tenant_id,
                account.user_id,
            ),
        )


class ProviderSideEffectLedger:
    """Durable duplicate-spend guard for paid provider submissions."""

    def __init__(self, store: ManagedCreditLedgerStore) -> None:
        self._store = store

    def prepare(
        self,
        *,
        request: ProviderRequest,
        authorization: CreditAuthorization,
        routing_decision_id: str,
    ) -> ProviderSideEffectRecord:
        _text("routing_decision_id", routing_decision_id)
        model = request.payload.get("model_id")
        if not isinstance(model, str) or not model.strip():
            raise ManagedCreditError("provider request requires model_id")
        digest = provider_request_payload_sha256(request)
        persistent = self._store.get_authorization(authorization.authorization_id)
        if persistent.state is not CreditAuthorizationState.RESERVED:
            raise ManagedCreditError("provider dispatch requires a reserved authorization")
        if persistent.routing_decision_id != routing_decision_id:
            raise ManagedCreditError("routing decision does not match authorization")
        if authorization.request_id != request.request_id:
            raise ManagedCreditError("provider request does not match authorization")
        with self._store._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            value = connection.execute(
                "SELECT * FROM provider_side_effects WHERE request_id=?",
                (request.request_id,),
            ).fetchone()
            if value is not None:
                record = _side_effect(_row(value))
                _same_side_effect(
                    record, request, authorization, routing_decision_id, digest
                )
                if record.submission_state in {
                    ProviderSubmissionState.SUBMITTING,
                    ProviderSubmissionState.ACCEPTED,
                    ProviderSubmissionState.AMBIGUOUS,
                    ProviderSubmissionState.COMPLETED,
                }:
                    raise ManagedCreditError(
                        "provider side effect already exists; reconcile instead of redispatch"
                    )
                connection.execute(
                    "UPDATE provider_side_effects SET submission_state=?,"
                    "reconciliation_state=? WHERE request_id=?",
                    (
                        ProviderSubmissionState.SUBMITTING.value,
                        ReconciliationState.NOT_REQUIRED.value,
                        request.request_id,
                    ),
                )
            else:
                connection.execute(
                    "INSERT INTO provider_side_effects "
                    "(request_id,tenant_id,user_id,authorization_id,routing_decision_id,"
                    "provider,model,payload_sha256,submission_state,reconciliation_state) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (
                        request.request_id,
                        authorization.tenant_id,
                        authorization.user_id,
                        authorization.authorization_id,
                        routing_decision_id,
                        request.provider_name,
                        model,
                        digest,
                        ProviderSubmissionState.SUBMITTING.value,
                        ReconciliationState.NOT_REQUIRED.value,
                    ),
                )
            current = connection.execute(
                "SELECT * FROM provider_side_effects WHERE request_id=?",
                (request.request_id,),
            ).fetchone()
            if current is None:
                raise ManagedCreditError("provider side-effect row was not persisted")
            return _side_effect(_row(current))

    def accepted(
        self, *, request_id: str, external_job_id: str
    ) -> ProviderSideEffectRecord:
        _text("external_job_id", external_job_id)
        return self._transition(
            request_id,
            ProviderSubmissionState.ACCEPTED,
            ReconciliationState.NOT_REQUIRED,
            external_job_id=external_job_id,
            submitted_at=_now(),
        )

    def failed(
        self, *, request_id: str, observed_status: str
    ) -> ProviderSideEffectRecord:
        _text("observed_status", observed_status)
        return self._transition(
            request_id,
            ProviderSubmissionState.FAILED,
            ReconciliationState.NOT_REQUIRED,
            observed_status=observed_status,
        )

    def ambiguous(
        self, *, request_id: str, observed_status: str
    ) -> ProviderSideEffectRecord:
        _text("observed_status", observed_status)
        return self._transition(
            request_id,
            ProviderSubmissionState.AMBIGUOUS,
            ReconciliationState.PENDING,
            observed_status=observed_status,
        )

    def complete(
        self,
        *,
        request_id: str,
        observed_status: str,
        actual_cost_microusd: int,
        artifact_reference: str,
    ) -> ProviderSideEffectRecord:
        _text("observed_status", observed_status)
        _text("artifact_reference", artifact_reference)
        if actual_cost_microusd < 0:
            raise ManagedCreditError("actual provider cost must be non-negative")
        return self._transition(
            request_id,
            ProviderSubmissionState.COMPLETED,
            ReconciliationState.RECONCILED,
            observed_status=observed_status,
            actual_cost_microusd=actual_cost_microusd,
            artifact_reference=artifact_reference,
        )

    def reconcile(
        self, *, request_id: str, external_job_id: str, observed_status: str
    ) -> ProviderSideEffectRecord:
        _text("external_job_id", external_job_id)
        _text("observed_status", observed_status)
        return self._transition(
            request_id,
            ProviderSubmissionState.ACCEPTED,
            ReconciliationState.RECONCILED,
            external_job_id=external_job_id,
            submitted_at=_now(),
            observed_status=observed_status,
            require=ProviderSubmissionState.AMBIGUOUS,
        )

    def get(self, request_id: str) -> ProviderSideEffectRecord:
        with self._store._connect() as connection:
            value = connection.execute(
                "SELECT * FROM provider_side_effects WHERE request_id=?", (request_id,)
            ).fetchone()
        if value is None:
            raise ManagedCreditError("provider side effect does not exist")
        return _side_effect(_row(value))

    def _transition(
        self,
        request_id: str,
        state: ProviderSubmissionState,
        reconciliation: ReconciliationState,
        *,
        external_job_id: str | None = None,
        submitted_at: str | None = None,
        observed_status: str | None = None,
        actual_cost_microusd: int | None = None,
        artifact_reference: str | None = None,
        require: ProviderSubmissionState | None = None,
    ) -> ProviderSideEffectRecord:
        with self._store._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            value = connection.execute(
                "SELECT * FROM provider_side_effects WHERE request_id=?", (request_id,)
            ).fetchone()
            if value is None:
                raise ManagedCreditError("provider side effect does not exist")
            current = _side_effect(_row(value))
            if require is not None and current.submission_state is not require:
                raise ManagedCreditError(
                    f"provider side effect must be {require.value} to reconcile"
                )
            connection.execute(
                "UPDATE provider_side_effects SET submission_state=?,"
                "external_job_id=COALESCE(?,external_job_id),"
                "submitted_at=COALESCE(?,submitted_at),"
                "last_observed_status=COALESCE(?,last_observed_status),"
                "actual_cost_microusd=COALESCE(?,actual_cost_microusd),"
                "artifact_reference=COALESCE(?,artifact_reference),"
                "reconciliation_state=? WHERE request_id=?",
                (
                    state.value,
                    external_job_id,
                    submitted_at,
                    observed_status,
                    actual_cost_microusd,
                    artifact_reference,
                    reconciliation.value,
                    request_id,
                ),
            )
            updated = connection.execute(
                "SELECT * FROM provider_side_effects WHERE request_id=?", (request_id,)
            ).fetchone()
            if updated is None:
                raise ManagedCreditError("provider side-effect row disappeared")
            return _side_effect(_row(updated))


def provider_request_payload_sha256(request: ProviderRequest) -> str:
    material: dict[str, object] = {
        "request_id": request.request_id,
        "job_id": request.job_id,
        "provider_name": request.provider_name,
        "operation": request.operation,
        "payload": dict(request.payload),
    }
    encoded = json.dumps(
        material, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _row(value: object) -> sqlite3.Row:
    if not isinstance(value, sqlite3.Row):
        raise ManagedCreditError("SQLite ledger returned an invalid row type")
    return value


def _account(row: sqlite3.Row) -> ManagedCreditAccount:
    return ManagedCreditAccount(
        tenant_id=str(row["tenant_id"]),
        user_id=str(row["user_id"]),
        available_microusd=int(row["available_microusd"]),
        reserved_microusd=int(row["reserved_microusd"]),
        version=int(row["version"]),
    )


def _authorization(row: sqlite3.Row) -> CreditAuthorization:
    return CreditAuthorization(
        authorization_id=str(row["authorization_id"]),
        request_id=str(row["request_id"]),
        tenant_id=str(row["tenant_id"]),
        user_id=str(row["user_id"]),
        provider_name=str(row["provider_name"]),
        model_id=str(row["model_id"]),
        reserved_microusd=int(row["reserved_microusd"]),
        account_version=int(row["account_version"]),
    )


def _persistent_authorization(row: sqlite3.Row) -> PersistentCreditAuthorization:
    job = row["provider_job_id"]
    cost = row["actual_cost_microusd"]
    return PersistentCreditAuthorization(
        authorization=_authorization(row),
        estimated_cost_microusd=int(row["estimated_cost_microusd"]),
        max_cost_microusd=int(row["max_cost_microusd"]),
        routing_decision_id=str(row["routing_decision_id"]),
        state=CreditAuthorizationState(str(row["state"])),
        provider_job_id=None if job is None else str(job),
        actual_cost_microusd=None if cost is None else int(cost),
    )


def _side_effect(row: sqlite3.Row) -> ProviderSideEffectRecord:
    cost = row["actual_cost_microusd"]
    return ProviderSideEffectRecord(
        request_id=str(row["request_id"]),
        tenant_id=str(row["tenant_id"]),
        user_id=str(row["user_id"]),
        authorization_id=str(row["authorization_id"]),
        routing_decision_id=str(row["routing_decision_id"]),
        provider=str(row["provider"]),
        model=str(row["model"]),
        payload_sha256=str(row["payload_sha256"]),
        submission_state=ProviderSubmissionState(str(row["submission_state"])),
        external_job_id=_optional(row, "external_job_id"),
        submitted_at=_optional(row, "submitted_at"),
        last_observed_status=_optional(row, "last_observed_status"),
        actual_cost_microusd=None if cost is None else int(cost),
        artifact_reference=_optional(row, "artifact_reference"),
        reconciliation_state=ReconciliationState(str(row["reconciliation_state"])),
    )


def _optional(row: sqlite3.Row, field: str) -> str | None:
    value = row[field]
    return None if value is None else str(value)


def _same_authorization(
    row: sqlite3.Row,
    account: ManagedCreditAccount,
    quote: ProviderCostQuote,
    routing_decision_id: str,
) -> None:
    observed = (
        str(row["tenant_id"]),
        str(row["user_id"]),
        str(row["provider_name"]),
        str(row["model_id"]),
        int(row["estimated_cost_microusd"]),
        int(row["max_cost_microusd"]),
        str(row["routing_decision_id"]),
    )
    expected = (
        account.tenant_id,
        account.user_id,
        quote.provider_name,
        quote.model_id,
        quote.estimated_cost_microusd,
        quote.max_cost_microusd,
        routing_decision_id,
    )
    if observed != expected:
        raise ManagedCreditError(
            "request_id is already bound to different authorization material"
        )


def _same_side_effect(
    record: ProviderSideEffectRecord,
    request: ProviderRequest,
    authorization: CreditAuthorization,
    routing_decision_id: str,
    digest: str,
) -> None:
    observed = (
        record.tenant_id,
        record.user_id,
        record.authorization_id,
        record.routing_decision_id,
        record.provider,
        record.model,
        record.payload_sha256,
    )
    expected = (
        authorization.tenant_id,
        authorization.user_id,
        authorization.authorization_id,
        routing_decision_id,
        request.provider_name,
        request.payload.get("model_id"),
        digest,
    )
    if observed != expected:
        raise ManagedCreditError(
            "request_id is already bound to a different provider side effect"
        )


def _text(name: str, value: str) -> None:
    if not value or not value.strip():
        raise ManagedCreditError(f"{name} must not be blank")
    if value != value.strip():
        raise ManagedCreditError(f"{name} must not contain surrounding whitespace")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
