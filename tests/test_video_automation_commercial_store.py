from __future__ import annotations

from pathlib import Path

import pytest

from src.video_automation.commercial_admission import (
    CommercialAdmissionEngine,
    CommercialAdmissionError,
    CommercialDispatchAuthority,
    CommercialPricingPolicy,
    LockedVideoQuote,
    PaymentAuthorization,
    ProviderPricingSnapshot,
    TaxProfile,
    VideoCostEnvelope,
)
from src.video_automation.commercial_store import CommercialAuthorityStore
from src.video_automation.managed_credits import ProviderCostQuote


def _commercial_setup(
    root: Path,
    *,
    provider_ceiling: int = 1_000_000,
) -> tuple[
    CommercialAuthorityStore,
    LockedVideoQuote,
    PaymentAuthorization,
    CommercialDispatchAuthority,
    ProviderCostQuote,
]:
    engine = CommercialAdmissionEngine(CommercialPricingPolicy())
    pricing = ProviderPricingSnapshot(
        provider_name="openrouter-video-managed",
        model_id="kwaivgi/kling-v3.0-pro",
        pricing_fingerprint="catalog-digest-v1",
        observed_at_epoch_s=1_000,
        expires_at_epoch_s=2_000,
        estimated_job_cost_microusd=400_000,
        max_job_cost_microusd=500_000,
    )
    quote = engine.create_locked_quote(
        quote_id="quote-001",
        now_epoch_s=1_000,
        tax_profile=TaxProfile.turkey_general_vat(),
        pricing=pricing,
        costs=VideoCostEnvelope(provider_generation_microusd=provider_ceiling),
        duration_seconds=20,
        aggregate_generated_seconds=20,
        resolution="720p",
        shot_count=2,
    )
    payment = PaymentAuthorization(
        payment_authorization_id="payment-001",
        quote_id=quote.quote_id,
        secured_amount_microusd=quote.gross_customer_price_microusd,
        secured_at_epoch_s=1_001,
    )
    provider_quote = ProviderCostQuote(
        provider_name=pricing.provider_name,
        model_id=pricing.model_id,
        estimated_cost_microusd=400_000,
        max_cost_microusd=500_000,
    )
    authority = engine.authorize_paid_dispatch(
        now_epoch_s=1_002,
        quote=quote,
        payment=payment,
        current_pricing=pricing,
        provider_quote=provider_quote,
    )
    store = CommercialAuthorityStore(root)
    store.record_quote(quote)
    store.record_payment(payment)
    store.record_authority(authority)
    return store, quote, payment, authority, provider_quote


def test_unpersisted_authority_is_not_trusted(tmp_path: Path) -> None:
    store, _quote, _payment, authority, provider_quote = _commercial_setup(tmp_path)
    forged = type(authority)(
        authority_sha256="forged-authority",
        quote_id=authority.quote_id,
        quote_sha256=authority.quote_sha256,
        payment_authorization_id=authority.payment_authorization_id,
        provider_name=authority.provider_name,
        model_id=authority.model_id,
        pricing_fingerprint=authority.pricing_fingerprint,
        provider_cost_ceiling_microusd=authority.provider_cost_ceiling_microusd,
        issued_at_epoch_s=authority.issued_at_epoch_s,
        expires_at_epoch_s=authority.expires_at_epoch_s,
    )
    with pytest.raises(CommercialAdmissionError, match="not durably trusted"):
        store.reserve_request(
            authority=forged,
            request_id="request-forged",
            provider_quote=provider_quote,
            now_epoch_s=1_003,
        )


def test_quote_budget_is_atomically_consumed_across_store_instances(tmp_path: Path) -> None:
    store, _quote, _payment, authority, provider_quote = _commercial_setup(tmp_path)
    second_process = CommercialAuthorityStore(tmp_path)
    first = store.reserve_request(
        authority=authority,
        request_id="request-001",
        provider_quote=provider_quote,
        now_epoch_s=1_003,
    )
    second = second_process.reserve_request(
        authority=authority,
        request_id="request-002",
        provider_quote=provider_quote,
        now_epoch_s=1_004,
    )
    assert first.max_cost_microusd == 500_000
    assert second.max_cost_microusd == 500_000
    with pytest.raises(CommercialAdmissionError, match="budget is exhausted"):
        store.reserve_request(
            authority=authority,
            request_id="request-003",
            provider_quote=ProviderCostQuote(
                provider_name=provider_quote.provider_name,
                model_id=provider_quote.model_id,
                estimated_cost_microusd=1,
                max_cost_microusd=1,
            ),
            now_epoch_s=1_005,
        )


def test_single_request_identity_cannot_reserve_twice(tmp_path: Path) -> None:
    store, _quote, _payment, authority, provider_quote = _commercial_setup(tmp_path)
    store.reserve_request(
        authority=authority,
        request_id="request-001",
        provider_quote=provider_quote,
        now_epoch_s=1_003,
    )
    with pytest.raises(CommercialAdmissionError, match="single-use"):
        store.reserve_request(
            authority=authority,
            request_id="request-001",
            provider_quote=provider_quote,
            now_epoch_s=1_004,
        )


def test_cost_overrun_quarantines_provider_model(tmp_path: Path) -> None:
    store, _quote, _payment, authority, provider_quote = _commercial_setup(tmp_path)
    store.reserve_request(
        authority=authority,
        request_id="request-001",
        provider_quote=provider_quote,
        now_epoch_s=1_003,
    )
    violated = store.settle_request(
        request_id="request-001",
        actual_cost_microusd=500_001,
    )
    assert violated is True
    assert store.is_provider_quarantined(
        provider_name=provider_quote.provider_name,
        model_id=provider_quote.model_id,
    )
    with pytest.raises(CommercialAdmissionError, match="quarantined"):
        store.reserve_request(
            authority=authority,
            request_id="request-002",
            provider_quote=provider_quote,
            now_epoch_s=1_004,
        )


def test_pre_dispatch_failure_can_release_unspent_budget(tmp_path: Path) -> None:
    store, _quote, _payment, authority, provider_quote = _commercial_setup(tmp_path)
    store.reserve_request(
        authority=authority,
        request_id="request-001",
        provider_quote=provider_quote,
        now_epoch_s=1_003,
    )
    store.release_request("request-001")
    store.reserve_request(
        authority=authority,
        request_id="request-002",
        provider_quote=provider_quote,
        now_epoch_s=1_004,
    )
