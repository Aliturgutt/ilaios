"""Commercial price protection for provider-backed Video Factory execution.

The pricing guard converts an already capability-matched provider routing plan
into the minimum user-facing net price that is allowed to be charged.  It is
intentionally conservative: unknown costs fail closed, configured retry and FX
buffers are reserved before execution, payment processing is treated as a cost,
and the requested gross-margin floor is solved algebraically rather than added
as a naive markup.

Taxes are deliberately outside this module.  The returned customer price is the
net amount before VAT/sales tax; applicable tax must be calculated and charged
on top by the jurisdiction-aware billing layer.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_CEILING

from .adaptive_production import ShotRoutingPlan

_BPS = Decimal("10000")
_CENT = Decimal("0.01")


class CommercialPricingError(ValueError):
    """Raised when a non-loss-making commercial quote cannot be proven."""


@dataclass(frozen=True, slots=True)
class CommercialPricingPolicy:
    """Explicit commercial assumptions required before paid generation.

    All values are deliberately configurable.  Production code must load them
    from governed business configuration rather than silently invent margins or
    fee assumptions.
    """

    provider_attempt_reserve: int
    provider_price_buffer_bps: int
    fx_buffer_bps: int
    infrastructure_fixed_usd: Decimal
    infrastructure_per_generated_second_usd: Decimal
    payment_fee_bps: int
    payment_fixed_fee_usd: Decimal
    minimum_gross_margin_bps: int
    minimum_net_charge_usd: Decimal = Decimal("0")

    def __post_init__(self) -> None:
        if self.provider_attempt_reserve < 1:
            raise CommercialPricingError("provider_attempt_reserve must be >= 1")
        for name in (
            "provider_price_buffer_bps",
            "fx_buffer_bps",
            "payment_fee_bps",
            "minimum_gross_margin_bps",
        ):
            value = getattr(self, name)
            if not 0 <= value < 10000:
                raise CommercialPricingError(f"{name} must be between 0 and 9999")
        if self.payment_fee_bps + self.minimum_gross_margin_bps >= 10000:
            raise CommercialPricingError(
                "payment fee and gross margin combination leaves no chargeable revenue"
            )
        for name in (
            "infrastructure_fixed_usd",
            "infrastructure_per_generated_second_usd",
            "payment_fixed_fee_usd",
            "minimum_net_charge_usd",
        ):
            if getattr(self, name) < Decimal("0"):
                raise CommercialPricingError(f"{name} must not be negative")


@dataclass(frozen=True, slots=True)
class CommercialVideoQuote:
    """Minimum safe net quote for one finished-product generation request."""

    generated_seconds: int
    estimated_provider_cost_usd: Decimal
    provider_reserve_usd: Decimal
    buffered_provider_reserve_usd: Decimal
    estimated_infrastructure_cost_usd: Decimal
    protected_cost_basis_usd: Decimal
    minimum_retained_revenue_usd: Decimal
    minimum_customer_net_price_usd: Decimal
    minimum_customer_net_price_cents: int
    target_gross_margin_bps: int

    @property
    def is_zero_provider_cost(self) -> bool:
        return self.estimated_provider_cost_usd == Decimal("0")


class CommercialPricingGuard:
    """Prove a customer net price that cannot undercut configured cost floors."""

    def quote(
        self,
        routing: ShotRoutingPlan,
        policy: CommercialPricingPolicy,
    ) -> CommercialVideoQuote:
        if routing.generated_seconds <= 0:
            raise CommercialPricingError("routing must contain generated seconds")
        if routing.estimated_provider_cost_usd < Decimal("0"):
            raise CommercialPricingError("provider cost must not be negative")

        provider_reserve = (
            routing.estimated_provider_cost_usd
            * Decimal(policy.provider_attempt_reserve)
        )
        buffer_bps = policy.provider_price_buffer_bps + policy.fx_buffer_bps
        buffered_provider = provider_reserve * (
            Decimal("1") + Decimal(buffer_bps) / _BPS
        )
        infrastructure = (
            policy.infrastructure_fixed_usd
            + policy.infrastructure_per_generated_second_usd
            * Decimal(routing.generated_seconds)
        )
        protected_cost = buffered_provider + infrastructure

        margin_rate = Decimal(policy.minimum_gross_margin_bps) / _BPS
        retained_required = protected_cost / (Decimal("1") - margin_rate)

        payment_rate = Decimal(policy.payment_fee_bps) / _BPS
        customer_price = (
            retained_required + policy.payment_fixed_fee_usd
        ) / (Decimal("1") - payment_rate)
        customer_price = max(customer_price, policy.minimum_net_charge_usd)
        customer_price = _round_up_cents(customer_price)

        return CommercialVideoQuote(
            generated_seconds=routing.generated_seconds,
            estimated_provider_cost_usd=routing.estimated_provider_cost_usd,
            provider_reserve_usd=provider_reserve,
            buffered_provider_reserve_usd=buffered_provider,
            estimated_infrastructure_cost_usd=infrastructure,
            protected_cost_basis_usd=protected_cost,
            minimum_retained_revenue_usd=retained_required,
            minimum_customer_net_price_usd=customer_price,
            minimum_customer_net_price_cents=int(customer_price * 100),
            target_gross_margin_bps=policy.minimum_gross_margin_bps,
        )

    def assert_charge_is_safe(
        self,
        quote: CommercialVideoQuote,
        *,
        customer_net_price_usd: Decimal,
    ) -> None:
        """Fail closed before execution when checkout charges below the safe quote."""

        if customer_net_price_usd < quote.minimum_customer_net_price_usd:
            raise CommercialPricingError(
                "customer price is below the protected non-loss-making quote"
            )


def _round_up_cents(value: Decimal) -> Decimal:
    if value < Decimal("0"):
        raise CommercialPricingError("price must not be negative")
    return value.quantize(_CENT, rounding=ROUND_CEILING)
