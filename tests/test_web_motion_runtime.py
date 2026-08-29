from pathlib import Path

from services.design_quality import DesignContext, NativeDesignStrategyEngine
from services.integrations.web_factory import WebsiteSpec
from services.integrations.web_project import materialize_next_project


def _spec() -> WebsiteSpec:
    return WebsiteSpec(
        site_id="site-motion-test",
        business_name="Motion Studio",
        business_category="architecture studio",
        audience="design clients",
        primary_goal="show work",
        conversion_objective="inquiry",
        locales=("en", "tr"),
        pages=("home", "contact"),
        features=(),
        brand_personality=("editorial", "precise"),
        trust_requirement="standard",
        visual_asset_availability="rich",
        information_density="medium",
    )


def test_generated_next_project_contains_native_motion_runtime(tmp_path: Path) -> None:
    strategy = NativeDesignStrategyEngine().plan(
        DesignContext(
            "architecture studio",
            "design clients",
            "show work",
            "inquiry",
            ("editorial", "precise"),
            "medium",
            "medium",
            "standard",
            "rich",
            "medium",
        )
    )
    artifact = materialize_next_project(_spec(), strategy.__dict__ if hasattr(strategy, "__dict__") else {
        "primary_composition": strategy.primary_composition,
        "secondary_compositions": strategy.secondary_compositions,
        "type_behavior": strategy.type_behavior,
        "spacing_behavior": strategy.spacing_behavior,
        "surface_behavior": strategy.surface_behavior,
        "imagery_behavior": strategy.imagery_behavior,
        "cta_hierarchy": strategy.cta_hierarchy,
        "diagram_usage": strategy.diagram_usage,
        "motion_intensity": strategy.motion_intensity,
        "interaction_density": strategy.interaction_density,
        "scroll_behavior": strategy.scroll_behavior,
        "showcase_behavior": strategy.showcase_behavior,
        "motion_accessibility": strategy.motion_accessibility,
        "navigation_behavior": strategy.navigation_behavior,
        "mobile_transformation": strategy.mobile_transformation,
    }, tmp_path)

    root = Path(artifact.root_path)
    runtime = (root / "components" / "MotionRuntime.tsx").read_text(encoding="utf-8")
    shell = (root / "components" / "PageShell.tsx").read_text(encoding="utf-8")
    css = (root / "app" / "globals.css").read_text(encoding="utf-8")
    package = (root / "package.json").read_text(encoding="utf-8")

    assert '"use client"' in runtime
    assert "IntersectionObserver" in runtime
    assert "requestAnimationFrame" in runtime
    assert "prefers-reduced-motion: reduce" in runtime
    assert "pointermove" in runtime
    assert "<MotionRuntime />" in shell
    assert "data-motion-intensity" in shell
    assert "data-scroll-behavior" in shell
    assert "data-interactive=\"tilt\"" in shell
    assert '[data-motion="reveal"]' in css
    assert "@media(prefers-reduced-motion:reduce)" in css
    assert "framer-motion" not in package
    assert '"motion"' not in package


def test_motion_project_generation_is_deterministic(tmp_path: Path) -> None:
    strategy = NativeDesignStrategyEngine().plan(
        DesignContext(
            "architecture studio",
            "design clients",
            "show work",
            "inquiry",
            ("editorial",),
            "medium",
            "medium",
            "standard",
            "rich",
            "medium",
        )
    )
    mapping = {
        "primary_composition": strategy.primary_composition,
        "secondary_compositions": strategy.secondary_compositions,
        "motion_intensity": strategy.motion_intensity,
        "interaction_density": strategy.interaction_density,
        "scroll_behavior": strategy.scroll_behavior,
        "showcase_behavior": strategy.showcase_behavior,
        "motion_accessibility": strategy.motion_accessibility,
    }
    first = materialize_next_project(_spec(), mapping, tmp_path)
    second = materialize_next_project(_spec(), mapping, tmp_path)
    assert first.digest == second.digest
    assert first.project_id == second.project_id
