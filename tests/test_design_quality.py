from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

import pytest

from services.design_quality import (
    REQUIRED_VIEWPORTS,
    DesignContext,
    DesignObservation,
    NativeDesignQualityEvaluator,
    NativeDesignStrategyEngine,
)
from services.integrations.web_factory import GovernedWebFactory
from services.runtime import GrantPolicy

parametrize = cast(Callable[..., Callable[[Callable[..., None]], Callable[..., None]]], pytest.mark.parametrize)


def complete_rows(**overrides: int) -> list[DesignObservation]:
    return [DesignObservation(route="/" if locale == "en" else "/tr", locale=locale, viewport=width, **cast(Any, overrides)) for locale in ("en", "tr") for width in REQUIRED_VIEWPORTS]


def sample_context(category: str = "developer platform", locale: str = "en") -> DesignContext:
    return DesignContext(category, "engineering teams", "explain product", "product evaluation", ("precise", "restrained"), "high", "high", "high", "medium", "high", locale)


def test_complete_clean_en_tr_matrix_passes_and_is_stable() -> None:
    evaluator = NativeDesignQualityEvaluator()
    first = evaluator.evaluate(complete_rows())
    second = evaluator.evaluate(reversed(complete_rows()))
    assert first.status == second.status == "PASS"
    assert first.findings == second.findings == ()
    GovernedWebFactory.accept_design_quality(first)


@parametrize(("field", "category", "severity"), [("horizontal_overflow", "design.responsive-quality", "major"), ("missing_focus_indicators", "design.interaction-quality", "p2"), ("contrast_failures", "design.typography-quality", "major")])
def test_blocking_defects_fail_closed(field: str, category: str, severity: str) -> None:
    result = NativeDesignQualityEvaluator().evaluate(complete_rows(**{field: 1}))
    assert result.status == "FAIL"
    assert any(f.category == category and f.severity == severity for f in result.findings)
    with pytest.raises(ValueError, match="quality gate failed"):
        GovernedWebFactory.accept_design_quality(result)


def test_missing_viewport_and_locale_evidence_is_blocking() -> None:
    result = NativeDesignQualityEvaluator().evaluate([DesignObservation(route="/", locale="en", viewport=320)])
    assert result.status == "FAIL"
    assert {f.category for f in result.blocking_findings} == {"design.responsive-quality", "design.localization-parity"}


def test_contextual_anti_generic_signal_resists_simple_false_positives() -> None:
    low = NativeDesignQualityEvaluator().evaluate(complete_rows(unexplained_decorative_patterns=2))
    high = NativeDesignQualityEvaluator().evaluate(complete_rows(unexplained_decorative_patterns=3))
    assert low.findings == ()
    assert high.status == "PASS"
    assert all(f.severity == "minor" for f in high.findings)


def test_structural_repetition_is_blocking() -> None:
    result = NativeDesignQualityEvaluator().evaluate(complete_rows(repeated_equal_card_groups=3, repeated_centered_sections=2))
    assert result.status == "FAIL"
    assert any(f.category == "design.anti-generic-ai" and f.severity == "p2" for f in result.findings)


def test_invalid_observation_is_rejected() -> None:
    with pytest.raises(ValueError, match="cannot be negative"):
        NativeDesignQualityEvaluator().evaluate([DesignObservation(route="/", locale="en", viewport=320, clipped_elements=-1)])


def test_design_strategy_is_deterministic() -> None:
    engine = NativeDesignStrategyEngine()
    first = engine.plan(sample_context())
    second = engine.plan(sample_context())
    assert first == second
    assert first.primary_composition == "technical-flow"
    assert first.motion_intensity == "low"
    assert first.interaction_density == "low"
    assert first.scroll_behavior == "standard"
    assert first.showcase_behavior == "static-evidence"
    assert first.motion_accessibility == "reduced-motion-static-equivalent"
    assert first.mobile_transformation == "reorder-reduce-and-recompose"
    assert engine.fingerprint(first, ("hero", "architecture")).section_sequence == ("hero", "architecture")


def test_web_factory_reuses_design_strategy(tmp_path: Path) -> None:
    factory = GovernedWebFactory(GrantPolicy(), tmp_path)
    first = factory.plan_design(sample_context())
    second = factory.plan_design(sample_context())
    assert first == second
    assert first.primary_composition == "technical-flow"


def test_context_changes_composition() -> None:
    engine = NativeDesignStrategyEngine()
    technical = engine.plan(sample_context())
    visual = engine.plan(DesignContext("architecture studio", "clients", "show work", "inquiry", ("editorial",), "medium", "medium", "medium", "rich", "medium", "tr"))
    assert technical.primary_composition != visual.primary_composition
    assert visual.primary_composition == "visual-portfolio"


def test_invalid_design_context_is_rejected() -> None:
    with pytest.raises(ValueError, match="locale"):
        NativeDesignStrategyEngine().plan(sample_context(locale="de"))


def test_visual_context_gets_dynamic_but_bounded_motion_strategy() -> None:
    strategy = NativeDesignStrategyEngine().plan(
        DesignContext(
            "architecture studio",
            "clients",
            "show work",
            "inquiry",
            ("editorial",),
            "medium",
            "medium",
            "medium",
            "rich",
            "medium",
            "en",
        )
    )
    assert strategy.motion_intensity == "expressive"
    assert strategy.interaction_density == "high"
    assert strategy.scroll_behavior == "narrative-linked"
    assert strategy.showcase_behavior == "asset-led-interactive"


def test_motion_qa_failures_are_blocking() -> None:
    result = NativeDesignQualityEvaluator().evaluate(
        complete_rows(
            scroll_jank_failures=1,
            motion_budget_failures=1,
            showcase_fallback_failures=1,
        )
    )
    assert result.status == "FAIL"
    categories = {finding.category for finding in result.blocking_findings}
    assert "design.motion-performance" in categories
    assert "design.motion-accessibility" in categories
