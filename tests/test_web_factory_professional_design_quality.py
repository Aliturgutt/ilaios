from __future__ import annotations

import pytest

from services.design_quality import (
    REQUIRED_VIEWPORTS,
    DesignObservation,
    NativeDesignQualityEvaluator,
)


def _clean_matrix() -> list[DesignObservation]:
    return [
        DesignObservation(route="/product", locale=locale, viewport=viewport)
        for locale in ("en", "tr")
        for viewport in REQUIRED_VIEWPORTS
    ]


def test_professional_visual_quality_signals_are_blocking() -> None:
    evaluator = NativeDesignQualityEvaluator()
    fields = (
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

    for field in fields:
        rows = _clean_matrix()
        rows[0] = DesignObservation(
            route="/product",
            locale="en",
            viewport=REQUIRED_VIEWPORTS[0],
            **{field: 1},
        )
        assessment = evaluator.evaluate(rows)
        assert assessment.status == "FAIL"
        assert assessment.blocking_findings
        assert any(finding.evidence.get(field) == 1 for finding in assessment.findings)


def test_professional_visual_quality_clean_matrix_passes() -> None:
    assessment = NativeDesignQualityEvaluator().evaluate(_clean_matrix())
    assert assessment.status == "PASS"
    assert assessment.blocking_findings == ()


@pytest.mark.parametrize(
    "field",
    (
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
    ),
)
def test_professional_visual_quality_counts_cannot_be_negative(field: str) -> None:
    with pytest.raises(ValueError, match=f"{field} cannot be negative"):
        NativeDesignQualityEvaluator().evaluate(
            [
                DesignObservation(
                    route="/product",
                    locale="en",
                    viewport=320,
                    **{field: -1},
                )
            ]
        )
