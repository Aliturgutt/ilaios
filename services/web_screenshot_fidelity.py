"""Deterministic screenshot-fidelity assessment for the canonical Web Factory.

This module is an evidence/repair-planning and scoring layer only. It does not capture
screenshots, mutate generated source, execute browsers, deploy, publish, or grant runtime
authority. Visual acceptance reuses the incumbent NativeDesignQualityEvaluator.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Literal

from services.design_quality import (
    DesignAssessment,
    DesignObservation,
    NativeDesignQualityEvaluator,
)

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_ALLOWED_VIEWPORTS = frozenset({320, 360, 390, 412, 430, 768, 1024, 1440})
_MAX_REPAIR_ATTEMPTS = 3

# Fixed fidelity budgets. Callers cannot lower these thresholds between attempts.
_MAX_PIXEL_MISMATCH_RATIO = 0.08
_MAX_LAYOUT_MISMATCH_RATIO = 0.03
_MAX_TEXT_MISMATCH_RATIO = 0.02

# Fixed professional visual-quality budgets from the Web Factory completion contract.
_MIN_CRITICAL_SCORE = 70
_MIN_OVERALL_SCORE = 80
_MIN_ACCESSIBILITY_SCORE = 85
_MIN_MOBILE_SCORE = 80

FidelityStatus = Literal["PASS", "REVISE", "FAIL"]
VisualQualityStatus = Literal["PASS", "REVISE", "DESIGN_QUALITY_FAILED"]


@dataclass(frozen=True, slots=True)
class ScreenshotFidelityObservation:
    route: str
    locale: str
    viewport: int
    reference_sha256: str
    generated_sha256: str
    source_sha256: str
    pixel_mismatch_ratio: float
    layout_mismatch_ratio: float
    text_mismatch_ratio: float
    horizontal_overflow_px: int = 0
    clipped_elements: int = 0
    overlapping_elements: int = 0


@dataclass(frozen=True, slots=True)
class ScreenshotFidelityFinding:
    category: str
    severity: str
    evidence: str
    repair_scope: str


@dataclass(frozen=True, slots=True)
class ScreenshotFidelityAssessment:
    status: FidelityStatus
    attempt: int
    observation: ScreenshotFidelityObservation
    findings: tuple[ScreenshotFidelityFinding, ...]
    remaining_attempts: int

    @property
    def repair_allowed(self) -> bool:
        return self.status == "REVISE" and self.remaining_attempts > 0


@dataclass(frozen=True, slots=True)
class VisualQualityScores:
    overall: int
    critical: int
    accessibility: int
    mobile: int


@dataclass(frozen=True, slots=True)
class VisualQualityGate:
    status: VisualQualityStatus
    attempt: int
    scores: VisualQualityScores
    assessment: DesignAssessment
    remaining_attempts: int
    thresholds: dict[str, int]

    @property
    def accepted(self) -> bool:
        return self.status == "PASS"


def assess_screenshot_fidelity(
    observation: ScreenshotFidelityObservation,
    *,
    attempt: int,
) -> ScreenshotFidelityAssessment:
    """Evaluate one immutable reference/generated screenshot pair fail-closed."""
    _validate_observation(observation)
    _validate_attempt(attempt)

    findings: list[ScreenshotFidelityFinding] = []
    if observation.horizontal_overflow_px > 0:
        findings.append(
            ScreenshotFidelityFinding(
                category="responsive-overflow",
                severity="major",
                evidence=f"horizontal_overflow_px={observation.horizontal_overflow_px}",
                repair_scope="layout-responsive",
            )
        )
    if observation.clipped_elements > 0:
        findings.append(
            ScreenshotFidelityFinding(
                category="clipping",
                severity="major",
                evidence=f"clipped_elements={observation.clipped_elements}",
                repair_scope="layout-geometry",
            )
        )
    if observation.overlapping_elements > 0:
        findings.append(
            ScreenshotFidelityFinding(
                category="overlap",
                severity="major",
                evidence=f"overlapping_elements={observation.overlapping_elements}",
                repair_scope="layout-geometry",
            )
        )
    if observation.layout_mismatch_ratio > _MAX_LAYOUT_MISMATCH_RATIO:
        findings.append(
            ScreenshotFidelityFinding(
                category="layout-fidelity",
                severity="major",
                evidence=f"layout_mismatch_ratio={observation.layout_mismatch_ratio:.6f}",
                repair_scope="layout-geometry",
            )
        )
    if observation.text_mismatch_ratio > _MAX_TEXT_MISMATCH_RATIO:
        findings.append(
            ScreenshotFidelityFinding(
                category="content-fidelity",
                severity="major",
                evidence=f"text_mismatch_ratio={observation.text_mismatch_ratio:.6f}",
                repair_scope="typography-content",
            )
        )
    if observation.pixel_mismatch_ratio > _MAX_PIXEL_MISMATCH_RATIO:
        findings.append(
            ScreenshotFidelityFinding(
                category="visual-fidelity",
                severity="major",
                evidence=f"pixel_mismatch_ratio={observation.pixel_mismatch_ratio:.6f}",
                repair_scope="visual-presentation",
            )
        )

    status: FidelityStatus
    if not findings:
        status = "PASS"
    elif attempt < _MAX_REPAIR_ATTEMPTS:
        status = "REVISE"
    else:
        status = "FAIL"

    return ScreenshotFidelityAssessment(
        status=status,
        attempt=attempt,
        observation=observation,
        findings=tuple(findings),
        remaining_attempts=_MAX_REPAIR_ATTEMPTS - attempt,
    )


def assess_visual_quality(
    observations: Iterable[DesignObservation],
    *,
    attempt: int,
) -> VisualQualityGate:
    """Score real rendered observations while retaining the canonical evaluator authority."""
    _validate_attempt(attempt)
    rows = tuple(observations)
    assessment = NativeDesignQualityEvaluator().evaluate(rows)
    scores = _score(rows)
    thresholds = {
        "critical": _MIN_CRITICAL_SCORE,
        "overall": _MIN_OVERALL_SCORE,
        "accessibility": _MIN_ACCESSIBILITY_SCORE,
        "mobile": _MIN_MOBILE_SCORE,
    }
    score_pass = (
        scores.critical >= _MIN_CRITICAL_SCORE
        and scores.overall >= _MIN_OVERALL_SCORE
        and scores.accessibility >= _MIN_ACCESSIBILITY_SCORE
        and scores.mobile >= _MIN_MOBILE_SCORE
    )
    passed = assessment.status == "PASS" and not assessment.blocking_findings and score_pass
    if passed:
        status: VisualQualityStatus = "PASS"
    elif attempt < _MAX_REPAIR_ATTEMPTS:
        status = "REVISE"
    else:
        status = "DESIGN_QUALITY_FAILED"
    return VisualQualityGate(
        status=status,
        attempt=attempt,
        scores=scores,
        assessment=assessment,
        remaining_attempts=_MAX_REPAIR_ATTEMPTS - attempt,
        thresholds=thresholds,
    )


def _score(rows: tuple[DesignObservation, ...]) -> VisualQualityScores:
    if not rows:
        raise ValueError("at least one design observation is required")
    critical_penalties: list[int] = []
    accessibility_penalties: list[int] = []
    mobile_penalties: list[int] = []
    overall_penalties: list[int] = []

    for row in rows:
        geometry = row.horizontal_overflow + row.clipped_elements + row.overlapping_elements
        critical_penalty = geometry * 16

        accessibility = (
            row.missing_focus_indicators
            + row.undersized_touch_targets
            + row.contrast_failures
            + row.missing_alt_text
            + row.unlabeled_icon_controls
            + row.hover_only_interactions
            + row.form_label_failures
            + row.field_feedback_failures
            + row.text_scaling_failures
        )
        accessibility_penalty = accessibility * 7
        if not row.reduced_motion_supported:
            accessibility_penalty += 8
        if not row.reduced_transparency_supported:
            accessibility_penalty += 4
        if not row.increased_contrast_supported:
            accessibility_penalty += 4

        professional = (
            row.giant_heading_failures
            + row.empty_visual_placeholders
            + row.excessive_whitespace_regions
            + row.repeated_layout_failures
            + row.cta_hierarchy_failures
            + row.turkish_layout_failures
            + row.mobile_hierarchy_failures
            + row.section_rhythm_failures
            + row.missing_brand_asset_failures
            + row.text_heavy_without_structure
        )
        overall_penalty = geometry * 10 + accessibility * 4 + professional * 6

        critical_penalties.append(critical_penalty)
        accessibility_penalties.append(accessibility_penalty)
        overall_penalties.append(overall_penalty)
        if row.viewport <= 430:
            mobile_penalties.append(
                geometry * 15
                + row.mobile_hierarchy_failures * 12
                + row.giant_heading_failures * 8
                + row.turkish_layout_failures * 8
                + row.undersized_touch_targets * 6
            )

    return VisualQualityScores(
        overall=max(0, 100 - max(overall_penalties)),
        critical=max(0, 100 - max(critical_penalties)),
        accessibility=max(0, 100 - max(accessibility_penalties)),
        mobile=max(0, 100 - max(mobile_penalties or [0])),
    )


def _validate_attempt(attempt: int) -> None:
    if attempt < 1 or attempt > _MAX_REPAIR_ATTEMPTS:
        raise ValueError("visual quality attempt must be between 1 and 3")


def _validate_observation(observation: ScreenshotFidelityObservation) -> None:
    if not observation.route.startswith("/") or "\x00" in observation.route:
        raise ValueError("screenshot fidelity route is invalid")
    if observation.locale not in {"en", "tr"}:
        raise ValueError("screenshot fidelity locale must be en or tr")
    if observation.viewport not in _ALLOWED_VIEWPORTS:
        raise ValueError("screenshot fidelity viewport is not canonical")

    digests = (
        observation.reference_sha256,
        observation.generated_sha256,
        observation.source_sha256,
    )
    if any(_SHA256_RE.fullmatch(value.casefold()) is None for value in digests):
        raise ValueError("screenshot fidelity SHA-256 lineage is malformed")
    if observation.reference_sha256.casefold() == observation.generated_sha256.casefold():
        if any(
            value != 0.0
            for value in (
                observation.pixel_mismatch_ratio,
                observation.layout_mismatch_ratio,
                observation.text_mismatch_ratio,
            )
        ):
            raise ValueError("identical screenshot digests conflict with mismatch evidence")

    ratios = (
        observation.pixel_mismatch_ratio,
        observation.layout_mismatch_ratio,
        observation.text_mismatch_ratio,
    )
    if any(value < 0.0 or value > 1.0 for value in ratios):
        raise ValueError("screenshot fidelity ratios must be between 0 and 1")
    counts = (
        observation.horizontal_overflow_px,
        observation.clipped_elements,
        observation.overlapping_elements,
    )
    if any(value < 0 for value in counts):
        raise ValueError("screenshot fidelity defect counts cannot be negative")


__all__ = [
    "FidelityStatus",
    "ScreenshotFidelityAssessment",
    "ScreenshotFidelityFinding",
    "ScreenshotFidelityObservation",
    "VisualQualityGate",
    "VisualQualityScores",
    "VisualQualityStatus",
    "assess_screenshot_fidelity",
    "assess_visual_quality",
]
