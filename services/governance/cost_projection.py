"""Fail-closed projection of governed execution costs with explicit currency semantics."""

from __future__ import annotations

import json
import math
from collections.abc import Iterable
from dataclasses import dataclass


class CostProjectionError(ValueError):
    """Persisted monetary telemetry cannot be interpreted safely."""


@dataclass(frozen=True, slots=True)
class ExplicitCostRecord:
    request_id: str
    amount_usd: float
    source_field: str
    source_unit: str

    def as_dict(self) -> dict[str, object]:
        return {
            "request_id": self.request_id,
            "amount_usd": self.amount_usd,
            "source_field": self.source_field,
            "source_unit": self.source_unit,
        }


_USD_FIELDS = ("actual_cost_usd", "total_cost_usd", "cost_usd")
_MICROUSD_FIELDS = (
    "actual_cost_microusd",
    "total_cost_microusd",
    "cost_microusd",
)


def project_explicit_costs(
    records: Iterable[tuple[str, object]],
) -> dict[str, object]:
    """Project only monetary values whose field name proves the USD unit.

    Opaque ledger units such as ``reserved_minor`` and ``actual_minor`` are
    intentionally ignored. They are accounting units, not evidence that a
    value is denominated in USD.
    """

    projected: list[ExplicitCostRecord] = []
    for request_id, raw_result in records:
        if not request_id:
            raise CostProjectionError("cost record request_id is required")
        payload = _stored_result(raw_result)
        if payload is None:
            continue
        record = _explicit_cost(request_id, payload)
        if record is not None:
            projected.append(record)

    state: dict[str, object] = {
        "currency": "USD",
        "coverage": "explicit_currency_only",
        "records": [record.as_dict() for record in projected],
    }
    if projected:
        state["total_cost_usd"] = sum(record.amount_usd for record in projected)
    return state


def _stored_result(raw_result: object) -> dict[str, object] | None:
    if raw_result is None:
        return None
    try:
        decoded = json.loads(str(raw_result))
    except (TypeError, ValueError, json.JSONDecodeError) as error:
        raise CostProjectionError("stored cost telemetry is malformed") from error
    if not isinstance(decoded, dict):
        raise CostProjectionError("stored cost telemetry is malformed")
    result = decoded.get("result")
    if result is None:
        return None
    if not isinstance(result, dict):
        raise CostProjectionError("stored cost result is malformed")
    return {str(key): value for key, value in result.items()}


def _explicit_cost(
    request_id: str,
    payload: dict[str, object],
) -> ExplicitCostRecord | None:
    for field in _USD_FIELDS:
        if field in payload:
            return ExplicitCostRecord(
                request_id=request_id,
                amount_usd=_money_number(payload[field], field),
                source_field=field,
                source_unit="USD",
            )
    for field in _MICROUSD_FIELDS:
        if field in payload:
            return ExplicitCostRecord(
                request_id=request_id,
                amount_usd=_money_number(payload[field], field) / 1_000_000.0,
                source_field=field,
                source_unit="microUSD",
            )
    return None


def _money_number(value: object, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CostProjectionError(f"{field} must be a numeric monetary value")
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise CostProjectionError(f"{field} must be finite and non-negative")
    return number
