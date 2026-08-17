"""Financial admission and reconciliation for paid Video Factory generations.

No paid provider call may start solely because a model is technically suitable.
A fresh authoritative quote, provider-cost reserve, user revenue authorization,
minimum gross-margin floor and retry reserve are required first. Finance uses
``Decimal`` throughout; floats are rejected at the boundary.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_UP

_CENT = Decimal("0.01")
_BPS = Decimal("10000")


class FinancialAdmissionError(ValueError):
    """Raised for structurally invalid financial evidence."""


@dataclass(frozen=True, slots=True)
class PricingQuote:
    provider_id: str
    model_id: str
    sku: str
    unit_price_usd: Decimal
    unit: str
    captured_at: datetime
    expires_at: datetime
    source: str

    def __post_init__(self) -> None:
        for name, value in (
            ("provider_id", self.provider_id),
            ("model_id", self.model_id),
            ("sku", self.sku),
            ("unit", self.unit),
            ("source", self.source),
        ):
            if not value.strip():
                raise FinancialAdmissionError(f"{name} must not be blank")
        _require_money("unit_price_usd", self.unit_price_usd, allow_zero=True)
        if self.captured_at.tzinfo is None or self.expires_at.tzinfo is None:
            raise FinancialAdmissionError("quote timestamps must be timezone-aware")
        if self.expires_at <= self.captured_at:
            raise FinancialAdmissionError("quote expires_at must be after captured_at")


@dataclass(frozen=True, slots=True)
class GenerationCostRequest:
    """Billable provider quantity for one shot before dispatch."""

    quantity: Decimal
    retry_reserve_count: int = 0

    def __post_init__(self) -> None:
        if isinstance(self.quantity, float):
            raise FinancialAdmissionError("quantity must use Decimal, not float")
        if self.quantity <= 0:
            raise FinancialAdmissionError("quantity must be greater than zero")
        if self.retry_reserve_count < 0:
            raise FinancialAdmissionError("retry_reserve_count must not be negative")


@dataclass(frozen=True, slots=True)
class FinancialAdmissionPolicy:
    """Commercial safety policy; 4000 bps means a 40% minimum gross margin."""

    min_gross_margin_bps: int = 4000
    safety_buffer_bps: int = 2000
    max_quote_age_seconds: int = 300

    def __post_init__(self) -> None:
        if not 0 <= self.min_gross_margin_bps < 10000:
            raise FinancialAdmissionError("min_gross_margin_bps must be in [0, 10000)")
        if self.safety_buffer_bps < 0:
            raise FinancialAdmissionError("safety_buffer_bps must not be negative")
        if self.max_quote_age_seconds <= 0:
            raise FinancialAdmissionError("max_quote_age_seconds must be positive")


@dataclass(frozen=True, slots=True)
class BudgetAuthorization:
    """Pre-authorized commercial envelope for this generation decision."""

    authorized_revenue_usd: Decimal
    reserved_provider_cost_usd: Decimal

    def __post_init__(self) -> None:
        _require_money("authorized_revenue_usd", self.authorized_revenue_usd)
        _require_money("reserved_provider_cost_usd", self.reserved_provider_cost_usd)


@dataclass(frozen=True, slots=True)
class AdmissionDecision:
    allowed: bool
    reason_code: str
    quoted_provider_cost_usd: Decimal
    worst_case_provider_cost_usd: Decimal
    minimum_sale_price_usd: Decimal
    authorized_revenue_usd: Decimal
    reserved_provider_cost_usd: Decimal


@dataclass(frozen=True, slots=True)
class CostReconciliation:
    accepted: bool
    reason_code: str
    actual_provider_cost_usd: Decimal
    reserved_provider_cost_usd: Decimal
    variance_usd: Decimal


def admit_paid_generation(
    *,
    quote: PricingQuote | None,
    request: GenerationCostRequest,
    authorization: BudgetAuthorization | None,
    policy: FinancialAdmissionPolicy,
    now: datetime,
) -> AdmissionDecision:
    """Fail closed unless one paid shot is commercially safe before provider POST."""

    zero = Decimal("0")
    if quote is None:
        return _denied("PRICE_UNKNOWN", zero, zero, zero, authorization)
    if now.tzinfo is None:
        raise FinancialAdmissionError("now must be timezone-aware")
    if now > quote.expires_at:
        return _denied("QUOTE_STALE", zero, zero, zero, authorization)
    age = (now.astimezone(timezone.utc) - quote.captured_at.astimezone(timezone.utc)).total_seconds()
    if age < 0 or age > policy.max_quote_age_seconds:
        return _denied("QUOTE_STALE", zero, zero, zero, authorization)
    if authorization is None:
        quoted = _money(quote.unit_price_usd * request.quantity)
        return _denied("BUDGET_NOT_RESERVED", quoted, quoted, quoted, None)

    quoted_cost = _money(quote.unit_price_usd * request.quantity)
    attempts = Decimal(1 + request.retry_reserve_count)
    buffered_multiplier = Decimal("1") + Decimal(policy.safety_buffer_bps) / _BPS
    worst_case_cost = _money(quoted_cost * attempts * buffered_multiplier)
    margin_fraction = Decimal(policy.min_gross_margin_bps) / _BPS
    minimum_sale_price = _money(worst_case_cost / (Decimal("1") - margin_fraction))

    if authorization.reserved_provider_cost_usd < worst_case_cost:
        return _denied(
            "COST_EXCEEDS_RESERVE",
            quoted_cost,
            worst_case_cost,
            minimum_sale_price,
            authorization,
        )
    if authorization.authorized_revenue_usd < minimum_sale_price:
        return _denied(
            "MARGIN_BELOW_FLOOR",
            quoted_cost,
            worst_case_cost,
            minimum_sale_price,
            authorization,
        )
    return AdmissionDecision(
        allowed=True,
        reason_code="ADMITTED",
        quoted_provider_cost_usd=quoted_cost,
        worst_case_provider_cost_usd=worst_case_cost,
        minimum_sale_price_usd=minimum_sale_price,
        authorized_revenue_usd=authorization.authorized_revenue_usd,
        reserved_provider_cost_usd=authorization.reserved_provider_cost_usd,
    )


def reconcile_provider_cost(
    *,
    actual_provider_cost_usd: Decimal,
    authorization: BudgetAuthorization,
) -> CostReconciliation:
    """Reconcile authoritative terminal charge against the pre-call reserve."""

    _require_money("actual_provider_cost_usd", actual_provider_cost_usd, allow_zero=True)
    variance = _money(actual_provider_cost_usd - authorization.reserved_provider_cost_usd)
    if actual_provider_cost_usd > authorization.reserved_provider_cost_usd:
        return CostReconciliation(
            accepted=False,
            reason_code="ACTUAL_COST_EXCEEDS_RESERVE",
            actual_provider_cost_usd=actual_provider_cost_usd,
            reserved_provider_cost_usd=authorization.reserved_provider_cost_usd,
            variance_usd=variance,
        )
    return CostReconciliation(
        accepted=True,
        reason_code="RECONCILED",
        actual_provider_cost_usd=actual_provider_cost_usd,
        reserved_provider_cost_usd=authorization.reserved_provider_cost_usd,
        variance_usd=variance,
    )


def decimal_from_provider(value: object) -> Decimal:
    """Parse authoritative provider money without accepting binary floats."""

    if isinstance(value, bool) or isinstance(value, float) or value is None:
        raise FinancialAdmissionError("provider money must be an exact string or integer")
    if not isinstance(value, (str, int, Decimal)):
        raise FinancialAdmissionError("provider money has unsupported type")
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise FinancialAdmissionError("provider money is malformed") from exc
    _require_money("provider money", parsed, allow_zero=True)
    return parsed


def _denied(
    reason: str,
    quoted: Decimal,
    worst: Decimal,
    minimum_sale: Decimal,
    authorization: BudgetAuthorization | None,
) -> AdmissionDecision:
    return AdmissionDecision(
        allowed=False,
        reason_code=reason,
        quoted_provider_cost_usd=quoted,
        worst_case_provider_cost_usd=worst,
        minimum_sale_price_usd=minimum_sale,
        authorized_revenue_usd=(
            Decimal("0") if authorization is None else authorization.authorized_revenue_usd
        ),
        reserved_provider_cost_usd=(
            Decimal("0") if authorization is None else authorization.reserved_provider_cost_usd
        ),
    )


def _money(value: Decimal) -> Decimal:
    return value.quantize(_CENT, rounding=ROUND_UP)


def _require_money(name: str, value: Decimal, *, allow_zero: bool = False) -> None:
    if isinstance(value, float) or not isinstance(value, Decimal):
        raise FinancialAdmissionError(f"{name} must be Decimal")
    if not value.is_finite():
        raise FinancialAdmissionError(f"{name} must be finite")
    if value < 0 or (value == 0 and not allow_zero):
        qualifier = "non-negative" if allow_zero else "greater than zero"
        raise FinancialAdmissionError(f"{name} must be {qualifier}")
