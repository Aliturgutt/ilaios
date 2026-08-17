from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from src.video_automation.video_financial_admission import (
    BudgetAuthorization,
    FinancialAdmissionError,
    FinancialAdmissionPolicy,
    GenerationCostRequest,
    PricingQuote,
    admit_paid_generation,
    decimal_from_provider,
    reconcile_provider_cost,
)


NOW = datetime(2026, 8, 17, 12, 0, tzinfo=timezone.utc)


def _quote(*, price: str = "0.04", captured_at: datetime = NOW) -> PricingQuote:
    return PricingQuote(
        provider_id="openrouter",
        model_id="catalog/model",
        sku="video_second",
        unit_price_usd=Decimal(price),
        unit="second",
        captured_at=captured_at,
        expires_at=captured_at + timedelta(minutes=10),
        source="authoritative-live-catalog",
    )


def test_paid_generation_is_admitted_only_with_reserve_and_margin() -> None:
    decision = admit_paid_generation(
        quote=_quote(),
        request=GenerationCostRequest(quantity=Decimal("5"), retry_reserve_count=1),
        authorization=BudgetAuthorization(
            authorized_revenue_usd=Decimal("1.00"),
            reserved_provider_cost_usd=Decimal("0.50"),
        ),
        policy=FinancialAdmissionPolicy(
            min_gross_margin_bps=4000,
            safety_buffer_bps=2000,
        ),
        now=NOW,
    )

    assert decision.allowed
    assert decision.reason_code == "ADMITTED"
    assert decision.quoted_provider_cost_usd == Decimal("0.20")
    assert decision.worst_case_provider_cost_usd == Decimal("0.48")
    assert decision.minimum_sale_price_usd == Decimal("0.80")


def test_unknown_price_fails_closed() -> None:
    decision = admit_paid_generation(
        quote=None,
        request=GenerationCostRequest(quantity=Decimal("5")),
        authorization=BudgetAuthorization(
            authorized_revenue_usd=Decimal("10"),
            reserved_provider_cost_usd=Decimal("10"),
        ),
        policy=FinancialAdmissionPolicy(),
        now=NOW,
    )

    assert not decision.allowed
    assert decision.reason_code == "PRICE_UNKNOWN"


def test_stale_quote_fails_closed() -> None:
    captured = NOW - timedelta(minutes=20)
    decision = admit_paid_generation(
        quote=_quote(captured_at=captured),
        request=GenerationCostRequest(quantity=Decimal("5")),
        authorization=BudgetAuthorization(
            authorized_revenue_usd=Decimal("10"),
            reserved_provider_cost_usd=Decimal("10"),
        ),
        policy=FinancialAdmissionPolicy(max_quote_age_seconds=300),
        now=NOW,
    )

    assert not decision.allowed
    assert decision.reason_code == "QUOTE_STALE"


def test_missing_reserve_fails_closed() -> None:
    decision = admit_paid_generation(
        quote=_quote(),
        request=GenerationCostRequest(quantity=Decimal("5")),
        authorization=None,
        policy=FinancialAdmissionPolicy(),
        now=NOW,
    )

    assert not decision.allowed
    assert decision.reason_code == "BUDGET_NOT_RESERVED"


def test_insufficient_provider_reserve_fails_closed() -> None:
    decision = admit_paid_generation(
        quote=_quote(),
        request=GenerationCostRequest(quantity=Decimal("5"), retry_reserve_count=1),
        authorization=BudgetAuthorization(
            authorized_revenue_usd=Decimal("10"),
            reserved_provider_cost_usd=Decimal("0.47"),
        ),
        policy=FinancialAdmissionPolicy(),
        now=NOW,
    )

    assert not decision.allowed
    assert decision.reason_code == "COST_EXCEEDS_RESERVE"


def test_margin_below_floor_fails_closed() -> None:
    decision = admit_paid_generation(
        quote=_quote(),
        request=GenerationCostRequest(quantity=Decimal("5")),
        authorization=BudgetAuthorization(
            authorized_revenue_usd=Decimal("0.39"),
            reserved_provider_cost_usd=Decimal("1.00"),
        ),
        policy=FinancialAdmissionPolicy(),
        now=NOW,
    )

    assert not decision.allowed
    assert decision.reason_code == "MARGIN_BELOW_FLOOR"


def test_terminal_actual_cost_cannot_exceed_reserved_provider_cost() -> None:
    authorization = BudgetAuthorization(
        authorized_revenue_usd=Decimal("5"),
        reserved_provider_cost_usd=Decimal("0.50"),
    )

    accepted = reconcile_provider_cost(
        actual_provider_cost_usd=Decimal("0.42"),
        authorization=authorization,
    )
    rejected = reconcile_provider_cost(
        actual_provider_cost_usd=Decimal("0.51"),
        authorization=authorization,
    )

    assert accepted.accepted
    assert accepted.reason_code == "RECONCILED"
    assert not rejected.accepted
    assert rejected.reason_code == "ACTUAL_COST_EXCEEDS_RESERVE"


@pytest.mark.parametrize("value", [0.1, None, True, object()])
def test_provider_money_rejects_inexact_or_unsupported_values(value: object) -> None:
    with pytest.raises(FinancialAdmissionError):
        decimal_from_provider(value)


def test_provider_money_parses_exact_strings() -> None:
    assert decimal_from_provider("0.1704948") == Decimal("0.1704948")
