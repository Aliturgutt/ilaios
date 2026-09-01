"""Contract tests for ILAIOS-native app design quality."""

import pytest

from services.app_design_quality import (
    AppDesignAssessment,
    AppDesignObservation,
    NativeAppDesignQualityEvaluator,
)
from services.app_factory import AppFactory


def complete_rows(**overrides: int) -> list[AppDesignObservation]:
    return [
        AppDesignObservation(
            "control-center",
            "windows",
            form_factor,
            width,
            800,
            clipped_elements=overrides.get("clipped_elements", 0),
            overlapping_elements=overrides.get("overlapping_elements", 0),
            missing_semantics=overrides.get("missing_semantics", 0),
            focus_traversal_failures=overrides.get("focus_traversal_failures", 0),
            missing_focus_indicators=overrides.get("missing_focus_indicators", 0),
            missing_interaction_states=overrides.get("missing_interaction_states", 0),
            undersized_touch_targets=overrides.get("undersized_touch_targets", 0),
            contrast_failures=overrides.get("contrast_failures", 0),
            inconsistent_components=overrides.get("inconsistent_components", 0),
            navigation_adaptation_failures=overrides.get(
                "navigation_adaptation_failures", 0
            ),
            dialog_or_sheet_failures=overrides.get("dialog_or_sheet_failures", 0),
            unexplained_decorative_patterns=overrides.get(
                "unexplained_decorative_patterns", 0
            ),
        )
        for form_factor, width in (("compact", 600), ("wide", 1440))
    ]


def test_complete_windows_evidence_passes_app_factory_gate() -> None:
    assessment = NativeAppDesignQualityEvaluator().evaluate(
        complete_rows(), required_surfaces=("windows:compact", "windows:wide")
    )
    assert assessment.status == "PASS"
    assert assessment.blocking_findings == ()
    AppFactory.accept_design_quality(assessment)


def test_blocking_defects_fail_closed() -> None:
    cases = (
        ("clipped_elements", "design.app-layout", "major"),
        ("missing_semantics", "design.app-accessibility", "p2"),
        ("missing_interaction_states", "design.app-interaction", "p2"),
        ("navigation_adaptation_failures", "design.app-navigation", "major"),
        ("dialog_or_sheet_failures", "design.app-interaction", "major"),
    )
    for field, category, severity in cases:
        assessment = NativeAppDesignQualityEvaluator().evaluate(
            complete_rows(**{field: 1}),
            required_surfaces=("windows:compact", "windows:wide"),
        )
        assert assessment.status == "FAIL"
        assert any(
            finding.category == category and finding.severity == severity
            for finding in assessment.findings
        )
        with pytest.raises(ValueError, match="app design quality gate failed"):
            AppFactory.accept_design_quality(assessment)


def test_missing_declared_surface_fails_closed() -> None:
    assessment = NativeAppDesignQualityEvaluator().evaluate(
        complete_rows(),
        required_surfaces=("windows:compact", "windows:wide", "android:compact"),
    )
    assert assessment.status == "FAIL"
    assert assessment.findings[-1].evidence == {"missing_surfaces": ("android:compact",)}


def test_invalid_and_negative_evidence_is_rejected() -> None:
    evaluator = NativeAppDesignQualityEvaluator()
    with pytest.raises(ValueError, match="platform is unsupported"):
        evaluator.evaluate(
            [AppDesignObservation("home", "linux", "wide", 1440, 900)],
            required_surfaces=("linux:wide",),
        )
    with pytest.raises(ValueError, match="cannot be negative"):
        evaluator.evaluate(
            complete_rows(clipped_elements=-1),
            required_surfaces=("windows:compact", "windows:wide"),
        )


def test_app_factory_rejects_spoofed_evaluator() -> None:
    assessment = AppDesignAssessment(
        "other.evaluator", "1.0.0", "PASS", (), ("windows:wide",), ("windows:wide",)
    )
    with pytest.raises(ValueError, match="unrecognized app design quality evaluator"):
        AppFactory.accept_design_quality(assessment)
