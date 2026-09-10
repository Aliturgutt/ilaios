"""Read-only subscription projection; no pricing or entitlement authority.

The caller supplies the incumbent commercial store and a verified principal.
Missing runtime wiring, prices, usage and lifecycle policy remain unavailable.
"""

from __future__ import annotations

from datetime import datetime

from services.commercial_access import CommercialAccessError, CommercialAccessStore
from services.commercial_plans import commercial_plan_ids, get_commercial_plan
from services.identity import Principal


def presentation_currency(locale: str, currency: str | None = None) -> str:
    if locale not in {"tr", "en"}:
        raise ValueError("unsupported locale")
    expected = "TRY" if locale == "tr" else "USD"
    if currency is not None and currency != expected:
        raise ValueError("unsupported currency for locale")
    return expected


def plan_catalog(locale: str, currency: str | None = None) -> dict[str, object]:
    selected_currency = presentation_currency(locale, currency)
    plans: list[dict[str, object]] = []
    for plan_id in commercial_plan_ids():
        plan = get_commercial_plan(plan_id)
        # USD is a catalog reference, never a client-calculated checkout quote.
        amount = plan.monthly_price_usd if selected_currency == "USD" else None
        if plan.monthly_price_usd == 0:
            amount = 0
        plans.append({
            "plan_id": plan_id,
            "parent": None if plan.parent is None else plan.parent.value,
            "monthly_price": amount,
            "currency": selected_currency,
            "price_kind": "custom" if plan.monthly_price_usd is None else (
                "unavailable" if amount is None else "reference"
            ),
            "workspace_users": plan.workspace_users,
            "max_active_projects": plan.max_active_projects,
            "max_active_automations": plan.max_active_automations,
            "automation_runs_per_month": plan.automation_runs_per_month,
            "storage_limit_gb": plan.storage_limit_gb,
            "max_concurrent_jobs": plan.max_concurrent_jobs,
            "video_models": list(plan.video_model_names),
            "max_video_resolution": plan.max_video_resolution,
            "video_pool_minutes": plan.monthly_video_pool_mini_480p_equivalent_minutes,
            "free_video_requires_verified_zero_cost": plan.free_video_requires_verified_zero_cost,
            "enterprise_custom_video_budget": plan.enterprise_custom_video_budget,
        })
    return {"locale": locale, "currency": selected_currency, "plans": plans}


def subscription_state(
    store: CommercialAccessStore | None, principal: Principal, now: datetime
) -> dict[str, object]:
    current: dict[str, object] = {
        "plan_id": None, "status": "UNKNOWN", "valid_until": None,
        "usage": None, "renewal": None,
    }
    if store is not None:
        try:
            entitlement = store.get_entitlement(
                tenant_id=principal.tenant_id, user_id=principal.principal_id
            )
        except CommercialAccessError:
            pass
        else:
            # Legacy/unrecognized plan identifiers are not silently mapped.
            if entitlement.plan_id in commercial_plan_ids():
                status = entitlement.state.value
                if status == "ACTIVE" and entitlement.valid_until is not None:
                    if entitlement.valid_until <= now:
                        status = "EXPIRED"
                current.update(
                    plan_id=entitlement.plan_id, status=status,
                    valid_until=(entitlement.valid_until.isoformat()
                                 if entitlement.valid_until is not None else None),
                )
    return {
        "current_plan": current,
        "actions": {"checkout": False, "upgrade": False, "downgrade": False,
                    "cancel": False, "renew": False},
    }


def checkout_preview(plan_id: str, locale: str, currency: str) -> dict[str, object]:
    presentation_currency(locale, currency)
    plan = get_commercial_plan(plan_id)
    return {
        "plan_id": plan.plan_id.value, "currency": currency,
        "final_price": None, "available": False,
        "reason": "checkout_unavailable",
    }
