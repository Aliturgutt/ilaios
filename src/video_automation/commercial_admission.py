"""Public fail-closed commercial admission API for paid Video Factory jobs."""

from .commercial_cost_config import (
    CommercialCostAllocation,
    CommercialCostConfig,
    FxRateSnapshot,
    create_governed_locked_quote,
)
from .commercial_dispatch import authorize_paid_dispatch, reconcile_commercial_cost
from .commercial_free_admission import FreeOperationAdmission, authorize_free_operation
from .commercial_quote import (
    CommercialDispatchAuthority,
    CommercialReconciliation,
    LockedVideoQuote,
    PaymentAuthorization,
)
from .commercial_quote_engine import CommercialQuoteEngine
from .commercial_types import (
    CommercialAdmissionError,
    CommercialPricingPolicy,
    ProviderPricingSnapshot,
    TaxProfile,
    VideoCostEnvelope,
)


class CommercialAdmissionEngine(CommercialQuoteEngine):
    """Own locked quote construction plus paid dispatch and reconciliation gates."""

    def authorize_paid_dispatch(self, **kwargs: object) -> CommercialDispatchAuthority:
        return authorize_paid_dispatch(**kwargs)  # type: ignore[arg-type]

    def reconcile(self, **kwargs: object) -> CommercialReconciliation:
        return reconcile_commercial_cost(**kwargs)  # type: ignore[arg-type]


__all__ = [
    "CommercialAdmissionEngine",
    "CommercialAdmissionError",
    "CommercialCostAllocation",
    "CommercialCostConfig",
    "CommercialDispatchAuthority",
    "CommercialPricingPolicy",
    "CommercialReconciliation",
    "FreeOperationAdmission",
    "FxRateSnapshot",
    "LockedVideoQuote",
    "PaymentAuthorization",
    "ProviderPricingSnapshot",
    "TaxProfile",
    "VideoCostEnvelope",
    "authorize_free_operation",
    "authorize_paid_dispatch",
    "create_governed_locked_quote",
    "reconcile_commercial_cost",
]
