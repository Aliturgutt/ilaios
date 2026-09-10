from __future__ import annotations

from services.design_quality import (
    REQUIRED_VIEWPORTS,
    DesignObservation,
    NativeDesignQualityEvaluator,
)


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
    common = {"route": "/product", "locale": "en", "viewport": REQUIRED_VIEWPORTS[0]}
    if field == "giant_heading_failures":
        return DesignObservation(**common, giant_heading_failures=value)
    if field == "empty_visual_placeholders":
        return DesignObservation(**common, empty_visual_placeholders=value)
    if field == "excessive_whitespace_regions":
        return DesignObservation(**common, excessive_whitespace_regions=value)
    if field == "repeated_layout_failures":
        return DesignObservation(**common, repeated_layout_failures=value)
    if field == "cta_hierarchy_failures":
        return DesignObservation(**common, cta_hierarchy_failures=value)
    if field == "turkish_layout_failures":
        return DesignObservation(**common, turkish_layout_failures=value)
    if field == "mobile_hierarchy_failures":
        return DesignObservation(**common, mobile_hierarchy_failures=value)
    if field == "section_rhythm_failures":
        return DesignObservation(**common, section_rhythm_failures=value)
    if field == "missing_brand_asset_failures":
        return DesignObservation(**common, missing_brand_asset_failures=value)
    if field == "text_heavy_without_structure":
        return DesignObservation(**common, text_heavy_without_structure=value)
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


def test_professional_visual_quality_counts_cannot_be_negative() -> None:
    evaluator = NativeDesignQualityEvaluator()
    for field in _PROFESSIONAL_FAILURES:
        try:
            evaluator.evaluate([_observation_with_failure(field, -1)])
        except ValueError as exc:
            assert str(exc) == f"{field} cannot be negative"
        else:
            raise AssertionError(f"negative {field} must fail closed")
