"""ILAIOS-native, dependency-free website design quality evaluation."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

REQUIRED_VIEWPORTS = (320, 360, 390, 412, 430, 768, 1024, 1440)
BLOCKING_SEVERITIES = frozenset({"critical", "major", "p2"})


@dataclass(frozen=True, slots=True)
class DesignObservation:
    route: str
    locale: str
    viewport: int
    horizontal_overflow: int = 0
    clipped_elements: int = 0
    overlapping_elements: int = 0
    missing_focus_indicators: int = 0
    undersized_touch_targets: int = 0
    contrast_failures: int = 0
    unreadable_text_blocks: int = 0
    inconsistent_components: int = 0
    unexplained_decorative_patterns: int = 0
    reduced_motion_supported: bool = True


@dataclass(frozen=True, slots=True)
class DesignFinding:
    evaluator_id: str
    version: str
    route: str
    viewport: int
    category: str
    severity: str
    finding: str
    evidence: Mapping[str, object]
    recommendation: str
    confidence: float
    status: str = "FAIL"


@dataclass(frozen=True, slots=True)
class DesignAssessment:
    evaluator_id: str
    version: str
    status: str
    findings: tuple[DesignFinding, ...]
    covered_viewports: tuple[int, ...]
    covered_locales: tuple[str, ...]

    @property
    def blocking_findings(self) -> tuple[DesignFinding, ...]:
        return tuple(f for f in self.findings if f.severity in BLOCKING_SEVERITIES)


class NativeDesignQualityEvaluator:
    """Apply bounded deterministic gates; leave aesthetic judgment as evidence input."""

    evaluator_id = "design.final-polish"
    version = "1.0.0"

    def evaluate(self, observations: Iterable[DesignObservation]) -> DesignAssessment:
        rows = tuple(observations)
        if not rows:
            raise ValueError("at least one design observation is required")
        findings: list[DesignFinding] = []
        for row in rows:
            self._validate(row)
            findings.extend(self._findings(row))

        viewports = tuple(sorted({row.viewport for row in rows}))
        locales = tuple(sorted({row.locale for row in rows}))
        missing = tuple(width for width in REQUIRED_VIEWPORTS if width not in viewports)
        if missing:
            findings.append(self._finding(
                rows[0], "design.responsive-quality", "major",
                "Required responsive evidence is incomplete.",
                {"missing_viewports": missing},
                "Capture and evaluate every required viewport.", 1.0,
            ))
        if not {"en", "tr"}.issubset(locales):
            findings.append(self._finding(
                rows[0], "design.localization-parity", "major",
                "EN/TR parity evidence is incomplete.",
                {"covered_locales": locales},
                "Evaluate matching English and Turkish surfaces.", 1.0,
            ))
        status = "FAIL" if any(f.severity in BLOCKING_SEVERITIES for f in findings) else "PASS"
        return DesignAssessment(self.evaluator_id, self.version, status, tuple(findings), viewports, locales)

    @staticmethod
    def _validate(row: DesignObservation) -> None:
        if row.locale not in {"en", "tr"}:
            raise ValueError("locale must be en or tr")
        if not row.route.startswith("/") or row.viewport < 240:
            raise ValueError("route or viewport is invalid")
        for name in (
            "horizontal_overflow", "clipped_elements", "overlapping_elements",
            "missing_focus_indicators", "undersized_touch_targets", "contrast_failures",
            "unreadable_text_blocks", "inconsistent_components",
            "unexplained_decorative_patterns",
        ):
            if getattr(row, name) < 0:
                raise ValueError(f"{name} cannot be negative")

    def _findings(self, row: DesignObservation) -> list[DesignFinding]:
        rules = (
            ("horizontal_overflow", "design.responsive-quality", "major", "Horizontal overflow detected.", "Remove the overflowing layout constraint."),
            ("clipped_elements", "design.responsive-quality", "major", "Visible content is clipped.", "Restore complete content visibility at this viewport."),
            ("overlapping_elements", "design.visual-quality", "major", "Visible elements overlap.", "Repair layout constraints and spacing."),
            ("missing_focus_indicators", "design.interaction-quality", "p2", "Keyboard focus is not visible.", "Provide a visible focus treatment."),
            ("undersized_touch_targets", "design.interaction-quality", "p2", "Touch targets are undersized.", "Increase interactive target dimensions or spacing."),
            ("contrast_failures", "design.typography-quality", "major", "Text or control contrast fails.", "Adjust foreground/background tokens to meet contrast requirements."),
            ("unreadable_text_blocks", "design.technical-content-quality", "p2", "Technical content is not comfortably readable.", "Improve line length, scale, or content chunking."),
            ("inconsistent_components", "design.component-consistency", "p2", "Component-system inconsistency detected.", "Use the established component tokens and states."),
        )
        findings = [
            self._finding(row, category, severity, message, {field: getattr(row, field)}, recommendation, 1.0)
            for field, category, severity, message, recommendation in rules
            if getattr(row, field)
        ]
        if not row.reduced_motion_supported:
            findings.append(self._finding(
                row, "design.motion-quality", "p2", "Reduced-motion behavior is missing.",
                {"reduced_motion_supported": False}, "Honor prefers-reduced-motion.", 1.0,
            ))
        if row.unexplained_decorative_patterns >= 3:
            findings.append(self._finding(
                row, "design.anti-generic-ai", "minor",
                "Repeated decorative patterns need contextual design review.",
                {"unexplained_decorative_patterns": row.unexplained_decorative_patterns},
                "Keep only decoration that supports hierarchy, brand, or comprehension.", .75,
            ))
        return findings

    def _finding(
        self, row: DesignObservation, category: str, severity: str, finding: str,
        evidence: Mapping[str, object], recommendation: str, confidence: float,
    ) -> DesignFinding:
        return DesignFinding(
            self.evaluator_id, self.version, row.route, row.viewport, category,
            severity, finding, evidence, recommendation, confidence,
        )
