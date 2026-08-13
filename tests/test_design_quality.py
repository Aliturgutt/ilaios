from collections.abc import Callable
from typing import Any, cast

import pytest

from services.design_quality import (
    REQUIRED_VIEWPORTS,
    DesignObservation,
    NativeDesignQualityEvaluator,
)
from services.integrations.web_factory import GovernedWebFactory

parametrize = cast(
    Callable[..., Callable[[Callable[..., None]], Callable[..., None]]],
    pytest.mark.parametrize,
)


def complete_rows(**overrides: int) -> list[DesignObservation]:
    return [
        DesignObservation(
            route="/" if locale == "en" else "/tr",
            locale=locale,
            viewport=width,
            **cast(Any, overrides),
        )
        for locale in ("en", "tr")
        for width in REQUIRED_VIEWPORTS
    ]


def test_complete_clean_en_tr_matrix_passes_and_is_stable() -> None:
    evaluator = NativeDesignQualityEvaluator()
    first = evaluator.evaluate(complete_rows())
    second = evaluator.evaluate(reversed(complete_rows()))
    assert first.status == second.status == "PASS"
    assert first.findings == second.findings == ()
    GovernedWebFactory.accept_design_quality(first)


@parametrize(
    ("field", "category", "severity"),
    [
        ("horizontal_overflow", "design.responsive-quality", "major"),
        ("missing_focus_indicators", "design.interaction-quality", "p2"),
        ("contrast_failures", "design.typography-quality", "major"),
    ],
)
def test_blocking_defects_fail_closed(field: str, category: str, severity: str) -> None:
    result = NativeDesignQualityEvaluator().evaluate(complete_rows(**{field: 1}))
    assert result.status == "FAIL"
    assert any(f.category == category and f.severity == severity for f in result.findings)
    with pytest.raises(ValueError, match="quality gate failed"):
        GovernedWebFactory.accept_design_quality(result)


def test_missing_viewport_and_locale_evidence_is_blocking() -> None:
    result = NativeDesignQualityEvaluator().evaluate([
        DesignObservation(route="/", locale="en", viewport=320)
    ])
    assert result.status == "FAIL"
    assert {f.category for f in result.blocking_findings} == {
        "design.responsive-quality", "design.localization-parity"
    }


def test_contextual_anti_generic_signal_resists_simple_false_positives() -> None:
    low = NativeDesignQualityEvaluator().evaluate(complete_rows(unexplained_decorative_patterns=2))
    high = NativeDesignQualityEvaluator().evaluate(complete_rows(unexplained_decorative_patterns=3))
    assert low.findings == ()
    assert high.status == "PASS"
    assert all(f.severity == "minor" for f in high.findings)


def test_invalid_observation_is_rejected() -> None:
    with pytest.raises(ValueError, match="cannot be negative"):
        NativeDesignQualityEvaluator().evaluate([
            DesignObservation(route="/", locale="en", viewport=320, clipped_elements=-1)
        ])
