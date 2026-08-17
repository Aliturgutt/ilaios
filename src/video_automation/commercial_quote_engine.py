"""Locked customer quote construction with VAT, margin and reserve protection."""

from __future__ import annotations

from decimal import Decimal, ROUND_CEILING

from .commercial_quote import LockedVideoQuote
from .commercial_types import (
    BPS,
    CommercialAdmissionError,
    CommercialPricingPolicy,
    ProviderPricingSnapshot,
    TaxProfile,
    VideoCostEnvelope,
    digest_material,
    nonnegative_int,
    positive_int,
    rate_bps,
    require_text,
)


class CommercialQuoteEngine:
    def __init__(self, policy: CommercialPricingPolicy) -> None:
        self.policy = policy

    def create_locked_quote(
        self,
        *,
        quote_id: str,
        now_epoch_s: int,
        tax_profile: TaxProfile,
        pricing: ProviderPricingSnapshot,
        costs: VideoCostEnvelope,
        duration_seconds: int,
        aggregate_generated_seconds: int,
        resolution: str,
        shot_count: int,
        currency: str = "USD",
    ) -> LockedVideoQuote:
        require_text("quote_id", quote_id)
        nonnegative_int("now_epoch_s", now_epoch_s)
        require_text("resolution", resolution)
        require_text("currency", currency)
        positive_int("duration_seconds", duration_seconds)
        positive_int("aggregate_generated_seconds", aggregate_generated_seconds)
        positive_int("shot_count", shot_count)
        pricing.require_fresh(now_epoch_s)
        if pricing.max_job_cost_microusd > costs.external_provider_ceiling_microusd:
            raise CommercialAdmissionError(
                "cost envelope does not cover live provider maximum cost"
            )

        protected = costs.protected_cost_microusd(self.policy.contingency_bps)
        net, tax, gross, fee = self._minimum_safe_price(
            protected, tax_profile.tax_rate_bps
        )
        expires = min(
            now_epoch_s + self.policy.quote_ttl_seconds,
            pricing.expires_at_epoch_s,
        )
        if expires <= now_epoch_s:
            raise CommercialAdmissionError("quote cannot use stale pricing")
        data = {
            "quote_id": quote_id,
            "provider_name": pricing.provider_name,
            "model_id": pricing.model_id,
            "pricing_fingerprint": pricing.pricing_fingerprint,
            "cost_envelope_sha256": costs.fingerprint,
            "currency": currency,
            "tax_profile_id": tax_profile.profile_id,
            "tax_rate_bps": tax_profile.tax_rate_bps,
            "duration_seconds": duration_seconds,
            "aggregate_generated_seconds": aggregate_generated_seconds,
            "resolution": resolution,
            "shot_count": shot_count,
            "max_provider_attempts": self.policy.max_provider_attempts,
            "max_repair_generations": self.policy.max_repair_generations,
            "provider_cost_ceiling_microusd": costs.external_provider_ceiling_microusd,
            "retry_cost_ceiling_microusd": costs.retry_microusd,
            "repair_cost_ceiling_microusd": costs.repair_microusd,
            "protected_cost_microusd": protected,
            "net_price_ex_tax_microusd": net,
            "tax_microusd": tax,
            "gross_customer_price_microusd": gross,
            "expected_payment_fee_microusd": fee,
            "payment_fee_rate_bps": self.policy.payment_fee_rate_bps,
            "payment_fixed_fee_microusd": self.policy.payment_fixed_fee_microusd,
            "contingency_bps": self.policy.contingency_bps,
            "target_margin_bps": self.policy.target_margin_bps,
            "hard_min_margin_bps": self.policy.hard_min_margin_bps,
            "created_at_epoch_s": now_epoch_s,
            "expires_at_epoch_s": expires,
        }
        quote_hash = digest_material(*(f"{k}={v}" for k, v in data.items()))
        return LockedVideoQuote(
            quote_id=quote_id,
            quote_sha256=quote_hash,
            provider_name=pricing.provider_name,
            model_id=pricing.model_id,
            pricing_fingerprint=pricing.pricing_fingerprint,
            cost_envelope_sha256=costs.fingerprint,
            currency=currency,
            tax_profile_id=tax_profile.profile_id,
            tax_rate_bps=tax_profile.tax_rate_bps,
            duration_seconds=duration_seconds,
            aggregate_generated_seconds=aggregate_generated_seconds,
            resolution=resolution,
            shot_count=shot_count,
            max_provider_attempts=self.policy.max_provider_attempts,
            max_repair_generations=self.policy.max_repair_generations,
            provider_cost_ceiling_microusd=costs.external_provider_ceiling_microusd,
            retry_cost_ceiling_microusd=costs.retry_microusd,
            repair_cost_ceiling_microusd=costs.repair_microusd,
            protected_cost_microusd=protected,
            net_price_ex_tax_microusd=net,
            tax_microusd=tax,
            gross_customer_price_microusd=gross,
            expected_payment_fee_microusd=fee,
            payment_fee_rate_bps=self.policy.payment_fee_rate_bps,
            payment_fixed_fee_microusd=self.policy.payment_fixed_fee_microusd,
            contingency_bps=self.policy.contingency_bps,
            target_margin_bps=self.policy.target_margin_bps,
            hard_min_margin_bps=self.policy.hard_min_margin_bps,
            created_at_epoch_s=now_epoch_s,
            expires_at_epoch_s=expires,
        )

    def _minimum_safe_price(
        self, protected_cost_microusd: int, tax_rate_bps: int
    ) -> tuple[int, int, int, int]:
        positive_int("protected_cost_microusd", protected_cost_microusd)
        rate_bps("tax_rate_bps", tax_rate_bps, allow_full=True)
        margin = Decimal(self.policy.target_margin_bps) / Decimal(BPS)
        vat = Decimal(BPS + tax_rate_bps) / Decimal(BPS)
        payment_rate = Decimal(self.policy.payment_fee_rate_bps) / Decimal(BPS)
        denominator = ((Decimal(1) - margin) / vat) - payment_rate
        if denominator <= 0:
            raise CommercialAdmissionError("pricing policy cannot avoid loss")
        gross = int(
            (
                (
                    Decimal(protected_cost_microusd)
                    + Decimal(self.policy.payment_fixed_fee_microusd)
                )
                / denominator
            ).to_integral_value(rounding=ROUND_CEILING)
        )
        while True:
            net = gross * BPS // (BPS + tax_rate_bps)
            tax = gross - net
            fee = (
                (gross * self.policy.payment_fee_rate_bps + BPS - 1) // BPS
                + self.policy.payment_fixed_fee_microusd
            )
            required_profit = (
                net * self.policy.target_margin_bps + BPS - 1
            ) // BPS
            if net - protected_cost_microusd - fee >= required_profit:
                break
            gross += 1
        actual_margin = (net - protected_cost_microusd - fee) * BPS // net
        if actual_margin < self.policy.hard_min_margin_bps:
            raise CommercialAdmissionError("computed price violates hard margin floor")
        return net, tax, gross, fee
