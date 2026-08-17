from __future__ import annotations

import pytest

from src.video_automation.commercial_admission import (
    CommercialAdmissionEngine,
    CommercialAdmissionError,
    CommercialPricingPolicy,
    LockedVideoQuote,
    ProviderPricingSnapshot,
    TaxProfile,
    VideoCostEnvelope,
)


def _pricing(*, expires_at: int = 2_000, maximum: int = 7_500_000) -> ProviderPricingSnapshot:
    return ProviderPricingSnapshot(
        provider_name="openrouter-video-managed",
        model_id="bytedance/seedance-2.0-fast",
        pricing_fingerprint="catalog-price-v1",
        observed_at_epoch_s=1_000,
        expires_at_epoch_s=expires_at,
        estimated_job_cost_microusd=7_000_000,
        max_job_cost_microusd=maximum,
    )


def _create(
    *,
    policy: CommercialPricingPolicy | None = None,
    tax: TaxProfile | None = None,
) -> tuple[CommercialAdmissionEngine, LockedVideoQuote]:
    engine = CommercialAdmissionEngine(policy or CommercialPricingPolicy())
    quote = engine.create_locked_quote(
        quote_id="quote-001",
        now_epoch_s=1_000,
        tax_profile=tax or TaxProfile.turkey_general_vat(),
        pricing=_pricing(),
        costs=VideoCostEnvelope(provider_generation_microusd=7_500_000),
        duration_seconds=30,
        aggregate_generated_seconds=30,
        resolution="1080p",
        shot_count=5,
    )
    return engine, quote


def test_tr_vat_target_margin_and_contingency_match_canonical_example() -> None:
    _engine, quote = _create()
    assert quote.protected_cost_microusd == 8_250_000
    assert quote.net_price_ex_tax_microusd == 13_750_000
    assert quote.tax_microusd == 2_750_000
    assert quote.gross_customer_price_microusd == 16_500_000
    assert quote.tax_rate_bps == 2_000
    assert quote.target_margin_bps == 4_000
    assert quote.hard_min_margin_bps == 3_000
    assert quote.contingency_bps == 1_000


def test_payment_fee_is_included_without_confusing_markup_and_margin() -> None:
    _engine, quote = _create(
        policy=CommercialPricingPolicy(payment_fee_rate_bps=300)
    )
    assert quote.gross_customer_price_microusd == 17_553_192
    profit = (
        quote.net_price_ex_tax_microusd
        - quote.protected_cost_microusd
        - quote.expected_payment_fee_microusd
    )
    assert profit * 10_000 // quote.net_price_ex_tax_microusd == 4_000


def test_tax_profile_is_explicit_not_global_hard_code() -> None:
    _engine, quote = _create(
        tax=TaxProfile("TEST_ZERO_TAX", "TEST", 0)
    )
    assert quote.tax_microusd == 0
    assert quote.gross_customer_price_microusd == quote.net_price_ex_tax_microusd


def test_locked_quote_never_outlives_pricing_snapshot() -> None:
    engine = CommercialAdmissionEngine(CommercialPricingPolicy())
    quote = engine.create_locked_quote(
        quote_id="quote-001",
        now_epoch_s=1_000,
        tax_profile=TaxProfile.turkey_general_vat(),
        pricing=_pricing(expires_at=1_100),
        costs=VideoCostEnvelope(provider_generation_microusd=7_500_000),
        duration_seconds=30,
        aggregate_generated_seconds=30,
        resolution="1080p",
        shot_count=5,
    )
    assert quote.expires_at_epoch_s == 1_100


def test_stale_pricing_cannot_create_quote() -> None:
    engine = CommercialAdmissionEngine(CommercialPricingPolicy())
    with pytest.raises(CommercialAdmissionError, match="stale"):
        engine.create_locked_quote(
            quote_id="quote-001",
            now_epoch_s=2_000,
            tax_profile=TaxProfile.turkey_general_vat(),
            pricing=_pricing(expires_at=2_000),
            costs=VideoCostEnvelope(provider_generation_microusd=7_500_000),
            duration_seconds=30,
            aggregate_generated_seconds=30,
            resolution="1080p",
            shot_count=5,
        )


def test_quote_hash_binds_retry_repair_cost_material() -> None:
    engine, first = _create()
    second = engine.create_locked_quote(
        quote_id="quote-001",
        now_epoch_s=1_000,
        tax_profile=TaxProfile.turkey_general_vat(),
        pricing=_pricing(maximum=7_500_001),
        costs=VideoCostEnvelope(
            provider_generation_microusd=7_500_000,
            retry_microusd=1,
        ),
        duration_seconds=30,
        aggregate_generated_seconds=30,
        resolution="1080p",
        shot_count=5,
    )
    assert first.quote_sha256 != second.quote_sha256
    assert second.retry_cost_ceiling_microusd == 1


def test_float_money_is_rejected() -> None:
    with pytest.raises(CommercialAdmissionError, match="integer"):
        VideoCostEnvelope(provider_generation_microusd=7_500_000.0)  # type: ignore[arg-type]
