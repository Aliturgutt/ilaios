from __future__ import annotations

from services.design_quality import (
    REQUIRED_VIEWPORTS,
    DesignObservation,
    NativeDesignQualityEvaluator,
)
from services.web_screenshot_fidelity import assess_visual_quality


_PROFESSIONAL_FAILURES = (
    "giant_heading_failures",
    "empty_visual_placeholders",
    "excessive_whitespace_regions",
    "repeated_layout_failures",
    "cta_hierarchy_failures",
    "turkish_layout_failures",
    "mobile_hierarchy_failures",
    "section_rhythm_failures",
    "missing_brand_asset_failures",
    "text_heavy_without_structure",
)


def _clean_matrix() -> list[DesignObservation]:
    return [
        DesignObservation(route="/product", locale=locale, viewport=viewport)
        for locale in ("en", "tr")
        for viewport in REQUIRED_VIEWPORTS
    ]


def _observation_with_failure(field: str, value: int) -> DesignObservation:
    if field == "giant_heading_failures":
        return DesignObservation("/product", "en", REQUIRED_VIEWPORTS[0], giant_heading_failures=value)
    if field == "empty_visual_placeholders":
        return DesignObservation("/product", "en", REQUIRED_VIEWPORTS[0], empty_visual_placeholders=value)
    if field == "excessive_whitespace_regions":
        return DesignObservation("/product", "en", REQUIRED_VIEWPORTS[0], excessive_whitespace_regions=value)
    if field == "repeated_layout_failures":
        return DesignObservation("/product", "en", REQUIRED_VIEWPORTS[0], repeated_layout_failures=value)
    if field == "cta_hierarchy_failures":
        return DesignObservation("/product", "en", REQUIRED_VIEWPORTS[0], cta_hierarchy_failures=value)
    if field == "turkish_layout_failures":
        return DesignObservation("/product", "en", REQUIRED_VIEWPORTS[0], turkish_layout_failures=value)
    if field == "mobile_hierarchy_failures":
        return DesignObservation("/product", "en", REQUIRED_VIEWPORTS[0], mobile_hierarchy_failures=value)
    if field == "section_rhythm_failures":
        return DesignObservation("/product", "en", REQUIRED_VIEWPORTS[0], section_rhythm_failures=value)
    if field == "missing_brand_asset_failures":
        return DesignObservation("/product", "en", REQUIRED_VIEWPORTS[0], missing_brand_asset_failures=value)
    if field == "text_heavy_without_structure":
        return DesignObservation("/product", "en", REQUIRED_VIEWPORTS[0], text_heavy_without_structure=value)
    raise AssertionError(f"unsupported professional quality field: {field}")


def test_professional_visual_quality_signals_are_blocking() -> None:
    evaluator = NativeDesignQualityEvaluator()
    for field in _PROFESSIONAL_FAILURES:
        rows = _clean_matrix()
        rows[0] = _observation_with_failure(field, 1)
        assessment = evaluator.evaluate(rows)
        assert assessment.status == "FAIL"
        assert assessment.blocking_findings
        assert any(finding.evidence.get(field) == 1 for finding in assessment.findings)


def test_professional_visual_quality_clean_matrix_passes() -> None:
    assessment = NativeDesignQualityEvaluator().evaluate(_clean_matrix())
    assert assessment.status == "PASS"
    assert assessment.blocking_findings == ()
    gate = assess_visual_quality(_clean_matrix(), attempt=1)
    assert gate.status == "PASS"
    assert gate.accepted is True
    assert gate.scores.overall == 100
    assert gate.scores.critical == 100
    assert gate.scores.accessibility == 100
    assert gate.scores.mobile == 100
    assert gate.thresholds == {"critical": 70, "overall": 80, "accessibility": 85, "mobile": 80}


def test_professional_visual_quality_counts_cannot_be_negative() -> None:
    evaluator = NativeDesignQualityEvaluator()
    for field in _PROFESSIONAL_FAILURES:
        try:
            evaluator.evaluate([_observation_with_failure(field, -1)])
        except ValueError as exc:
            assert str(exc) == f"{field} cannot be negative"
        else:
            raise AssertionError(f"negative {field} must fail closed")


def test_visual_quality_revises_before_final_attempt_and_fails_closed_on_attempt_three() -> None:
    rows = _clean_matrix()
    rows[0] = DesignObservation("/product", "en", REQUIRED_VIEWPORTS[0], giant_heading_failures=1)
    first = assess_visual_quality(rows, attempt=1)
    third = assess_visual_quality(rows, attempt=3)
    assert first.status == "REVISE"
    assert first.accepted is False
    assert third.status == "DESIGN_QUALITY_FAILED"
    assert third.accepted is False
    assert third.remaining_attempts == 0


def test_accessibility_and_mobile_score_thresholds_are_measurable() -> None:
    accessibility_rows = _clean_matrix()
    accessibility_rows[0] = DesignObservation(
        "/product",
        "en",
        REQUIRED_VIEWPORTS[0],
        missing_focus_indicators=8,
        undersized_touch_targets=8,
    )
    accessibility = assess_visual_quality(accessibility_rows, attempt=1)
    assert accessibility.scores.accessibility < 85
    assert accessibility.status == "REVISE"

    mobile_rows = _clean_matrix()
    mobile_rows[0] = DesignObservation(
        "/product",
        "en",
        REQUIRED_VIEWPORTS[0],
        mobile_hierarchy_failures=2,
        giant_heading_failures=1,
    )
    mobile = assess_visual_quality(mobile_rows, attempt=1)
    assert mobile.scores.mobile < 80
    assert mobile.status == "REVISE"
