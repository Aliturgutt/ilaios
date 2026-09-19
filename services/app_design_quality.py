"""ILAIOS-native, dependency-free app design quality evaluation."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

BLOCKING_SEVERITIES = frozenset({"critical", "major", "p2"})
SUPPORTED_PLATFORMS = frozenset({"windows", "android", "ios"})
SUPPORTED_FORM_FACTORS = frozenset({"compact", "tablet", "wide"})


@dataclass(frozen=True, slots=True)
class AppDesignObservation:
    surface: str
    platform: str
    form_factor: str
    width: int
    height: int
    clipped_elements: int = 0
    overlapping_elements: int = 0
    missing_semantics: int = 0
    focus_traversal_failures: int = 0
    missing_focus_indicators: int = 0
    missing_interaction_states: int = 0
    undersized_touch_targets: int = 0
    contrast_failures: int = 0
    inconsistent_components: int = 0
    navigation_adaptation_failures: int = 0
    dialog_or_sheet_failures: int = 0
    unexplained_decorative_patterns: int = 0
    safe_area_failures: int = 0
    back_navigation_failures: int = 0
    missing_accessible_labels: int = 0
    touch_spacing_failures: int = 0
    text_scaling_failures: int = 0
    deep_link_failures: int = 0
    chart_accessibility_failures: int = 0
    reduced_motion_supported: bool = True

    @property
    def coverage_key(self) -> str:
        return f"{self.platform}:{self.form_factor}"


@dataclass(frozen=True, slots=True)
class AppDesignFinding:
    evaluator_id: str
    version: str
    surface: str
    platform: str
    form_factor: str
    category: str
    severity: str
    finding: str
    evidence: Mapping[str, object]
    recommendation: str
    confidence: float
    status: str = "FAIL"


@dataclass(frozen=True, slots=True)
class AppDesignAssessment:
    evaluator_id: str
    version: str
    status: str
    findings: tuple[AppDesignFinding, ...]
    covered_surfaces: tuple[str, ...]
    required_surfaces: tuple[str, ...]

    @property
    def blocking_findings(self) -> tuple[AppDesignFinding, ...]:
        return tuple(
            finding
            for finding in self.findings
            if finding.severity in BLOCKING_SEVERITIES
        )


class NativeAppDesignQualityEvaluator:
    """Apply deterministic native-app gates to bounded inspection evidence."""

    evaluator_id = "design.app-final-polish"
    version = "1.1.0"

    def evaluate(
        self,
        observations: Iterable[AppDesignObservation],
        *,
        required_surfaces: Iterable[str],
    ) -> AppDesignAssessment:
        rows = tuple(observations)
        required = tuple(sorted(set(required_surfaces)))
        if not rows:
            raise ValueError("at least one app design observation is required")
        if not required:
            raise ValueError("at least one required app surface is required")
        findings: list[AppDesignFinding] = []
        for row in rows:
            self._validate(row)
            findings.extend(self._findings(row))

        covered = tuple(sorted({row.coverage_key for row in rows}))
        missing = tuple(surface for surface in required if surface not in covered)
        if missing:
            findings.append(
                self._finding(
                    rows[0],
                    "design.app-coverage",
                    "major",
                    "Required native app evidence is incomplete.",
                    {"missing_surfaces": missing},
                    "Capture every declared platform and form-factor surface.",
                    1.0,
                )
            )
        status = (
            "FAIL"
            if any(
                finding.severity in BLOCKING_SEVERITIES for finding in findings
            )
            else "PASS"
        )
        return AppDesignAssessment(
            self.evaluator_id,
            self.version,
            status,
            tuple(findings),
            covered,
            required,
        )

    @staticmethod
    def _validate(row: AppDesignObservation) -> None:
        if not row.surface or row.surface != row.surface.strip():
            raise ValueError("surface must be non-blank and trimmed")
        if row.platform not in SUPPORTED_PLATFORMS:
            raise ValueError("platform is unsupported")
        if row.form_factor not in SUPPORTED_FORM_FACTORS:
            raise ValueError("form_factor is unsupported")
        if row.width < 240 or row.height < 320:
            raise ValueError("app viewport is invalid")
        for name in (
            "clipped_elements",
            "overlapping_elements",
            "missing_semantics",
            "focus_traversal_failures",
            "missing_focus_indicators",
            "missing_interaction_states",
            "undersized_touch_targets",
            "contrast_failures",
            "inconsistent_components",
            "navigation_adaptation_failures",
            "dialog_or_sheet_failures",
            "unexplained_decorative_patterns",
            "safe_area_failures",
            "back_navigation_failures",
            "missing_accessible_labels",
            "touch_spacing_failures",
            "text_scaling_failures",
            "deep_link_failures",
            "chart_accessibility_failures",
        ):
            if getattr(row, name) < 0:
                raise ValueError(f"{name} cannot be negative")

    def _findings(self, row: AppDesignObservation) -> list[AppDesignFinding]:
        rules = (
            (
                "clipped_elements",
                "design.app-layout",
                "major",
                "Visible content is clipped.",
                "Repair native layout constraints.",
            ),
            (
                "overlapping_elements",
                "design.app-layout",
                "major",
                "Visible elements overlap.",
                "Repair layout constraints and spacing.",
            ),
            (
                "missing_semantics",
                "design.app-accessibility",
                "p2",
                "Interactive content lacks semantics.",
                "Add native semantic roles and state.",
            ),
            (
                "focus_traversal_failures",
                "design.app-accessibility",
                "major",
                "Focus traversal fails.",
                "Restore logical keyboard or assistive focus order.",
            ),
            (
                "missing_focus_indicators",
                "design.app-interaction",
                "p2",
                "Keyboard focus is not visible.",
                "Provide a visible native focus treatment.",
            ),
            (
                "missing_interaction_states",
                "design.app-interaction",
                "p2",
                "A control lacks required interaction states.",
                "Provide applicable hover, pressed, selected, disabled, loading, and error states.",
            ),
            (
                "undersized_touch_targets",
                "design.app-interaction",
                "p2",
                "Touch targets are undersized.",
                "Increase target size or separation.",
            ),
            (
                "contrast_failures",
                "design.app-visual",
                "major",
                "Text or control contrast fails.",
                "Correct foreground and background tokens.",
            ),
            (
                "inconsistent_components",
                "design.app-consistency",
                "p2",
                "Component-system inconsistency detected.",
                "Use the established native component and token system.",
            ),
            (
                "navigation_adaptation_failures",
                "design.app-navigation",
                "major",
                "Navigation does not adapt to the form factor.",
                "Use an intentional compact, tablet, or wide navigation pattern.",
            ),
            (
                "dialog_or_sheet_failures",
                "design.app-interaction",
                "major",
                "Dialog or sheet behavior fails.",
                "Restore focus containment, dismissal, and safe responsive sizing.",
            ),
            (
                "safe_area_failures",
                "design.app-layout",
                "major",
                "Content violates platform safe areas or system insets.",
                "Respect system bars, cutouts, window chrome, and gesture insets.",
            ),
            (
                "back_navigation_failures",
                "design.app-navigation",
                "major",
                "Back navigation is unpredictable or broken.",
                "Restore platform-consistent back behavior and state restoration.",
            ),
            (
                "missing_accessible_labels",
                "design.app-accessibility",
                "major",
                "Interactive controls lack accessible names.",
                "Provide native accessibility labels without visual-only dependence.",
            ),
            (
                "touch_spacing_failures",
                "design.app-interaction",
                "p2",
                "Adjacent touch targets are insufficiently separated.",
                "Increase spacing or target bounds to prevent accidental activation.",
            ),
            (
                "text_scaling_failures",
                "design.app-accessibility",
                "p2",
                "Text scaling or dynamic type breaks the interface.",
                "Support platform text scaling without clipping or information loss.",
            ),
            (
                "deep_link_failures",
                "design.app-navigation",
                "p2",
                "Declared deep-link navigation does not preserve route intent.",
                "Repair route mapping and state restoration for declared deep links.",
            ),
            (
                "chart_accessibility_failures",
                "design.app-data-visualization",
                "p2",
                "Data visualization lacks accessible labels or non-color encoding.",
                "Provide accessible labels, legends, and redundant data encoding.",
            ),
        )
        findings = [
            self._finding(
                row,
                category,
                severity,
                message,
                {field: getattr(row, field)},
                recommendation,
                1.0,
            )
            for field, category, severity, message, recommendation in rules
            if getattr(row, field)
        ]
        if not row.reduced_motion_supported:
            findings.append(
                self._finding(
                    row,
                    "design.app-motion",
                    "p2",
                    "Reduced-motion behavior is missing.",
                    {"reduced_motion_supported": False},
                    "Honor the platform reduced-motion preference.",
                    1.0,
                )
            )
        if row.unexplained_decorative_patterns >= 3:
            findings.append(
                self._finding(
                    row,
                    "design.app-anti-generic-ai",
                    "minor",
                    "Repeated decorative patterns need contextual review.",
                    {
                        "unexplained_decorative_patterns": (
                            row.unexplained_decorative_patterns
                        )
                    },
                    "Keep decoration only when it supports hierarchy, brand, or comprehension.",
                    0.75,
                )
            )
        return findings

    def _finding(
        self,
        row: AppDesignObservation,
        category: str,
        severity: str,
        finding: str,
        evidence: Mapping[str, object],
        recommendation: str,
        confidence: float,
    ) -> AppDesignFinding:
        return AppDesignFinding(
            self.evaluator_id,
            self.version,
            row.surface,
            row.platform,
            row.form_factor,
            category,
            severity,
            finding,
            evidence,
            recommendation,
            confidence,
        )
