from __future__ import annotations

from dataclasses import replace

import pytest

from src.video_automation.commercial_admission import (
    CommercialAdmissionEngine,
    CommercialAdmissionError,
    CommercialPricingPolicy,
    LockedVideoQuote,
    PaymentAuthorization,
    ProviderPricingSnapshot,
    TaxProfile,
    VideoCostEnvelope,
)
from src.video_automation.managed_credits import ProviderCostQuote


def _pricing(*, fingerprint: str = "catalog-price-v1") -> ProviderPricingSnapshot:
    return ProviderPricingSnapshot(
        provider_name="openrouter-video-managed",
        model_id="bytedance/seedance-2.0-fast",
        pricing_fingerprint=fingerprint,
        observed_at_epoch_s=1_000,
        expires_at_epoch_s=2_000,
        estimated_job_cost_microusd=7_000_000,
        max_job_cost_microusd=7_500_000,
    )


def _setup() -> tuple[CommercialAdmissionEngine, LockedVideoQuote]:
    engine = CommercialAdmissionEngine(CommercialPricingPolicy())
    quote = engine.create_locked_quote(
        quote_id="quote-001",
        now_epoch_s=1_000,
        tax_profile=TaxProfile.turkey_general_vat(),
        pricing=_pricing(),
        costs=VideoCostEnvelope(provider_generation_microusd=7_500_000),
        duration_seconds=30,
        aggregate_generated_seconds=30,
        resolution="1080p",
        shot_count=5,
    )
    return engine, quote


def _payment(*, amount: int = 16_500_000, status: str = "SECURED") -> PaymentAuthorization:
    return PaymentAuthorization(
        "pay-auth-001", "quote-001", amount, 1_001, status
    )


def _provider_quote(*, maximum: int = 7_500_000) -> ProviderCostQuote:
    return ProviderCostQuote(
        provider_name="openrouter-video-managed",
        model_id="bytedance/seedance-2.0-fast",
        estimated_cost_microusd=7_000_000,
        max_cost_microusd=maximum,
    )


def test_payment_gate_fails_closed() -> None:
    engine, quote = _setup()
    cases: tuple[tuple[PaymentAuthorization, str], ...] = (
        (_payment(status="PENDING"), "not secured"),
        (_payment(amount=16_499_999), "does not cover"),
        (replace(_payment(), quote_id="other"), "different quote"),
    )
    for payment, message in cases:
        with pytest.raises(CommercialAdmissionError, match=message):
            engine.authorize_paid_dispatch(
                now_epoch_s=1_010,
                quote=quote,
                payment=payment,
                current_pricing=_pricing(),
                provider_quote=_provider_quote(),
            )


def test_changed_pricing_requires_requote_before_paid_dispatch() -> None:
    engine, quote = _setup()
    with pytest.raises(CommercialAdmissionError, match="pricing changed"):
        engine.authorize_paid_dispatch(
            now_epoch_s=1_010,
            quote=quote,
            payment=_payment(),
            current_pricing=_pricing(fingerprint="catalog-price-v2"),
            provider_quote=_provider_quote(),
        )


def test_provider_request_cannot_exceed_locked_ceiling() -> None:
    engine, quote = _setup()
    with pytest.raises(CommercialAdmissionError, match="exceeds locked"):
        engine.authorize_paid_dispatch(
            now_epoch_s=1_010,
            quote=quote,
            payment=_payment(),
            current_pricing=_pricing(),
            provider_quote=_provider_quote(maximum=7_500_001),
        )


def test_valid_payment_and_price_issue_dispatch_authority() -> None:
    engine, quote = _setup()
    authority = engine.authorize_paid_dispatch(
        now_epoch_s=1_010,
        quote=quote,
        payment=_payment(),
        current_pricing=_pricing(),
        provider_quote=_provider_quote(),
    )
    assert authority.quote_sha256 == quote.quote_sha256
    assert authority.payment_authorization_id == "pay-auth-001"
    assert authority.provider_cost_ceiling_microusd == 7_500_000
    assert len(authority.authority_sha256) == 64


def test_reconciliation_quarantines_provider_cost_anomaly() -> None:
    engine, quote = _setup()
    result = engine.reconcile(
        quote=quote,
        actual_provider_cost_microusd=7_500_001,
        actual_other_variable_cost_microusd=0,
    )
    assert result.provider_quarantined is True
    assert "provider cost exceeded" in (result.quarantine_reason or "")


def test_reconciliation_quarantines_hard_floor_margin_breach() -> None:
    engine, quote = _setup()
    result = engine.reconcile(
        quote=quote,
        actual_provider_cost_microusd=7_500_000,
        actual_other_variable_cost_microusd=3_000_000,
    )
    assert result.actual_margin_bps < quote.hard_min_margin_bps
    assert result.provider_quarantined is True
