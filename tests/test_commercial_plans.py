from __future__ import annotations

import pytest

from services.commercial_plans import (
    CommercialPlanError,
    CommercialPlanId,
    commercial_plan_ids,
    get_commercial_plan,
)


def test_plan_family_is_single_ordered_authority() -> None:
    assert commercial_plan_ids() == (
        "FREE",
        "PRO",
        "BUSINESS",
        "POWER",
        "ENTERPRISE",
    )
    assert get_commercial_plan("FREE").parent is None
    assert get_commercial_plan("PRO").parent is CommercialPlanId.FREE
    assert get_commercial_plan("BUSINESS").parent is CommercialPlanId.PRO
    assert get_commercial_plan("POWER").parent is CommercialPlanId.BUSINESS
    assert get_commercial_plan("ENTERPRISE").parent is CommercialPlanId.POWER


def test_uploaded_price_references_are_preserved() -> None:
    assert get_commercial_plan("FREE").monthly_price_usd == 0
    assert get_commercial_plan("PRO").monthly_price_usd == 49
    assert get_commercial_plan("BUSINESS").monthly_price_usd == 99
    assert get_commercial_plan("POWER").monthly_price_usd == 199
    assert get_commercial_plan("ENTERPRISE").monthly_price_usd is None


def test_free_plan_is_fail_closed_for_paid_provider_dispatch() -> None:
    free = get_commercial_plan("FREE")
    assert free.paid_provider_allowed is False
    assert free.monthly_provider_budget_usd == 0
    assert free.paid_dispatch_budget_verified is False
    assert free.workspace_users == 1
    assert free.max_concurrent_jobs == 1
    assert free.max_active_projects == 3
    assert free.max_active_automations == 1
    assert free.automation_runs_per_month == 30
    assert free.storage_limit_gb == 2
    assert free.history_evidence_retention_days == 30


def test_paid_plans_remain_fail_closed_until_provider_budget_is_configured() -> None:
    for plan_id in ("PRO", "BUSINESS", "POWER", "ENTERPRISE"):
        plan = get_commercial_plan(plan_id)
        assert plan.paid_provider_allowed is True
        assert plan.monthly_provider_budget_usd is None
        assert plan.paid_dispatch_budget_verified is False


def test_unknown_plan_is_rejected() -> None:
    with pytest.raises(CommercialPlanError, match="unknown commercial plan"):
        get_commercial_plan("LEGACY")
