"""Versioned cost configuration for the existing commercial quote authority.

These values are operating inputs, not claims about live invoices or production
pricing. Unknown costs remain ``None`` and paid quoting fails closed.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_CEILING

from .commercial_quote import LockedVideoQuote
from .commercial_quote_engine import CommercialQuoteEngine
from .commercial_store import CommercialAuthorityStore
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

_COST_EVIDENCE_SCHEMA = """
CREATE TABLE IF NOT EXISTS commercial_quote_cost_evidence (
 quote_id TEXT PRIMARY KEY,
 quote_sha256 TEXT UNIQUE NOT NULL,
 cost_envelope_sha256 TEXT NOT NULL,
 config_version TEXT NOT NULL,
 active_users INTEGER NOT NULL CHECK(active_users > 0),
 chargeable_operations_per_active_user_month INTEGER NOT NULL CHECK(chargeable_operations_per_active_user_month > 0),
 fixed_cost_share_microusd INTEGER NOT NULL CHECK(fixed_cost_share_microusd >= 0),
 storage_backup_share_microusd INTEGER NOT NULL CHECK(storage_backup_share_microusd >= 0),
 infrastructure_share_microusd INTEGER NOT NULL CHECK(infrastructure_share_microusd >= 0),
 fx_reserve_microusd INTEGER NOT NULL CHECK(fx_reserve_microusd >= 0),
 income_tax_reserve_microusd INTEGER NOT NULL CHECK(income_tax_reserve_microusd >= 0),
 fx_source TEXT NOT NULL,
 fx_observed_at_epoch_s INTEGER NOT NULL CHECK(fx_observed_at_epoch_s >= 0),
 fx_expires_at_epoch_s INTEGER NOT NULL CHECK(fx_expires_at_epoch_s > 0),
 FOREIGN KEY(quote_id) REFERENCES commercial_quotes(quote_id)
);
"""


@dataclass(frozen=True, slots=True)
class FxRateSnapshot:
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
    target_minimum_net_operating_profit_margin_bps: int = 4_000
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
            object.__setattr__(self, name, _decimal(name, getattr(self, name)))
        for name in ("render_monthly_usd", "vercel_monthly_usd", "cloudflare_monthly_usd"):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, _decimal(name, value))
        rate_bps("payment_fee_reserve_bps", self.payment_fee_reserve_bps)
        rate_bps("usd_try_fx_buffer_bps", self.usd_try_fx_buffer_bps)
        rate_bps("target_minimum_net_operating_profit_margin_bps", self.target_minimum_net_operating_profit_margin_bps)
        positive_int("free_operations_per_active_user_per_month", self.free_operations_per_active_user_per_month)
        if self.income_tax_reserve_bps is not None:
            rate_bps("income_tax_reserve_bps", self.income_tax_reserve_bps)
        components = self.domain_email_monthly_try + self.accounting_monthly_try + self.labor_monthly_try + self.internet_and_other_subscriptions_monthly_try
        if components != self.fixed_base_monthly_try:
            raise CommercialAdmissionError("fixed_base_monthly_try must equal configured fixed-cost components")

    def require_paid_quote_ready(self) -> None:
        missing = [name for name in ("render_monthly_usd", "vercel_monthly_usd", "cloudflare_monthly_usd", "income_tax_reserve_bps") if getattr(self, name) is None]
        if missing:
            raise CommercialAdmissionError("paid quote cost config incomplete: " + ", ".join(missing))

    def pricing_policy(self, *, quote_ttl_seconds: int = 300) -> CommercialPricingPolicy:
        self.require_paid_quote_ready()
        margin = self.target_minimum_net_operating_profit_margin_bps
        return CommercialPricingPolicy(target_margin_bps=margin, hard_min_margin_bps=margin, contingency_bps=0, payment_fee_rate_bps=self.payment_fee_reserve_bps, payment_fixed_fee_microusd=0, quote_ttl_seconds=quote_ttl_seconds)


@dataclass(frozen=True, slots=True)
class CommercialCostAllocation:
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
    store: CommercialAuthorityStore,
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
    config.require_paid_quote_ready()
    fx.require_fresh(now_epoch_s)
    pricing.require_fresh(now_epoch_s)
    positive_int("active_users", active_users)
    positive_int("chargeable_operations_per_active_user_month", chargeable_operations_per_active_user_month)
    positive_int("provider_generation_microusd", provider_generation_microusd)
    for name, value in (("retry_microusd", retry_microusd), ("repair_microusd", repair_microusd), ("voice_audio_microusd", voice_audio_microusd), ("other_variable_microusd", other_variable_microusd)):
        nonnegative_int(name, value)

    denominator = active_users * chargeable_operations_per_active_user_month
    fixed_share = _try_share_to_microusd(config.fixed_base_monthly_try, denominator, fx.usd_try)
    storage_share = _try_share_to_microusd(config.storage_backup_per_active_user_monthly_try * active_users, denominator, fx.usd_try)
    monthly_infrastructure = sum(usd_to_microusd(value) for value in (config.render_monthly_usd, config.vercel_monthly_usd, config.cloudflare_monthly_usd) if value is not None)
    infrastructure_share = _ceil_div(monthly_infrastructure, denominator)
    usd_variable = provider_generation_microusd + retry_microusd + repair_microusd + voice_audio_microusd
    fx_reserve = _ceil_bps(usd_variable, config.usd_try_fx_buffer_bps)
    pre_tax_reserve = usd_variable + other_variable_microusd + fixed_share + storage_share + infrastructure_share + fx_reserve
    income_tax_bps = config.income_tax_reserve_bps
    if income_tax_bps is None:
        raise CommercialAdmissionError("income tax reserve is unknown")
    income_tax_reserve = _ceil_bps(pre_tax_reserve, income_tax_bps)
    costs = VideoCostEnvelope(provider_generation_microusd=provider_generation_microusd, retry_microusd=retry_microusd, repair_microusd=repair_microusd, voice_audio_microusd=voice_audio_microusd, storage_microusd=storage_share, infrastructure_microusd=fixed_share + infrastructure_share, fx_reserve_microusd=fx_reserve, risk_reserve_microusd=income_tax_reserve, other_variable_microusd=other_variable_microusd)
    quote = CommercialQuoteEngine(config.pricing_policy(quote_ttl_seconds=quote_ttl_seconds)).create_locked_quote(quote_id=quote_id, now_epoch_s=now_epoch_s, tax_profile=tax_profile, pricing=pricing, costs=costs, duration_seconds=duration_seconds, aggregate_generated_seconds=aggregate_generated_seconds, resolution=resolution, shot_count=shot_count)
    allocation = CommercialCostAllocation(active_users=active_users, chargeable_operations_per_active_user_month=chargeable_operations_per_active_user_month, fixed_cost_share_microusd=fixed_share, storage_backup_share_microusd=storage_share, infrastructure_share_microusd=infrastructure_share, fx_reserve_microusd=fx_reserve, income_tax_reserve_microusd=income_tax_reserve, fx_source=fx.source, fx_observed_at_epoch_s=fx.observed_at_epoch_s, fx_expires_at_epoch_s=fx.expires_at_epoch_s, config_version=config.version)
    store.record_quote(quote)
    _record_cost_evidence(store, quote, allocation)
    return quote, allocation


def _record_cost_evidence(store: CommercialAuthorityStore, quote: LockedVideoQuote, allocation: CommercialCostAllocation) -> None:
    values = (quote.quote_id, quote.quote_sha256, quote.cost_envelope_sha256, allocation.config_version, allocation.active_users, allocation.chargeable_operations_per_active_user_month, allocation.fixed_cost_share_microusd, allocation.storage_backup_share_microusd, allocation.infrastructure_share_microusd, allocation.fx_reserve_microusd, allocation.income_tax_reserve_microusd, allocation.fx_source, allocation.fx_observed_at_epoch_s, allocation.fx_expires_at_epoch_s)
    with store._connect() as connection:
        connection.executescript(_COST_EVIDENCE_SCHEMA)
        connection.execute("BEGIN IMMEDIATE")
        existing = connection.execute("SELECT * FROM commercial_quote_cost_evidence WHERE quote_id=?", (quote.quote_id,)).fetchone()
        if existing is not None:
            if tuple(existing) != values:
                raise CommercialAdmissionError("quote cost evidence is already persisted differently")
            return
        connection.execute("INSERT INTO commercial_quote_cost_evidence VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", values)


def _decimal(name: str, value: Decimal) -> Decimal:
    try:
        amount = Decimal(value)
    except (InvalidOperation, TypeError) as exc:
        raise CommercialAdmissionError(f"{name} must be numeric") from exc
    if not amount.is_finite() or amount < 0:
        raise CommercialAdmissionError(f"{name} must be finite and non-negative")
    return amount


def _try_share_to_microusd(monthly_try: Decimal, denominator: int, usd_try: Decimal) -> int:
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
