"""Public fail-closed commercial admission API for paid Video Factory jobs."""

from .commercial_dispatch import authorize_paid_dispatch, reconcile_commercial_cost
from .commercial_quote import CommercialDispatchAuthority, CommercialReconciliation, LockedVideoQuote, PaymentAuthorization
from .commercial_quote_engine import CommercialQuoteEngine
from .commercial_types import CommercialAdmissionError, CommercialPricingPolicy, ProviderPricingSnapshot, TaxProfile, VideoCostEnvelope


class CommercialAdmissionEngine(CommercialQuoteEngine):
    """Own locked quote construction plus paid dispatch and reconciliation gates."""

    def authorize_paid_dispatch(self, **kwargs: object) -> CommercialDispatchAuthority:
        return authorize_paid_dispatch(**kwargs)  # type: ignore[arg-type]

    def reconcile(self, **kwargs: object) -> CommercialReconciliation:
        return reconcile_commercial_cost(**kwargs)  # type: ignore[arg-type]


__all__ = [
    "CommercialAdmissionEngine", "CommercialAdmissionError",
    "CommercialDispatchAuthority", "CommercialPricingPolicy",
    "CommercialReconciliation", "LockedVideoQuote", "PaymentAuthorization",
    "ProviderPricingSnapshot", "TaxProfile", "VideoCostEnvelope",
    "authorize_paid_dispatch", "reconcile_commercial_cost",
]
