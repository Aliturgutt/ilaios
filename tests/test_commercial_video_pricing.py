from __future__ import annotations

from decimal import Decimal

import pytest

from src.video_automation.adaptive_production import (
    AdaptiveProviderRouter,
    AdaptiveShotPlanner,
    ShotRoutingPolicy,
    VideoModelCapability,
    parse_pricing_skus,
)
from src.video_automation.commercial_pricing import (
    CommercialPricingError,
    CommercialPricingGuard,
    CommercialPricingPolicy,
)


def _paid_routing() -> object:
    plan = AdaptiveShotPlanner().plan(20)
    model = VideoModelCapability(
        provider_id="openrouter-video",
        model_id="bytedance/seedance-current",
        supported_durations=tuple(range(2, 13)),
        supported_resolutions=("720p",),
        supported_aspect_ratios=("16:9",),
        supported_frame_images=("first_frame", "last_frame"),
        supports_audio=True,
        supports_input_references=True,
        pricing_skus=parse_pricing_skus({"per-video-second": "0.05"}),
        quality_rank=90,
    )
    return AdaptiveProviderRouter().route(
        plan,
        (model,),
        ShotRoutingPolicy(
            allow_paid=True,
            max_total_provider_cost_usd=Decimal("2.00"),
            max_cost_per_shot_usd=Decimal("0.50"),
        ),
        resolution="720p",
        aspect_ratio="16:9",
    )


def test_quote_reserves_retries_buffers_fees_and_margin() -> None:
    routing = _paid_routing()
    policy = CommercialPricingPolicy(
        provider_attempt_reserve=2,
        provider_price_buffer_bps=1000,
        fx_buffer_bps=500,
        infrastructure_fixed_usd=Decimal("0.10"),
        infrastructure_per_generated_second_usd=Decimal("0.002"),
        payment_fee_bps=300,
        payment_fixed_fee_usd=Decimal("0.30"),
        minimum_gross_margin_bps=3000,
    )

    quote = CommercialPricingGuard().quote(routing, policy)

    assert quote.estimated_provider_cost_usd == Decimal("1.00")
    assert quote.provider_reserve_usd == Decimal("2.00")
    assert quote.buffered_provider_reserve_usd == Decimal("2.3000")
    assert quote.estimated_infrastructure_cost_usd == Decimal("0.140")
    assert quote.protected_cost_basis_usd == Decimal("2.4400")
    assert quote.minimum_customer_net_price_usd > Decimal("3.90")


def test_checkout_below_floor_is_rejected() -> None:
    routing = _paid_routing()
    policy = CommercialPricingPolicy(
        provider_attempt_reserve=1,
        provider_price_buffer_bps=0,
        fx_buffer_bps=0,
        infrastructure_fixed_usd=Decimal("0"),
        infrastructure_per_generated_second_usd=Decimal("0"),
        payment_fee_bps=0,
        payment_fixed_fee_usd=Decimal("0"),
        minimum_gross_margin_bps=2500,
    )
    guard = CommercialPricingGuard()
    quote = guard.quote(routing, policy)

    with pytest.raises(CommercialPricingError, match="below"):
        guard.assert_charge_is_safe(
            quote,
            customer_net_price_usd=quote.minimum_customer_net_price_usd
            - Decimal("0.01"),
        )


def test_free_provider_route_still_prices_nonzero_infrastructure() -> None:
    plan = AdaptiveShotPlanner().plan(10)
    model = VideoModelCapability(
        provider_id="openrouter-video",
        model_id="provider/free",
        supported_durations=tuple(range(2, 13)),
        supported_resolutions=("720p",),
        supported_aspect_ratios=("16:9",),
        supported_frame_images=("first_frame", "last_frame"),
        supports_audio=True,
        supports_input_references=True,
        pricing_skus=parse_pricing_skus({"per-video-second": "0"}),
    )
    routing = AdaptiveProviderRouter().route(
        plan,
        (model,),
        ShotRoutingPolicy(),
        resolution="720p",
        aspect_ratio="16:9",
    )
    quote = CommercialPricingGuard().quote(
        routing,
        CommercialPricingPolicy(
            provider_attempt_reserve=1,
            provider_price_buffer_bps=0,
            fx_buffer_bps=0,
            infrastructure_fixed_usd=Decimal("0.05"),
            infrastructure_per_generated_second_usd=Decimal("0.001"),
            payment_fee_bps=0,
            payment_fixed_fee_usd=Decimal("0"),
            minimum_gross_margin_bps=0,
        ),
    )

    assert quote.is_zero_provider_cost
    assert quote.minimum_customer_net_price_usd == Decimal("0.06")


def test_invalid_paid_business_assumptions_fail_closed() -> None:
    with pytest.raises(CommercialPricingError):
        CommercialPricingPolicy(
            provider_attempt_reserve=0,
            provider_price_buffer_bps=0,
            fx_buffer_bps=0,
            infrastructure_fixed_usd=Decimal("0"),
            infrastructure_per_generated_second_usd=Decimal("0"),
            payment_fee_bps=0,
            payment_fixed_fee_usd=Decimal("0"),
            minimum_gross_margin_bps=0,
        )
