from pathlib import Path

from services.commercial_plans import CommercialPlanId, get_commercial_plan


ROOT = Path(__file__).resolve().parents[1]
SURFACE = ROOT / "apps" / "website" / "app" / "UseILAIOSPage.tsx"


def test_website_plan_surface_matches_locked_commercial_video_authority() -> None:
    content = SURFACE.read_text(encoding="utf-8")
    expected = {
        CommercialPlanId.PRO: (49, "Seedance 2.0 Mini", "480p", 20),
        CommercialPlanId.BUSINESS: (99, "Seedance 2.0 Fast", "720p", 30),
        CommercialPlanId.POWER: (199, "Seedance 2.0", "1080p", 50),
    }
    for plan_id, (price, model, resolution, minutes) in expected.items():
        plan = get_commercial_plan(plan_id)
        assert plan.monthly_price_usd == price
        assert model in plan.video_model_names
        assert plan.max_video_resolution == resolution
        assert plan.monthly_video_pool_mini_480p_equivalent_minutes == minutes
        assert f"${price} / month" in content
        assert resolution in content
        assert str(minutes) in content

    free = get_commercial_plan(CommercialPlanId.FREE)
    assert free.monthly_price_usd == 0
    assert free.max_video_resolution is None
    assert free.monthly_video_pool_mini_480p_equivalent_minutes is None

    enterprise = get_commercial_plan(CommercialPlanId.ENTERPRISE)
    assert enterprise.monthly_price_usd is None
    assert enterprise.max_video_resolution == "4K"
    assert enterprise.enterprise_custom_video_budget is True
