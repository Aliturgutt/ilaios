"""Fail-closed FREE admission using the existing managed-credit SQLite authority.

This module does not create a second ledger. It stores FREE-usage evidence in the
same ``managed_media_finops.sqlite3`` database owned by ``ManagedCreditLedgerStore``.
"""

from __future__ import annotations

from dataclasses import dataclass

from .commercial_cost_config import CommercialCostConfig
from .commercial_types import CommercialAdmissionError, nonnegative_int, require_text
from .managed_credit_store import ManagedCreditLedgerStore


@dataclass(frozen=True, slots=True)
class FreeOperationAdmission:
    request_id: str
    tenant_id: str
    user_id: str
    month_key: str
    provider_name: str
    model_id: str
    ordinal: int
    monthly_limit: int


_SCHEMA = """
CREATE TABLE IF NOT EXISTS free_operation_usage (
 request_id TEXT PRIMARY KEY,
 tenant_id TEXT NOT NULL,
 user_id TEXT NOT NULL,
 month_key TEXT NOT NULL,
 provider_name TEXT NOT NULL,
 model_id TEXT NOT NULL,
 provider_cost_microusd INTEGER NOT NULL CHECK (provider_cost_microusd = 0),
 ordinal INTEGER NOT NULL CHECK (ordinal >= 1),
 created_at_epoch_s INTEGER NOT NULL CHECK (created_at_epoch_s >= 0),
 UNIQUE (tenant_id, user_id, month_key, ordinal));
CREATE INDEX IF NOT EXISTS free_operation_usage_scope_idx
 ON free_operation_usage (tenant_id, user_id, month_key);
"""


def authorize_free_operation(
    *,
    store: ManagedCreditLedgerStore,
    config: CommercialCostConfig,
    request_id: str,
    tenant_id: str,
    user_id: str,
    month_key: str,
    provider_name: str,
    model_id: str,
    provider_cost_microusd: int,
    platform_free_budget_allowed: bool,
    now_epoch_s: int,
) -> FreeOperationAdmission:
    """Admit one exact-zero-cost operation or fail closed without paid fallback."""

    for name, value in (
        ("request_id", request_id),
        ("tenant_id", tenant_id),
        ("user_id", user_id),
        ("month_key", month_key),
        ("provider_name", provider_name),
        ("model_id", model_id),
    ):
        require_text(name, value)
    nonnegative_int("provider_cost_microusd", provider_cost_microusd)
    nonnegative_int("now_epoch_s", now_epoch_s)
    monthly_limit = config.free_operations_per_active_user_per_month
    if provider_cost_microusd != 0:
        raise CommercialAdmissionError(
            "FREE admission requires authoritative zero provider cost; paid quote required"
        )
    if not platform_free_budget_allowed:
        raise CommercialAdmissionError(
            "FREE platform budget is unavailable; paid quote required or request rejected"
        )

    with store._connect() as connection:  # same managed-credit database authority
        connection.executescript(_SCHEMA)
        connection.execute("BEGIN IMMEDIATE")
        existing = connection.execute(
            "SELECT * FROM free_operation_usage WHERE request_id=?",
            (request_id,),
        ).fetchone()
        if existing is not None:
            row = dict(existing)
            expected = {
                "tenant_id": tenant_id,
                "user_id": user_id,
                "month_key": month_key,
                "provider_name": provider_name,
                "model_id": model_id,
                "provider_cost_microusd": provider_cost_microusd,
            }
            for key, expected_value in expected.items():
                if row[key] != expected_value:
                    raise CommercialAdmissionError(
                        "free-operation request_id already exists with different identity"
                    )
            return FreeOperationAdmission(
                request_id=request_id,
                tenant_id=tenant_id,
                user_id=user_id,
                month_key=month_key,
                provider_name=provider_name,
                model_id=model_id,
                ordinal=int(row["ordinal"]),
                monthly_limit=monthly_limit,
            )

        count_row = connection.execute(
            "SELECT COUNT(*) AS count FROM free_operation_usage "
            "WHERE tenant_id=? AND user_id=? AND month_key=?",
            (tenant_id, user_id, month_key),
        ).fetchone()
        if count_row is None:
            raise CommercialAdmissionError("free-operation usage count unavailable")
        used = int(count_row["count"])
        if used >= monthly_limit:
            raise CommercialAdmissionError(
                "monthly FREE operation quota exhausted; paid quote required"
            )
        ordinal = used + 1
        connection.execute(
            "INSERT INTO free_operation_usage "
            "(request_id,tenant_id,user_id,month_key,provider_name,model_id,"
            "provider_cost_microusd,ordinal,created_at_epoch_s) VALUES (?,?,?,?,?,?,?,?,?)",
            (
                request_id,
                tenant_id,
                user_id,
                month_key,
                provider_name,
                model_id,
                provider_cost_microusd,
                ordinal,
                now_epoch_s,
            ),
        )
    return FreeOperationAdmission(
        request_id=request_id,
        tenant_id=tenant_id,
        user_id=user_id,
        month_key=month_key,
        provider_name=provider_name,
        model_id=model_id,
        ordinal=ordinal,
        monthly_limit=monthly_limit,
    )
