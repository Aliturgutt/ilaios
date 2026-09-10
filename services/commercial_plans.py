"""Canonical commercial plan configuration for ILAIOS.

This module defines plan identity and inheritance only. Entitlement state remains
owned by services.commercial_access; provider spend reservation/settlement remains
owned by the managed-credit ledger. Payment adapters cannot mint entitlement.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class CommercialPlanError(ValueError):
    """Raised when commercial plan configuration is invalid."""


class CommercialPlanId(str, Enum):
    FREE = "FREE"
    PRO = "PRO"
    BUSINESS = "BUSINESS"
    POWER = "POWER"
    ENTERPRISE = "ENTERPRISE"


@dataclass(frozen=True, slots=True)
class CommercialPlan:
    plan_id: CommercialPlanId
    parent: CommercialPlanId | None
    monthly_price_usd: int | None
    workspace_users: int | None
    max_concurrent_jobs: int
    max_active_projects: int | None
    max_active_automations: int | None
    automation_runs_per_month: int | None
    storage_limit_gb: int | None
    history_evidence_retention_days: int | None
    paid_provider_allowed: bool
    monthly_provider_budget_usd: float | None

    def __post_init__(self) -> None:
        if self.max_concurrent_jobs < 1:
            raise CommercialPlanError("max_concurrent_jobs must be positive")
        for name in (
            "workspace_users",
            "max_active_projects",
            "max_active_automations",
            "automation_runs_per_month",
            "storage_limit_gb",
            "history_evidence_retention_days",
        ):
            value = getattr(self, name)
            if value is not None and value < 1:
                raise CommercialPlanError(f"{name} must be positive when configured")
        if self.monthly_price_usd is not None and self.monthly_price_usd < 0:
            raise CommercialPlanError("monthly_price_usd cannot be negative")
        if self.monthly_provider_budget_usd is not None and self.monthly_provider_budget_usd < 0:
            raise CommercialPlanError("monthly_provider_budget_usd cannot be negative")
        if self.plan_id is CommercialPlanId.FREE:
            if self.monthly_price_usd != 0 or self.paid_provider_allowed:
                raise CommercialPlanError("FREE must be zero-price and fail closed for paid providers")
            if self.monthly_provider_budget_usd not in (None, 0):
                raise CommercialPlanError("FREE cannot carry a paid provider budget")
        elif self.plan_id is not CommercialPlanId.ENTERPRISE:
            if self.monthly_price_usd is None or self.monthly_price_usd <= 0:
                raise CommercialPlanError("paid plans require a positive monthly price reference")
            if not self.paid_provider_allowed:
                raise CommercialPlanError("paid plans must permit governed paid-provider admission")

    @property
    def paid_dispatch_budget_verified(self) -> bool:
        return self.paid_provider_allowed and self.monthly_provider_budget_usd is not None


# Uploaded plan specifications lock these public price references. Provider budgets
# remain UNKNOWN until evidence-backed economics are configured; paid dispatch must
# therefore fail closed on paid_dispatch_budget_verified == False.
_PLANS: dict[CommercialPlanId, CommercialPlan] = {
    CommercialPlanId.FREE: CommercialPlan(
        plan_id=CommercialPlanId.FREE,
        parent=None,
        monthly_price_usd=0,
        workspace_users=1,
        max_concurrent_jobs=1,
        max_active_projects=3,
        max_active_automations=1,
        automation_runs_per_month=30,
        storage_limit_gb=2,
        history_evidence_retention_days=30,
        paid_provider_allowed=False,
        monthly_provider_budget_usd=0,
    ),
    CommercialPlanId.PRO: CommercialPlan(
        plan_id=CommercialPlanId.PRO,
        parent=CommercialPlanId.FREE,
        monthly_price_usd=49,
        workspace_users=None,
        max_concurrent_jobs=1,
        max_active_projects=None,
        max_active_automations=None,
        automation_runs_per_month=None,
        storage_limit_gb=None,
        history_evidence_retention_days=None,
        paid_provider_allowed=True,
        monthly_provider_budget_usd=None,
    ),
    CommercialPlanId.BUSINESS: CommercialPlan(
        plan_id=CommercialPlanId.BUSINESS,
        parent=CommercialPlanId.PRO,
        monthly_price_usd=99,
        workspace_users=None,
        max_concurrent_jobs=1,
        max_active_projects=None,
        max_active_automations=None,
        automation_runs_per_month=None,
        storage_limit_gb=None,
        history_evidence_retention_days=None,
        paid_provider_allowed=True,
        monthly_provider_budget_usd=None,
    ),
    CommercialPlanId.POWER: CommercialPlan(
        plan_id=CommercialPlanId.POWER,
        parent=CommercialPlanId.BUSINESS,
        monthly_price_usd=199,
        workspace_users=None,
        max_concurrent_jobs=1,
        max_active_projects=None,
        max_active_automations=None,
        automation_runs_per_month=None,
        storage_limit_gb=None,
        history_evidence_retention_days=None,
        paid_provider_allowed=True,
        monthly_provider_budget_usd=None,
    ),
    CommercialPlanId.ENTERPRISE: CommercialPlan(
        plan_id=CommercialPlanId.ENTERPRISE,
        parent=CommercialPlanId.POWER,
        monthly_price_usd=None,
        workspace_users=None,
        max_concurrent_jobs=1,
        max_active_projects=None,
        max_active_automations=None,
        automation_runs_per_month=None,
        storage_limit_gb=None,
        history_evidence_retention_days=None,
        paid_provider_allowed=True,
        monthly_provider_budget_usd=None,
    ),
}


def get_commercial_plan(plan_id: str | CommercialPlanId) -> CommercialPlan:
    try:
        canonical = plan_id if isinstance(plan_id, CommercialPlanId) else CommercialPlanId(plan_id)
    except ValueError as exc:
        raise CommercialPlanError("unknown commercial plan") from exc
    return _PLANS[canonical]


def commercial_plan_ids() -> tuple[str, ...]:
    return tuple(plan.value for plan in CommercialPlanId)
