"""Deterministic screenshot-fidelity assessment for the canonical Web Factory.

This module is an evidence/repair-planning layer only. It does not capture screenshots,
mutate generated source, execute browsers, deploy, publish, or grant runtime authority.
Repair execution must remain in the incumbent governed Web Factory path.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_ALLOWED_VIEWPORTS = frozenset({320, 360, 390, 412, 430, 768, 1024, 1440})
_MAX_REPAIR_ATTEMPTS = 3

# Fixed acceptance budgets. Callers cannot lower these thresholds between attempts.
_MAX_PIXEL_MISMATCH_RATIO = 0.08
_MAX_LAYOUT_MISMATCH_RATIO = 0.03
_MAX_TEXT_MISMATCH_RATIO = 0.02


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
    status: str
    attempt: int
    observation: ScreenshotFidelityObservation
    findings: tuple[ScreenshotFidelityFinding, ...]
    remaining_attempts: int

    @property
    def repair_allowed(self) -> bool:
        return self.status == "REVISE" and self.remaining_attempts > 0


def assess_screenshot_fidelity(
    observation: ScreenshotFidelityObservation,
    *,
    attempt: int,
) -> ScreenshotFidelityAssessment:
    """Evaluate one immutable reference/generated screenshot pair fail-closed.

    The bounded loop has at most three assessment attempts. Thresholds are module-owned
    constants so retrying cannot silently weaken acceptance. Returned repair scopes are
    descriptive only; they do not authorize filesystem or runtime mutation.
    """
    _validate_observation(observation)
    if attempt < 1 or attempt > _MAX_REPAIR_ATTEMPTS:
        raise ValueError("screenshot fidelity attempt must be between 1 and 3")

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
        # Byte-identical reference/generated images are valid, but the comparison metrics
        # must also report an exact match or the evidence is internally inconsistent.
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
    "ScreenshotFidelityAssessment",
    "ScreenshotFidelityFinding",
    "ScreenshotFidelityObservation",
    "assess_screenshot_fidelity",
]
