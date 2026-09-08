"""Versioned cost configuration for the existing commercial quote authority.

The values here are operating inputs, not claims about live invoices or production
pricing.  Unknown provider/infrastructure costs stay ``None`` and therefore fail
closed when a governed paid quote is requested.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal, InvalidOperation, ROUND_CEILING

from .commercial_quote import LockedVideoQuote
from .commercial_quote_engine import CommercialQuoteEngine
from .commercial_types import (
    BPS,
    CommercialAdmissionError,
    CommercialPricingPolicy,
    ProviderPricingSnapshot,
    TaxProfile,
    VideoCostEnvelope,
    nonnegative_int,
    positive_int,
    rate_bps,
    require_text,
)
from .managed_credits import usd_to_microusd


@dataclass(frozen=True, slots=True)
class FxRateSnapshot:
    """Timestamped USD/TRY input used for one quote calculation."""

    source: str
    usd_try: Decimal
    observed_at_epoch_s: int
    expires_at_epoch_s: int

    def __post_init__(self) -> None:
        require_text("source", self.source)
        nonnegative_int("observed_at_epoch_s", self.observed_at_epoch_s)
        positive_int("expires_at_epoch_s", self.expires_at_epoch_s)
        try:
            rate = Decimal(self.usd_try)
        except (InvalidOperation, TypeError) as exc:
            raise CommercialAdmissionError("USD/TRY rate must be numeric") from exc
        if not rate.is_finite() or rate <= 0:
            raise CommercialAdmissionError("USD/TRY rate must be positive and finite")
        object.__setattr__(self, "usd_try", rate)
        if self.observed_at_epoch_s >= self.expires_at_epoch_s:
            raise CommercialAdmissionError("FX snapshot lifetime is invalid")

    def require_fresh(self, now_epoch_s: int) -> None:
        nonnegative_int("now_epoch_s", now_epoch_s)
        if now_epoch_s >= self.expires_at_epoch_s:
            raise CommercialAdmissionError("USD/TRY rate is stale; paid quote forbidden")


@dataclass(frozen=True, slots=True)
class CommercialCostConfig:
    """Changeable commercial cost inputs for the canonical quote engine."""

    version: str = "2026-09-08-initial"
    domain_email_monthly_try: Decimal = Decimal("500")
    accounting_monthly_try: Decimal = Decimal("10000")
    labor_monthly_try: Decimal = Decimal("40000")
    internet_and_other_subscriptions_monthly_try: Decimal = Decimal("15000")
    fixed_base_monthly_try: Decimal = Decimal("65500")
    render_monthly_usd: Decimal | None = None
    vercel_monthly_usd: Decimal | None = Decimal("20")
    cloudflare_monthly_usd: Decimal | None = None
    storage_backup_per_active_user_monthly_try: Decimal = Decimal("10")
    payment_fee_reserve_bps: int = 500
    usd_try_fx_buffer_bps: int = 500
    target_minimum_net_operating_profit_margin_bps: int = 4000
    free_operations_per_active_user_per_month: int = 100
    income_tax_reserve_bps: int | None = None

    def __post_init__(self) -> None:
        require_text("version", self.version)
        for name in (
            "domain_email_monthly_try",
            "accounting_monthly_try",
            "labor_monthly_try",
            "internet_and_other_subscriptions_monthly_try",
            "fixed_base_monthly_try",
            "storage_backup_per_active_user_monthly_try",
        ):
            value = _decimal(name, getattr(self, name), allow_zero=True)
            object.__setattr__(self, name, value)
        for name in ("render_monthly_usd", "vercel_monthly_usd", "cloudflare_monthly_usd"):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, _decimal(name, value, allow_zero=True))
        rate_bps("payment_fee_reserve_bps", self.payment_fee_reserve_bps)
        rate_bps("usd_try_fx_buffer_bps", self.usd_try_fx_buffer_bps)
        rate_bps(
            "target_minimum_net_operating_profit_margin_bps",
            self.target_minimum_net_operating_profit_margin_bps,
        )
        positive_int(
            "free_operations_per_active_user_per_month",
            self.free_operations_per_active_user_per_month,
        )
        if self.income_tax_reserve_bps is not None:
            rate_bps("income_tax_reserve_bps", self.income_tax_reserve_bps)
        components = (
            self.domain_email_monthly_try
            + self.accounting_monthly_try
            + self.labor_monthly_try
            + self.internet_and_other_subscriptions_monthly_try
        )
        if components != self.fixed_base_monthly_try:
            raise CommercialAdmissionError(
                "fixed_base_monthly_try must equal the configured fixed-cost components"
            )

    def require_paid_quote_ready(self) -> None:
        missing: list[str] = []
        if self.render_monthly_usd is None:
            missing.append("render_monthly_usd")
        if self.vercel_monthly_usd is None:
            missing.append("vercel_monthly_usd")
        if self.cloudflare_monthly_usd is None:
            missing.append("cloudflare_monthly_usd")
        if self.income_tax_reserve_bps is None:
            missing.append("income_tax_reserve_bps")
        if missing:
            raise CommercialAdmissionError(
                "paid quote cost config incomplete: " + ", ".join(missing)
            )

    def pricing_policy(self, *, quote_ttl_seconds: int = 300) -> CommercialPricingPolicy:
        """Map config into the existing quote authority; no second quote engine."""

        self.require_paid_quote_ready()
        return CommercialPricingPolicy(
            target_margin_bps=self.target_minimum_net_operating_profit_margin_bps,
            hard_min_margin_bps=self.target_minimum_net_operating_profit_margin_bps,
            contingency_bps=0,
            payment_fee_rate_bps=self.payment_fee_reserve_bps,
            payment_fixed_fee_microusd=0,
            quote_ttl_seconds=quote_ttl_seconds,
        )


@dataclass(frozen=True, slots=True)
class CommercialCostAllocation:
    """Evidence-bearing cost allocation fed into the existing VideoCostEnvelope."""

    active_users: int
    chargeable_operations_per_active_user_month: int
    fixed_cost_share_microusd: int
    storage_backup_share_microusd: int
    infrastructure_share_microusd: int
    fx_reserve_microusd: int
    income_tax_reserve_microusd: int
    fx_source: str
    fx_observed_at_epoch_s: int
    fx_expires_at_epoch_s: int
    config_version: str


def create_governed_locked_quote(
    *,
    config: CommercialCostConfig,
    fx: FxRateSnapshot,
    quote_id: str,
    now_epoch_s: int,
    tax_profile: TaxProfile,
    pricing: ProviderPricingSnapshot,
    provider_generation_microusd: int,
    retry_microusd: int,
    repair_microusd: int,
    active_users: int,
    chargeable_operations_per_active_user_month: int,
    duration_seconds: int,
    aggregate_generated_seconds: int,
    resolution: str,
    shot_count: int,
    voice_audio_microusd: int = 0,
    other_variable_microusd: int = 0,
    quote_ttl_seconds: int = 300,
) -> tuple[LockedVideoQuote, CommercialCostAllocation]:
    """Fail-closed governed entrypoint into the existing CommercialQuoteEngine."""

    config.require_paid_quote_ready()
    fx.require_fresh(now_epoch_s)
    pricing.require_fresh(now_epoch_s)
    positive_int("active_users", active_users)
    positive_int(
        "chargeable_operations_per_active_user_month",
        chargeable_operations_per_active_user_month,
    )
    positive_int("provider_generation_microusd", provider_generation_microusd)
    for name, value in (
        ("retry_microusd", retry_microusd),
        ("repair_microusd", repair_microusd),
        ("voice_audio_microusd", voice_audio_microusd),
        ("other_variable_microusd", other_variable_microusd),
    ):
        nonnegative_int(name, value)

    denominator = active_users * chargeable_operations_per_active_user_month
    fixed_share = _try_monthly_share_to_microusd(
        config.fixed_base_monthly_try,
        denominator=denominator,
        usd_try=fx.usd_try,
    )
    storage_share = _try_monthly_share_to_microusd(
        config.storage_backup_per_active_user_monthly_try * active_users,
        denominator=denominator,
        usd_try=fx.usd_try,
    )
    infrastructure_monthly_microusd = sum(
        usd_to_microusd(value)
        for value in (
            config.render_monthly_usd,
            config.vercel_monthly_usd,
            config.cloudflare_monthly_usd,
        )
        if value is not None
    )
    infrastructure_share = _ceil_div(infrastructure_monthly_microusd, denominator)

    usd_variable = (
        provider_generation_microusd
        + retry_microusd
        + repair_microusd
        + voice_audio_microusd
    )
    fx_reserve = _ceil_bps(usd_variable, config.usd_try_fx_buffer_bps)
    pre_tax_reserve = (
        provider_generation_microusd
        + retry_microusd
        + repair_microusd
        + voice_audio_microusd
        + other_variable_microusd
        + fixed_share
        + storage_share
        + infrastructure_share
        + fx_reserve
    )
    income_tax_bps = config.income_tax_reserve_bps
    if income_tax_bps is None:  # narrowed by require_paid_quote_ready; defensive fail closed
        raise CommercialAdmissionError("income tax reserve is unknown")
    income_tax_reserve = _ceil_bps(pre_tax_reserve, income_tax_bps)

    costs = VideoCostEnvelope(
        provider_generation_microusd=provider_generation_microusd,
        retry_microusd=retry_microusd,
        repair_microusd=repair_microusd,
        voice_audio_microusd=voice_audio_microusd,
        storage_microusd=storage_share,
        infrastructure_microusd=fixed_share + infrastructure_share,
        fx_reserve_microusd=fx_reserve,
        risk_reserve_microusd=income_tax_reserve,
        other_variable_microusd=other_variable_microusd,
    )
    policy = config.pricing_policy(quote_ttl_seconds=quote_ttl_seconds)
    quote = CommercialQuoteEngine(policy).create_locked_quote(
        quote_id=quote_id,
        now_epoch_s=now_epoch_s,
        tax_profile=tax_profile,
        pricing=pricing,
        costs=costs,
        duration_seconds=duration_seconds,
        aggregate_generated_seconds=aggregate_generated_seconds,
        resolution=resolution,
        shot_count=shot_count,
    )
    allocation = CommercialCostAllocation(
        active_users=active_users,
        chargeable_operations_per_active_user_month=chargeable_operations_per_active_user_month,
        fixed_cost_share_microusd=fixed_share,
        storage_backup_share_microusd=storage_share,
        infrastructure_share_microusd=infrastructure_share,
        fx_reserve_microusd=fx_reserve,
        income_tax_reserve_microusd=income_tax_reserve,
        fx_source=fx.source,
        fx_observed_at_epoch_s=fx.observed_at_epoch_s,
        fx_expires_at_epoch_s=fx.expires_at_epoch_s,
        config_version=config.version,
    )
    return quote, allocation


def _decimal(name: str, value: Decimal, *, allow_zero: bool) -> Decimal:
    try:
        amount = Decimal(value)
    except (InvalidOperation, TypeError) as exc:
        raise CommercialAdmissionError(f"{name} must be numeric") from exc
    minimum_ok = amount >= 0 if allow_zero else amount > 0
    if not amount.is_finite() or not minimum_ok:
        raise CommercialAdmissionError(f"{name} must be finite and non-negative")
    return amount


def _try_monthly_share_to_microusd(
    monthly_try: Decimal,
    *,
    denominator: int,
    usd_try: Decimal,
) -> int:
    positive_int("denominator", denominator)
    usd = (monthly_try / usd_try) / Decimal(denominator)
    return int((usd * Decimal(1_000_000)).to_integral_value(rounding=ROUND_CEILING))


def _ceil_div(value: int, denominator: int) -> int:
    nonnegative_int("value", value)
    positive_int("denominator", denominator)
    return (value + denominator - 1) // denominator


def _ceil_bps(value: int, bps: int) -> int:
    nonnegative_int("value", value)
    rate_bps("bps", bps)
    return (value * bps + BPS - 1) // BPS
