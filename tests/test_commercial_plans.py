from __future__ import annotations

import pytest

from services.commercial_plans import (
    CommercialPlanError,
    CommercialPlanId,
    commercial_plan_ids,
    get_commercial_plan,
)


def test_plan_family_is_single_ordered_authority() -> None:
    assert commercial_plan_ids() == ("FREE", "PRO", "BUSINESS", "POWER", "ENTERPRISE")
    assert get_commercial_plan("FREE").parent is None
    assert get_commercial_plan("PRO").parent is CommercialPlanId.FREE
    assert get_commercial_plan("BUSINESS").parent is CommercialPlanId.PRO
    assert get_commercial_plan("POWER").parent is CommercialPlanId.BUSINESS
    assert get_commercial_plan("ENTERPRISE").parent is CommercialPlanId.POWER


def test_approved_price_references_are_preserved() -> None:
    assert get_commercial_plan("FREE").monthly_price_usd == 0
    assert get_commercial_plan("FREE").monthly_price_try == 0
    assert get_commercial_plan("PRO").monthly_price_usd == 49
    assert get_commercial_plan("PRO").monthly_price_try == 2401
    assert get_commercial_plan("BUSINESS").monthly_price_usd == 99
    assert get_commercial_plan("BUSINESS").monthly_price_try == 4851
    assert get_commercial_plan("POWER").monthly_price_usd == 199
    assert get_commercial_plan("POWER").monthly_price_try == 9751
    assert get_commercial_plan("ENTERPRISE").monthly_price_usd is None
    assert get_commercial_plan("ENTERPRISE").monthly_price_try is None


def test_video_resolution_hierarchy_is_locked() -> None:
    assert get_commercial_plan("FREE").max_video_resolution is None
    assert get_commercial_plan("PRO").max_video_resolution == "480p"
    assert get_commercial_plan("BUSINESS").max_video_resolution == "720p"
    assert get_commercial_plan("POWER").max_video_resolution == "1080p"
    assert get_commercial_plan("ENTERPRISE").max_video_resolution == "4K"


def test_free_video_has_no_fixed_minutes_and_requires_verified_zero_cost() -> None:
    free = get_commercial_plan("FREE")
    assert free.paid_provider_allowed is False
    assert free.monthly_provider_budget_usd == 0
    assert free.paid_dispatch_budget_verified is False
    assert free.video_model_names == ("verified-zero-cost-provider/model",)
    assert free.max_video_resolution is None
    assert free.monthly_video_pool_mini_480p_equivalent_minutes is None
    assert free.approximate_video_equivalents == ()
    assert free.free_video_requires_verified_zero_cost is True
    assert (free.workspace_users, free.max_concurrent_jobs, free.max_active_projects) == (1, 1, 3)
    assert (free.max_active_automations, free.automation_runs_per_month, free.storage_limit_gb) == (1, 30, 2)
    assert free.history_evidence_retention_days == 30


def test_paid_operational_allowances_are_locked() -> None:
    pro = get_commercial_plan("PRO")
    assert (pro.max_active_projects, pro.max_active_automations, pro.automation_runs_per_month) == (10, 3, 150)
    assert (pro.storage_limit_gb, pro.max_concurrent_jobs, pro.workspace_users) == (10, 2, 1)
    business = get_commercial_plan("BUSINESS")
    assert (business.max_active_projects, business.max_active_automations, business.automation_runs_per_month) == (30, 10, 500)
    assert (business.storage_limit_gb, business.max_concurrent_jobs, business.workspace_users) == (50, 4, 3)
    power = get_commercial_plan("POWER")
    assert (power.max_active_projects, power.max_active_automations, power.automation_runs_per_month) == (100, 25, 2000)
    assert (power.storage_limit_gb, power.max_concurrent_jobs, power.workspace_users) == (100, 8, 10)
    assert get_commercial_plan("ENTERPRISE").max_concurrent_jobs is None


def test_pro_video_allowance_is_one_shared_twenty_minute_pool() -> None:
    pro = get_commercial_plan("PRO")
    assert pro.video_model_names == ("Seedance 2.0 Mini",)
    assert pro.max_video_resolution == "480p"
    assert pro.monthly_video_pool_mini_480p_equivalent_minutes == 20
    assert pro.approximate_video_equivalents == ()


def test_business_video_allowance_is_one_shared_thirty_minute_pool() -> None:
    business = get_commercial_plan("BUSINESS")
    assert business.video_model_names == ("Seedance 2.0 Mini", "Seedance 2.0 Fast")
    assert business.max_video_resolution == "720p"
    assert business.monthly_video_pool_mini_480p_equivalent_minutes == 30
    assert business.approximate_video_equivalents == ("Seedance 2.0 Fast 480p: 10 min", "Seedance 2.0 Fast 720p: 4-5 min")


def test_power_video_allowance_is_one_shared_fifty_minute_pool() -> None:
    power = get_commercial_plan("POWER")
    assert power.video_model_names == ("Seedance 2.0 Mini", "Seedance 2.0 Fast", "Seedance 2.0")
    assert power.max_video_resolution == "1080p"
    assert power.monthly_video_pool_mini_480p_equivalent_minutes == 50
    assert power.approximate_video_equivalents == ("Seedance 2.0 Fast 480p: 16-17 min", "Seedance 2.0 480p: 10 min")


def test_enterprise_video_allowance_is_contract_specific() -> None:
    enterprise = get_commercial_plan("ENTERPRISE")
    assert enterprise.video_model_names == ("Seedance 2.0 Mini", "Seedance 2.0 Fast", "Seedance 2.0", "contract-allowlisted-models")
    assert enterprise.max_video_resolution == "4K"
    assert enterprise.monthly_video_pool_mini_480p_equivalent_minutes is None
    assert enterprise.enterprise_custom_video_budget is True


def test_paid_provider_spend_ceiling_is_separate_from_customer_video_allowance() -> None:
    for plan_id in ("PRO", "BUSINESS", "POWER", "ENTERPRISE"):
        plan = get_commercial_plan(plan_id)
        assert plan.paid_provider_allowed is True
        assert plan.monthly_provider_budget_usd is None
        assert plan.paid_dispatch_budget_verified is False


def test_unknown_plan_is_rejected() -> None:
    with pytest.raises(CommercialPlanError, match="unknown commercial plan"):
        get_commercial_plan("LEGACY")
