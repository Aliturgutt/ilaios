"""Tests for the ILAIOS-native generated Next.js source project."""

from __future__ import annotations

from pathlib import Path

import pytest

from services.design_quality import DesignContext, NativeDesignStrategyEngine
from services.integrations.web_factory import derive_website_spec
from services.integrations.web_project import materialize_next_project


def _strategy() -> dict[str, object]:
    strategy = NativeDesignStrategyEngine().plan(
        DesignContext(
            business_category="law firm",
            audience="corporate decision makers",
            primary_goal="credible finished website",
            conversion_objective="contact conversion",
            brand_personality=("premium", "clear"),
            content_volume="medium",
            product_complexity="medium",
            trust_requirement="high",
            visual_asset_availability="standard",
            information_density="medium",
            locale="en",
        )
    )
    return {
        "primary_composition": strategy.primary_composition,
        "secondary_compositions": strategy.secondary_compositions,
        "type_behavior": strategy.type_behavior,
        "spacing_behavior": strategy.spacing_behavior,
        "surface_behavior": strategy.surface_behavior,
        "imagery_behavior": strategy.imagery_behavior,
        "cta_hierarchy": strategy.cta_hierarchy,
        "diagram_usage": strategy.diagram_usage,
        "motion_intensity": strategy.motion_intensity,
        "navigation_behavior": strategy.navigation_behavior,
        "mobile_transformation": strategy.mobile_transformation,
    }


def test_next_project_contains_real_react_typescript_routes(tmp_path: Path) -> None:
    spec = derive_website_spec(
        "web-next-project",
        "Build a premium bilingual Turkish/English website for a corporate law firm",
    )
    artifact = materialize_next_project(spec, _strategy(), tmp_path)
    root = Path(artifact.root_path)
    paths = {item.relative_path for item in artifact.files}

    assert artifact.digest
    assert "package.json" in paths
    assert "tsconfig.json" in paths
    assert "components/PageShell.tsx" in paths
    assert "app/en/page.tsx" in paths
    assert "app/en/contact/page.tsx" in paths
    assert "app/tr/page.tsx" in paths
    assert "app/tr/contact/page.tsx" in paths
    assert "next" in (root / "package.json").read_text(encoding="utf-8")
    assert "PageShell" in (root / "components/PageShell.tsx").read_text(encoding="utf-8")


def test_next_project_is_deterministic_and_tamper_evident(tmp_path: Path) -> None:
    spec = derive_website_spec(
        "web-next-project-stable",
        "Build a website for a security company serving enterprise teams",
    )
    first = materialize_next_project(spec, _strategy(), tmp_path)
    second = materialize_next_project(spec, _strategy(), tmp_path)
    assert second == first

    root = Path(first.root_path)
    (root / "app" / "page.tsx").write_text("tampered", encoding="utf-8")
    with pytest.raises(ValueError, match="tampered"):
        materialize_next_project(spec, _strategy(), tmp_path)
