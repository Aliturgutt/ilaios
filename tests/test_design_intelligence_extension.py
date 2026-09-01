"""Clean-room red-team proofs for expanded ILAIOS UI/design intelligence."""

from typing import Any, cast

from services.app_design_quality import (
    AppDesignObservation,
    NativeAppDesignQualityEvaluator,
)
from services.design_quality import (
    REQUIRED_VIEWPORTS,
    DesignObservation,
    NativeDesignQualityEvaluator,
)
from src.ilaios_ui_design import resolve_ui_design


def _web_rows(**overrides: Any) -> list[DesignObservation]:
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


def _app_rows(**overrides: int) -> list[AppDesignObservation]:
    return [
        AppDesignObservation(
            "control-center",
            "windows",
            form_factor,
            width,
            800,
            **cast(Any, overrides),
        )
        for form_factor, width in (("compact", 600), ("wide", 1440))
    ]


def test_ui_spec_carries_expanded_quality_gates_without_new_authority() -> None:
    spec = resolve_ui_design("dashboard design", product="ILAIOS")
    assert spec.schema_version == "ilaios.ui-spec.v1"
    assert "semantic-labels-and-alt-text-when-applicable" in spec.quality_gates
    assert "form-feedback-near-source-when-applicable" in spec.quality_gates
    assert "layout-stability" in spec.quality_gates
    assert "non-color-only-data-encoding-when-applicable" in spec.quality_gates
    assert "predictable-navigation-and-back-behavior" in spec.quality_gates
    assert "existing-ilaios-design-quality-authority" in spec.quality_gates


def test_web_accessibility_form_performance_navigation_and_chart_failures_block() -> None:
    cases = (
        ("missing_alt_text", "design.accessibility", "major"),
        ("unlabeled_icon_controls", "design.accessibility", "major"),
        ("hover_only_interactions", "design.interaction-quality", "p2"),
        ("form_label_failures", "design.form-feedback", "major"),
        ("field_feedback_failures", "design.form-feedback", "p2"),
        ("layout_shift_failures", "design.performance-quality", "p2"),
        ("navigation_hierarchy_failures", "design.navigation-quality", "major"),
        ("chart_accessibility_failures", "design.data-visualization", "p2"),
    )
    evaluator = NativeDesignQualityEvaluator()
    for field, category, severity in cases:
        result = evaluator.evaluate(_web_rows(**{field: 1}))
        assert result.status == "FAIL"
        assert any(
            finding.category == category and finding.severity == severity
            for finding in result.findings
        )


def test_web_fluid_interaction_and_motion_failures_block() -> None:
    cases = (
        ("input_feedback_failures", "design.interaction-response"),
        ("gesture_tracking_failures", "design.gesture-continuity"),
        ("non_interruptible_motion_failures", "design.motion-quality"),
        ("velocity_handoff_failures", "design.motion-quality"),
        ("spatial_transition_failures", "design.motion-quality"),
        ("text_scaling_failures", "design.typography-quality"),
    )
    evaluator = NativeDesignQualityEvaluator()
    for field, category in cases:
        result = evaluator.evaluate(_web_rows(**{field: 1}))
        assert result.status == "FAIL"
        assert any(
            finding.category == category and finding.severity == "p2"
            for finding in result.findings
        )


def test_web_accessibility_motion_fallbacks_fail_closed_when_required() -> None:
    evaluator = NativeDesignQualityEvaluator()
    for field in ("reduced_transparency_supported", "increased_contrast_supported"):
        result = evaluator.evaluate(_web_rows(**{field: False}))
        assert result.status == "FAIL"
        assert any(
            finding.category == "design.accessibility"
            and finding.severity == "p2"
            and finding.evidence.get(field) is False
            for finding in result.findings
        )


def test_app_safe_area_navigation_labels_scaling_and_data_gates_block() -> None:
    cases = (
        ("safe_area_failures", "design.app-layout", "major"),
        ("back_navigation_failures", "design.app-navigation", "major"),
        ("missing_accessible_labels", "design.app-accessibility", "major"),
        ("touch_spacing_failures", "design.app-interaction", "p2"),
        ("text_scaling_failures", "design.app-accessibility", "p2"),
        ("deep_link_failures", "design.app-navigation", "p2"),
        ("chart_accessibility_failures", "design.app-data-visualization", "p2"),
    )
    evaluator = NativeAppDesignQualityEvaluator()
    for field, category, severity in cases:
        result = evaluator.evaluate(
            _app_rows(**{field: 1}),
            required_surfaces=("windows:compact", "windows:wide"),
        )
        assert result.status == "FAIL"
        assert any(
            finding.category == category and finding.severity == severity
            for finding in result.findings
        )


def test_clean_rows_still_pass_after_additive_quality_extension() -> None:
    assert NativeDesignQualityEvaluator().evaluate(_web_rows()).status == "PASS"
    assert (
        NativeAppDesignQualityEvaluator()
        .evaluate(
            _app_rows(),
            required_surfaces=("windows:compact", "windows:wide"),
        )
        .status
        == "PASS"
    )
