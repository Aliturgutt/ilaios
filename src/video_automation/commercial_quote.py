"""Locked quote, secured-payment and reconciliation evidence models."""

from __future__ import annotations

from dataclasses import dataclass

from .commercial_types import (
    CommercialAdmissionError,
    nonnegative_int,
    positive_int,
    rate_bps,
    require_text,
)


@dataclass(frozen=True, slots=True)
class LockedVideoQuote:
    quote_id: str
    quote_sha256: str
    provider_name: str
    model_id: str
    pricing_fingerprint: str
    cost_envelope_sha256: str
    currency: str
    tax_profile_id: str
    tax_rate_bps: int
    duration_seconds: int
    aggregate_generated_seconds: int
    resolution: str
    shot_count: int
    max_provider_attempts: int
    max_repair_generations: int
    provider_cost_ceiling_microusd: int
    retry_cost_ceiling_microusd: int
    repair_cost_ceiling_microusd: int
    protected_cost_microusd: int
    net_price_ex_tax_microusd: int
    tax_microusd: int
    gross_customer_price_microusd: int
    expected_payment_fee_microusd: int
    payment_fee_rate_bps: int
    payment_fixed_fee_microusd: int
    contingency_bps: int
    target_margin_bps: int
    hard_min_margin_bps: int
    created_at_epoch_s: int
    expires_at_epoch_s: int

    def __post_init__(self) -> None:
        for name in (
            "quote_id", "quote_sha256", "provider_name", "model_id",
            "pricing_fingerprint", "cost_envelope_sha256", "currency",
            "tax_profile_id", "resolution",
        ):
            require_text(name, getattr(self, name))
        for name in (
            "duration_seconds", "aggregate_generated_seconds", "shot_count",
            "max_provider_attempts", "provider_cost_ceiling_microusd",
            "protected_cost_microusd", "net_price_ex_tax_microusd",
            "gross_customer_price_microusd", "expires_at_epoch_s",
        ):
            positive_int(name, getattr(self, name))
        for name in (
            "max_repair_generations", "retry_cost_ceiling_microusd",
            "repair_cost_ceiling_microusd", "tax_microusd",
            "expected_payment_fee_microusd", "payment_fixed_fee_microusd",
            "created_at_epoch_s",
        ):
            nonnegative_int(name, getattr(self, name))
        rate_bps("tax_rate_bps", self.tax_rate_bps, allow_full=True)
        for name in (
            "payment_fee_rate_bps", "contingency_bps",
            "target_margin_bps", "hard_min_margin_bps",
        ):
            rate_bps(name, getattr(self, name))
        if self.expires_at_epoch_s <= self.created_at_epoch_s:
            raise CommercialAdmissionError("quote lifetime is invalid")
        if self.target_margin_bps < self.hard_min_margin_bps:
            raise CommercialAdmissionError("quote margin policy is invalid")

    def require_valid(self, now_epoch_s: int) -> None:
        nonnegative_int("now_epoch_s", now_epoch_s)
        if now_epoch_s >= self.expires_at_epoch_s:
            raise CommercialAdmissionError("locked quote expired; requote required")


@dataclass(frozen=True, slots=True)
class PaymentAuthorization:
    payment_authorization_id: str
    quote_id: str
    secured_amount_microusd: int
    secured_at_epoch_s: int
    status: str = "SECURED"

    def __post_init__(self) -> None:
        require_text("payment_authorization_id", self.payment_authorization_id)
        require_text("quote_id", self.quote_id)
        positive_int("secured_amount_microusd", self.secured_amount_microusd)
        nonnegative_int("secured_at_epoch_s", self.secured_at_epoch_s)
        require_text("status", self.status)

    def require_secured_for(self, quote: LockedVideoQuote) -> None:
        if self.status != "SECURED":
            raise CommercialAdmissionError(
                "payment is not secured; paid generation is forbidden"
            )
        if self.quote_id != quote.quote_id:
            raise CommercialAdmissionError("payment is bound to a different quote")
        if self.secured_amount_microusd < quote.gross_customer_price_microusd:
            raise CommercialAdmissionError(
                "secured payment does not cover locked customer price"
            )


@dataclass(frozen=True, slots=True)
class CommercialDispatchAuthority:
    authority_sha256: str
    quote_id: str
    quote_sha256: str
    payment_authorization_id: str
    provider_name: str
    model_id: str
    pricing_fingerprint: str
    provider_cost_ceiling_microusd: int
    issued_at_epoch_s: int
    expires_at_epoch_s: int

    def __post_init__(self) -> None:
        for name in (
            "authority_sha256", "quote_id", "quote_sha256",
            "payment_authorization_id", "provider_name", "model_id",
            "pricing_fingerprint",
        ):
            require_text(name, getattr(self, name))
        positive_int(
            "provider_cost_ceiling_microusd", self.provider_cost_ceiling_microusd
        )
        nonnegative_int("issued_at_epoch_s", self.issued_at_epoch_s)
        positive_int("expires_at_epoch_s", self.expires_at_epoch_s)
        if self.expires_at_epoch_s <= self.issued_at_epoch_s:
            raise CommercialAdmissionError("dispatch authority lifetime is invalid")

    def require_valid(self, now_epoch_s: int) -> None:
        nonnegative_int("now_epoch_s", now_epoch_s)
        if now_epoch_s >= self.expires_at_epoch_s:
            raise CommercialAdmissionError(
                "commercial dispatch authority expired; requote required"
            )


@dataclass(frozen=True, slots=True)
class CommercialReconciliation:
    quote_id: str
    actual_provider_cost_microusd: int
    actual_other_variable_cost_microusd: int
    actual_total_cost_microusd: int
    gross_profit_microusd: int
    actual_margin_bps: int
    provider_quarantined: bool
    quarantine_reason: str | None
