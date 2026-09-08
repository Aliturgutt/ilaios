from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import pytest

from src.video_automation.commercial_admission import (
    CommercialAdmissionError,
    CommercialCostConfig,
    FreeOperationAdmission,
    FxRateSnapshot,
    ProviderPricingSnapshot,
    TaxProfile,
    authorize_free_operation,
    create_governed_locked_quote,
)
from src.video_automation.managed_credit_store import ManagedCreditLedgerStore


_NOW = 1_000


def _fx(*, expires_at: int = 2_000) -> FxRateSnapshot:
    return FxRateSnapshot(
        source="admin-timestamped-test-rate",
        usd_try=Decimal("48.45"),
        observed_at_epoch_s=_NOW,
        expires_at_epoch_s=expires_at,
    )


def _pricing(*, expires_at: int = 2_000) -> ProviderPricingSnapshot:
    return ProviderPricingSnapshot(
        provider_name="openrouter-video-managed",
        model_id="bytedance/seedance-2.0-fast",
        pricing_fingerprint="verified-price-v1",
        observed_at_epoch_s=_NOW,
        expires_at_epoch_s=expires_at,
        estimated_job_cost_microusd=1_000_000,
        max_job_cost_microusd=1_200_000,
    )


def _ready_config() -> CommercialCostConfig:
    return CommercialCostConfig(
        render_monthly_usd=Decimal("25"),
        cloudflare_monthly_usd=Decimal("5"),
        income_tax_reserve_bps=1_500,
    )


def _authorize_free(
    store: ManagedCreditLedgerStore,
    *,
    request_id: str,
    tenant_id: str = "tenant-a",
    provider_cost_microusd: int = 0,
    config: CommercialCostConfig | None = None,
) -> FreeOperationAdmission:
    return authorize_free_operation(
        store=store,
        config=config or CommercialCostConfig(),
        request_id=request_id,
        tenant_id=tenant_id,
        user_id="user-a",
        month_key="2026-09",
        provider_name="openrouter",
        model_id="openrouter/free" if provider_cost_microusd == 0 else "not-free",
        provider_cost_microusd=provider_cost_microusd,
        platform_free_budget_allowed=True,
        now_epoch_s=_NOW,
    )


def test_initial_cost_config_matches_locked_business_inputs() -> None:
    config = CommercialCostConfig()
    assert config.fixed_base_monthly_try == Decimal("65500")
    assert config.domain_email_monthly_try == Decimal("500")
    assert config.accounting_monthly_try == Decimal("10000")
    assert config.labor_monthly_try == Decimal("40000")
    assert config.internet_and_other_subscriptions_monthly_try == Decimal("15000")
    assert config.vercel_monthly_usd == Decimal("20")
    assert config.storage_backup_per_active_user_monthly_try == Decimal("10")
    assert config.payment_fee_reserve_bps == 500
    assert config.usd_try_fx_buffer_bps == 500
    assert config.target_minimum_net_operating_profit_margin_bps == 4_000
    assert config.free_operations_per_active_user_per_month == 100


def test_paid_quote_fails_closed_when_unverified_cost_inputs_are_missing() -> None:
    with pytest.raises(CommercialAdmissionError, match="render_monthly_usd"):
        create_governed_locked_quote(
            config=CommercialCostConfig(),
            fx=_fx(),
            quote_id="quote-missing-cost",
            now_epoch_s=_NOW,
            tax_profile=TaxProfile.turkey_general_vat(),
            pricing=_pricing(),
            provider_generation_microusd=1_000_000,
            retry_microusd=100_000,
            repair_microusd=100_000,
            active_users=100,
            chargeable_operations_per_active_user_month=10,
            duration_seconds=10,
            aggregate_generated_seconds=10,
            resolution="720p",
            shot_count=1,
        )


def test_paid_quote_fails_closed_on_stale_fx() -> None:
    stale_fx = FxRateSnapshot(
        source="stale-admin-rate",
        usd_try=Decimal("48.45"),
        observed_at_epoch_s=900,
        expires_at_epoch_s=_NOW,
    )
    with pytest.raises(CommercialAdmissionError, match="stale"):
        create_governed_locked_quote(
            config=_ready_config(),
            fx=stale_fx,
            quote_id="quote-stale-fx",
            now_epoch_s=_NOW,
            tax_profile=TaxProfile.turkey_general_vat(),
            pricing=_pricing(),
            provider_generation_microusd=1_000_000,
            retry_microusd=100_000,
            repair_microusd=100_000,
            active_users=100,
            chargeable_operations_per_active_user_month=10,
            duration_seconds=10,
            aggregate_generated_seconds=10,
            resolution="720p",
            shot_count=1,
        )


def test_governed_quote_includes_fx_fixed_cost_tax_reserve_paytr_and_40_percent_margin() -> None:
    quote, allocation = create_governed_locked_quote(
        config=_ready_config(),
        fx=_fx(),
        quote_id="quote-governed",
        now_epoch_s=_NOW,
        tax_profile=TaxProfile.turkey_general_vat(),
        pricing=_pricing(),
        provider_generation_microusd=1_000_000,
        retry_microusd=100_000,
        repair_microusd=100_000,
        active_users=100,
        chargeable_operations_per_active_user_month=10,
        duration_seconds=10,
        aggregate_generated_seconds=10,
        resolution="720p",
        shot_count=1,
    )
    assert allocation.fixed_cost_share_microusd > 0
    assert allocation.storage_backup_share_microusd > 0
    assert allocation.infrastructure_share_microusd > 0
    assert allocation.fx_reserve_microusd == 60_000
    assert allocation.income_tax_reserve_microusd > 0
    assert quote.payment_fee_rate_bps == 500
    assert quote.target_margin_bps == 4_000
    assert quote.hard_min_margin_bps == 4_000
    assert quote.tax_rate_bps == 2_000
    profit = (
        quote.net_price_ex_tax_microusd
        - quote.protected_cost_microusd
        - quote.expected_payment_fee_microusd
    )
    assert profit * 10_000 // quote.net_price_ex_tax_microusd >= 4_000


def test_free_admission_requires_exact_zero_cost_and_never_silently_falls_back(
    tmp_path: Path,
) -> None:
    store = ManagedCreditLedgerStore(tmp_path)
    with pytest.raises(CommercialAdmissionError, match="paid quote required"):
        _authorize_free(
            store,
            request_id="paid-cost-request",
            provider_cost_microusd=1,
        )


def test_free_admission_is_idempotent_tenant_user_scoped_and_quota_bounded(
    tmp_path: Path,
) -> None:
    store = ManagedCreditLedgerStore(tmp_path)
    first = _authorize_free(store, request_id="free-request-001")
    repeated = _authorize_free(store, request_id="free-request-001")
    assert first.ordinal == repeated.ordinal == 1
    assert first.monthly_limit == 100

    for ordinal in range(2, 101):
        admitted = _authorize_free(store, request_id=f"free-request-{ordinal:03d}")
        assert admitted.ordinal == ordinal

    with pytest.raises(CommercialAdmissionError, match="quota exhausted"):
        _authorize_free(store, request_id="free-request-101")

    other_tenant = _authorize_free(
        store,
        request_id="other-tenant-001",
        tenant_id="tenant-b",
    )
    assert other_tenant.ordinal == 1


def test_free_quota_cannot_be_overridden_outside_config(tmp_path: Path) -> None:
    store = ManagedCreditLedgerStore(tmp_path)
    config = replace(
        CommercialCostConfig(),
        free_operations_per_active_user_per_month=1,
    )
    admitted = _authorize_free(store, request_id="bounded-001", config=config)
    assert admitted.monthly_limit == 1

    with pytest.raises(CommercialAdmissionError, match="quota exhausted"):
        _authorize_free(store, request_id="bounded-002", config=config)
