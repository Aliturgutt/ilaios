"""Payment-before-dispatch, live-price revalidation and reconciliation."""

from __future__ import annotations

from .commercial_quote import (
    CommercialDispatchAuthority,
    CommercialReconciliation,
    LockedVideoQuote,
    PaymentAuthorization,
)
from .commercial_types import (
    BPS,
    CommercialAdmissionError,
    ProviderPricingSnapshot,
    digest_material,
    nonnegative_int,
)
from .managed_credits import ProviderCostQuote


def authorize_paid_dispatch(
    *,
    now_epoch_s: int,
    quote: LockedVideoQuote,
    payment: PaymentAuthorization,
    current_pricing: ProviderPricingSnapshot,
    provider_quote: ProviderCostQuote,
) -> CommercialDispatchAuthority:
    quote.require_valid(now_epoch_s)
    payment.require_secured_for(quote)
    current_pricing.require_fresh(now_epoch_s)
    if current_pricing.provider_name != quote.provider_name:
        raise CommercialAdmissionError("provider changed; requote required")
    if current_pricing.model_id != quote.model_id:
        raise CommercialAdmissionError("model changed; requote required")
    if current_pricing.pricing_fingerprint != quote.pricing_fingerprint:
        raise CommercialAdmissionError("pricing changed; requote required")
    if current_pricing.max_job_cost_microusd > quote.provider_cost_ceiling_microusd:
        raise CommercialAdmissionError(
            "live provider cost exceeds locked ceiling; requote required"
        )
    if provider_quote.provider_name != quote.provider_name:
        raise CommercialAdmissionError("provider quote does not match provider")
    if provider_quote.model_id != quote.model_id:
        raise CommercialAdmissionError("provider quote does not match model")
    if provider_quote.max_cost_microusd > quote.provider_cost_ceiling_microusd:
        raise CommercialAdmissionError(
            "provider request exceeds locked job cost ceiling"
        )

    expires = min(quote.expires_at_epoch_s, current_pricing.expires_at_epoch_s)
    data = {
        "quote_id": quote.quote_id,
        "quote_sha256": quote.quote_sha256,
        "payment_authorization_id": payment.payment_authorization_id,
        "provider_name": quote.provider_name,
        "model_id": quote.model_id,
        "pricing_fingerprint": quote.pricing_fingerprint,
        "provider_cost_ceiling_microusd": provider_quote.max_cost_microusd,
        "issued_at_epoch_s": now_epoch_s,
        "expires_at_epoch_s": expires,
    }
    authority_hash = digest_material(*(f"{k}={v}" for k, v in data.items()))
    return CommercialDispatchAuthority(
        authority_sha256=authority_hash,
        quote_id=quote.quote_id,
        quote_sha256=quote.quote_sha256,
        payment_authorization_id=payment.payment_authorization_id,
        provider_name=quote.provider_name,
        model_id=quote.model_id,
        pricing_fingerprint=quote.pricing_fingerprint,
        provider_cost_ceiling_microusd=provider_quote.max_cost_microusd,
        issued_at_epoch_s=now_epoch_s,
        expires_at_epoch_s=expires,
    )


def reconcile_commercial_cost(
    *,
    quote: LockedVideoQuote,
    actual_provider_cost_microusd: int,
    actual_other_variable_cost_microusd: int,
) -> CommercialReconciliation:
    nonnegative_int("actual_provider_cost_microusd", actual_provider_cost_microusd)
    nonnegative_int(
        "actual_other_variable_cost_microusd", actual_other_variable_cost_microusd
    )
    actual_total = (
        actual_provider_cost_microusd
        + actual_other_variable_cost_microusd
        + quote.expected_payment_fee_microusd
    )
    gross_profit = quote.net_price_ex_tax_microusd - actual_total
    actual_margin = gross_profit * BPS // quote.net_price_ex_tax_microusd
    reasons: list[str] = []
    if actual_provider_cost_microusd > quote.provider_cost_ceiling_microusd:
        reasons.append("actual provider cost exceeded locked provider ceiling")
    if actual_margin < quote.hard_min_margin_bps:
        reasons.append("actual gross margin fell below hard minimum")
    return CommercialReconciliation(
        quote_id=quote.quote_id,
        actual_provider_cost_microusd=actual_provider_cost_microusd,
        actual_other_variable_cost_microusd=actual_other_variable_cost_microusd,
        actual_total_cost_microusd=actual_total,
        gross_profit_microusd=gross_profit,
        actual_margin_bps=actual_margin,
        provider_quarantined=bool(reasons),
        quarantine_reason="; ".join(reasons) if reasons else None,
    )
