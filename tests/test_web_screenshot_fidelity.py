from __future__ import annotations

from dataclasses import replace

import pytest

from services.web_screenshot_fidelity import (
    ScreenshotFidelityObservation,
    assess_screenshot_fidelity,
)


def _observation() -> ScreenshotFidelityObservation:
    return ScreenshotFidelityObservation(
        route="/dashboard",
        locale="en",
        viewport=1440,
        reference_sha256="a" * 64,
        generated_sha256="b" * 64,
        source_sha256="c" * 64,
        pixel_mismatch_ratio=0.02,
        layout_mismatch_ratio=0.01,
        text_mismatch_ratio=0.01,
    )


def test_passes_when_fixed_fidelity_budgets_and_layout_safety_hold() -> None:
    assessment = assess_screenshot_fidelity(_observation(), attempt=1)
    assert assessment.status == "PASS"
    assert assessment.findings == ()
    assert assessment.repair_allowed is False
    assert assessment.remaining_attempts == 2


def test_requests_bounded_repair_without_granting_mutation_authority() -> None:
    observation = replace(
        _observation(),
        pixel_mismatch_ratio=0.11,
        layout_mismatch_ratio=0.04,
        horizontal_overflow_px=12,
    )
    assessment = assess_screenshot_fidelity(observation, attempt=1)
    assert assessment.status == "REVISE"
    assert assessment.repair_allowed is True
    assert {finding.category for finding in assessment.findings} == {
        "responsive-overflow",
        "layout-fidelity",
        "visual-fidelity",
    }
    assert {finding.repair_scope for finding in assessment.findings} <= {
        "layout-responsive",
        "layout-geometry",
        "visual-presentation",
    }


def test_third_failed_attempt_is_terminal_and_cannot_loop_forever() -> None:
    observation = replace(_observation(), text_mismatch_ratio=0.25)
    assessment = assess_screenshot_fidelity(observation, attempt=3)
    assert assessment.status == "FAIL"
    assert assessment.repair_allowed is False
    assert assessment.remaining_attempts == 0


@pytest.mark.parametrize("attempt", [0, 4, 100])
def test_rejects_attempts_outside_canonical_bound(attempt: int) -> None:
    with pytest.raises(ValueError, match="between 1 and 3"):
        assess_screenshot_fidelity(_observation(), attempt=attempt)


def test_rejects_noncanonical_viewport_and_locale() -> None:
    with pytest.raises(ValueError, match="viewport"):
        assess_screenshot_fidelity(replace(_observation(), viewport=999), attempt=1)
    with pytest.raises(ValueError, match="locale"):
        assess_screenshot_fidelity(replace(_observation(), locale="de"), attempt=1)


def test_rejects_missing_or_malformed_immutable_lineage() -> None:
    malformed = "bad"
    observations = (
        replace(_observation(), reference_sha256=malformed),
        replace(_observation(), generated_sha256=malformed),
        replace(_observation(), source_sha256=malformed),
    )
    for observation in observations:
        with pytest.raises(ValueError, match="lineage"):
            assess_screenshot_fidelity(observation, attempt=1)


def test_rejects_internally_inconsistent_identical_screenshot_evidence() -> None:
    observation = replace(
        _observation(),
        generated_sha256="a" * 64,
        pixel_mismatch_ratio=0.2,
    )
    with pytest.raises(ValueError, match="conflict"):
        assess_screenshot_fidelity(observation, attempt=1)


def test_rejects_invalid_ratios_and_negative_defect_counts() -> None:
    with pytest.raises(ValueError, match="ratios"):
        assess_screenshot_fidelity(replace(_observation(), pixel_mismatch_ratio=1.1), attempt=1)
    with pytest.raises(ValueError, match="cannot be negative"):
        assess_screenshot_fidelity(replace(_observation(), clipped_elements=-1), attempt=1)


def test_fixed_thresholds_cannot_be_weakened_by_retry() -> None:
    observation = replace(_observation(), layout_mismatch_ratio=0.031)
    first = assess_screenshot_fidelity(observation, attempt=1)
    second = assess_screenshot_fidelity(observation, attempt=2)
    third = assess_screenshot_fidelity(observation, attempt=3)
    assert first.status == "REVISE"
    assert second.status == "REVISE"
    assert third.status == "FAIL"
    assert all(
        any(finding.category == "layout-fidelity" for finding in assessment.findings)
        for assessment in (first, second, third)
    )
