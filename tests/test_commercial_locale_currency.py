import sqlite3
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import pytest

from src.video_automation.commercial_cost_config import FxRateSnapshot
from src.video_automation.commercial_dispatch import authorize_paid_dispatch
from src.video_automation.commercial_quote import LockedVideoQuote, PaymentAuthorization
from src.video_automation.commercial_quote_engine import CommercialQuoteEngine
from src.video_automation.commercial_store import _SCHEMA, CommercialAuthorityStore
from src.video_automation.commercial_types import (
    CommercialAdmissionError,
    CommercialPricingPolicy,
    ProviderPricingSnapshot,
    TaxProfile,
    VideoCostEnvelope,
)
from src.video_automation.managed_credits import ProviderCostQuote


def pricing() -> ProviderPricingSnapshot:
    return ProviderPricingSnapshot("provider", "model", "price-v1", 1000, 2000, 1_000_000, 1_000_000)


def quote(locale: str | None = "tr", **overrides: object) -> LockedVideoQuote:
    values: dict[str, object] = {
        "quote_id": "quote", "now_epoch_s": 1000,
        "tax_profile": TaxProfile("billing-profile", "TEST", 2000),
        "pricing": pricing(), "costs": VideoCostEnvelope(provider_generation_microusd=1_000_000),
        "duration_seconds": 1, "aggregate_generated_seconds": 1, "resolution": "480p", "shot_count": 1,
        "checkout_locale": locale, "payment_currencies": frozenset({"TRY", "USD"}),
        "checkout_usd_try": Decimal("40.123456"), "checkout_fx_evidence": "test-rate|40.123456|1000|1100",
        "checkout_fx_expires_at": 1100,
    }
    values.update(overrides)
    return CommercialQuoteEngine(CommercialPricingPolicy()).create_locked_quote(**values)  # type: ignore[arg-type]


def payment(q: LockedVideoQuote) -> PaymentAuthorization:
    return PaymentAuthorization("payment", q.quote_id, q.gross_customer_price_microusd, 1000,
                                currency=q.currency, secured_amount_minor=q.customer_amount_minor)


@pytest.mark.parametrize("locale,currency,amount", [("tr", "TRY", 8828), ("tr-TR", "TRY", 8828),
                                                    ("en", "USD", 221), ("en-US", "USD", 221)])
def test_locale_locks_real_payment_amount_and_preserves_tax(locale: str, currency: str, amount: int) -> None:
    q = quote(locale)
    assert q.currency == currency
    assert q.customer_amount_minor == amount
    assert q.gross_customer_price_microusd == 2_200_001
    assert q.tax_profile_id == "billing-profile"
    assert q.tax_rate_bps == 2000
    payment(q).require_secured_for(q)


def test_tr_quote_expires_with_fx_and_changes_economic_hash() -> None:
    tr, en = quote("tr"), quote("en")
    assert tr.expires_at_epoch_s == 1100
    assert tr.quote_sha256 != en.quote_sha256
    with pytest.raises(CommercialAdmissionError, match="expired"):
        tr.require_valid(1100)


@pytest.mark.parametrize("changes", [
    {"checkout_usd_try": None}, {"checkout_usd_try": Decimal("NaN")},
    {"checkout_usd_try": Decimal(0)}, {"checkout_usd_try": 40.0},
    {"checkout_fx_evidence": None}, {"checkout_fx_expires_at": 1000},
    {"payment_currencies": frozenset()}, {"payment_currencies": frozenset({"USD"})},
])
def test_unproven_try_checkout_fails_closed(changes: dict[str, object]) -> None:
    with pytest.raises(CommercialAdmissionError):
        quote(**changes)


def test_unconfirmed_usd_and_unknown_locale_cannot_fallback() -> None:
    with pytest.raises(CommercialAdmissionError, match="support"):
        quote("en", payment_currencies=frozenset({"TRY"}))
    with pytest.raises(CommercialAdmissionError, match="locale"):
        quote("de")


def test_wrong_currency_or_amount_rejected_in_memory_and_durable_store(tmp_path: Path) -> None:
    q = quote()
    store = CommercialAuthorityStore(tmp_path)
    store.record_quote(q)
    good = payment(q)
    for bad in (replace(good, currency="USD"), replace(good, secured_amount_minor=1),
                replace(good, secured_amount_minor=100_000)):
        with pytest.raises(CommercialAdmissionError):
            bad.require_secured_for(q)
        with pytest.raises(CommercialAdmissionError):
            store.record_payment(bad)
    store.record_payment(good)
    store.record_payment(good)
    authority = authorize_paid_dispatch(now_epoch_s=1000, quote=q, payment=good,
        current_pricing=pricing(), provider_quote=ProviderCostQuote("provider", "model", 1_000_000, 1_000_000))
    store.record_authority(authority)
    restarted = CommercialAuthorityStore(tmp_path)
    restarted.verify_authority(authority, now_epoch_s=1001)
    with restarted._connect() as db:
        db.execute("UPDATE commercial_payments SET currency='USD'")
    with pytest.raises(CommercialAdmissionError, match="currency"):
        restarted.verify_authority(authority, now_epoch_s=1001)


def test_legacy_database_migration_preserves_old_usd_quote(tmp_path: Path) -> None:
    q = quote(None)
    path = tmp_path / "video_commercial_finops.sqlite3"
    with sqlite3.connect(path) as db:
        db.executescript(_SCHEMA)
        db.execute("INSERT INTO commercial_quotes VALUES (?,?,?,?,?,?,?,?,?,?)",
                   CommercialAuthorityStore._quote_values(q)[:10])
    store = CommercialAuthorityStore(tmp_path)
    store.record_quote(q)
    store.record_payment(payment(q))
    CommercialAuthorityStore(tmp_path).record_quote(q)


def test_currency_cannot_just_relabel_usd_amount() -> None:
    with pytest.raises(CommercialAdmissionError, match="locale"):
        quote(None, currency="TRY")


def test_future_fx_observation_rejected() -> None:
    with pytest.raises(CommercialAdmissionError, match="future"):
        FxRateSnapshot("test", Decimal(40), 1100, 1200).require_fresh(1000)
