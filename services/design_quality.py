"""ILAIOS-native, dependency-free website design strategy and quality evaluation."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

REQUIRED_VIEWPORTS = (320, 360, 390, 412, 430, 768, 1024, 1440)
BLOCKING_SEVERITIES = frozenset({"critical", "major", "p2"})
COMPOSITIONS = frozenset(
    {
        "editorial-split",
        "technical-flow",
        "layered-architecture",
        "narrative-scroll",
        "product-showcase",
        "minimal-institutional",
        "visual-portfolio",
        "structured-comparison",
        "process-pipeline",
        "evidence-trust",
        "documentation-led",
        "media-led",
    }
)


@dataclass(frozen=True, slots=True)
class DesignContext:
    business_category: str
    audience: str
    primary_goal: str
    conversion_objective: str
    brand_personality: tuple[str, ...]
    content_volume: str
    product_complexity: str
    trust_requirement: str
    visual_asset_availability: str
    information_density: str
    locale: str = "en"
    device_priority: str = "responsive"


@dataclass(frozen=True, slots=True)
class DesignStrategy:
    primary_composition: str
    secondary_compositions: tuple[str, ...]
    type_behavior: str
    spacing_behavior: str
    surface_behavior: str
    imagery_behavior: str
    cta_hierarchy: str
    diagram_usage: str
    motion_intensity: str
    interaction_density: str
    scroll_behavior: str
    showcase_behavior: str
    motion_accessibility: str
    navigation_behavior: str
    mobile_transformation: str


@dataclass(frozen=True, slots=True)
class CompositionFingerprint:
    hero_composition: str
    section_sequence: tuple[str, ...]
    content_density: str
    grid_patterns: tuple[str, ...]
    accent_distribution: str


class NativeDesignStrategyEngine:
    """Create inspectable context-derived strategy; never use random variation."""

    def plan(self, context: DesignContext) -> DesignStrategy:
        if context.locale not in {"en", "tr"}:
            raise ValueError("design context locale must be en or tr")
        values = (
            context.business_category,
            context.audience,
            context.primary_goal,
            context.conversion_objective,
            context.content_volume,
            context.product_complexity,
            context.trust_requirement,
            context.visual_asset_availability,
            context.information_density,
        )
        if any(not value.strip() for value in values):
            raise ValueError("design context fields must be non-empty")
        category = context.business_category.strip().lower()
        dense = (
            context.information_density in {"high", "dense"}
            or context.content_volume == "high"
        )
        trusted = context.trust_requirement in {"high", "critical"}
        visual = context.visual_asset_availability in {"high", "rich"}
        if category in {
            "developer platform",
            "security",
            "infrastructure",
            "enterprise software",
        }:
            primary, secondary = (
                ("technical-flow" if dense else "layered-architecture"),
                ("evidence-trust", "documentation-led"),
            )
        elif category in {"architecture studio", "media brand", "restaurant"} and visual:
            primary, secondary = (
                "visual-portfolio" if category == "architecture studio" else "media-led",
                ("editorial-split", "narrative-scroll"),
            )
        elif category in {"law firm", "professional services"} or trusted:
            primary, secondary = (
                "minimal-institutional",
                ("evidence-trust", "structured-comparison"),
            )
        elif category in {"saas", "software"}:
            primary, secondary = (
                "product-showcase",
                ("technical-flow", "structured-comparison"),
            )
        else:
            primary, secondary = (
                "editorial-split",
                ("narrative-scroll", "structured-comparison"),
            )
        if trusted:
            motion_intensity = "low"
            interaction_density = "low"
            scroll_behavior = "standard"
            showcase_behavior = "static-evidence"
        elif visual:
            motion_intensity = "expressive"
            interaction_density = "high"
            scroll_behavior = "narrative-linked"
            showcase_behavior = "asset-led-interactive"
        elif category in {"developer platform", "saas", "software", "enterprise software"}:
            motion_intensity = "restrained"
            interaction_density = "moderate"
            scroll_behavior = "section-linked"
            showcase_behavior = "system-or-product-interactive"
        else:
            motion_intensity = "restrained"
            interaction_density = "moderate"
            scroll_behavior = "section-linked"
            showcase_behavior = "contextual-interactive"

        return DesignStrategy(
            primary,
            secondary,
            "dense-technical" if dense else "editorial-readable",
            "compact-rhythm" if dense else "variable-narrative-rhythm",
            "selective-surfaces" if trusted else "open-layout-first",
            "asset-led" if visual else "diagram-and-type-led",
            "single-primary-with-contextual-secondary",
            "high" if context.product_complexity in {"high", "complex"} else "contextual",
            motion_intensity,
            interaction_density,
            scroll_behavior,
            showcase_behavior,
            "reduced-motion-static-equivalent",
            "dense" if dense else "progressive-disclosure",
            "reorder-reduce-and-recompose",
        )

    def fingerprint(
        self, strategy: DesignStrategy, sections: tuple[str, ...]
    ) -> CompositionFingerprint:
        if strategy.primary_composition not in COMPOSITIONS:
            raise ValueError("unsupported composition")
        return CompositionFingerprint(
            strategy.primary_composition,
            sections,
            strategy.type_behavior,
            (strategy.primary_composition, *strategy.secondary_compositions),
            "hierarchy-led",
        )


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
    repeated_equal_card_groups: int = 0
    repeated_centered_sections: int = 0
    missing_alt_text: int = 0
    unlabeled_icon_controls: int = 0
    hover_only_interactions: int = 0
    form_label_failures: int = 0
    field_feedback_failures: int = 0
    layout_shift_failures: int = 0
    navigation_hierarchy_failures: int = 0
    chart_accessibility_failures: int = 0
    input_feedback_failures: int = 0
    gesture_tracking_failures: int = 0
    non_interruptible_motion_failures: int = 0
    velocity_handoff_failures: int = 0
    spatial_transition_failures: int = 0
    scroll_jank_failures: int = 0
    pointer_tracking_failures: int = 0
    motion_budget_failures: int = 0
    showcase_fallback_failures: int = 0
    text_scaling_failures: int = 0
    reduced_motion_supported: bool = True
    reduced_transparency_supported: bool = True
    increased_contrast_supported: bool = True


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
        return tuple(
            finding
            for finding in self.findings
            if finding.severity in BLOCKING_SEVERITIES
        )


class NativeDesignQualityEvaluator:
    evaluator_id = "design.final-polish"
    version = "1.4.0"

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
            findings.append(
                self._finding(
                    rows[0],
                    "design.responsive-quality",
                    "major",
                    "Required responsive evidence is incomplete.",
                    {"missing_viewports": missing},
                    "Capture and evaluate every required viewport.",
                    1.0,
                )
            )
        if not {"en", "tr"}.issubset(locales):
            findings.append(
                self._finding(
                    rows[0],
                    "design.localization-parity",
                    "major",
                    "EN/TR parity evidence is incomplete.",
                    {"covered_locales": locales},
                    "Evaluate matching English and Turkish surfaces.",
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
        return DesignAssessment(
            self.evaluator_id,
            self.version,
            status,
            tuple(findings),
            viewports,
            locales,
        )

    @staticmethod
    def _validate(row: DesignObservation) -> None:
        if (
            row.locale not in {"en", "tr"}
            or not row.route.startswith("/")
            or row.viewport < 240
        ):
            raise ValueError("route, locale or viewport is invalid")
        fields = (
            "horizontal_overflow",
            "clipped_elements",
            "overlapping_elements",
            "missing_focus_indicators",
            "undersized_touch_targets",
            "contrast_failures",
            "unreadable_text_blocks",
            "inconsistent_components",
            "unexplained_decorative_patterns",
            "repeated_equal_card_groups",
            "repeated_centered_sections",
            "missing_alt_text",
            "unlabeled_icon_controls",
            "hover_only_interactions",
            "form_label_failures",
            "field_feedback_failures",
            "layout_shift_failures",
            "navigation_hierarchy_failures",
            "chart_accessibility_failures",
            "input_feedback_failures",
            "gesture_tracking_failures",
            "non_interruptible_motion_failures",
            "velocity_handoff_failures",
            "spatial_transition_failures",
            "scroll_jank_failures",
            "pointer_tracking_failures",
            "motion_budget_failures",
            "showcase_fallback_failures",
            "text_scaling_failures",
        )
        for name in fields:
            if getattr(row, name) < 0:
                raise ValueError(f"{name} cannot be negative")

    def _findings(self, row: DesignObservation) -> list[DesignFinding]:
        rules = (
            (
                "horizontal_overflow",
                "design.responsive-quality",
                "major",
                "Horizontal overflow detected.",
                "Repair responsive constraints without hiding required content.",
            ),
            (
                "clipped_elements",
                "design.responsive-quality",
                "major",
                "Clipped elements detected.",
                "Repair measured layout constraints.",
            ),
            (
                "overlapping_elements",
                "design.visual-quality",
                "major",
                "Overlapping elements detected.",
                "Repair hierarchy, sizing, or spacing at the root cause.",
            ),
            (
                "missing_focus_indicators",
                "design.interaction-quality",
                "p2",
                "Visible keyboard focus is missing.",
                "Restore visible focus treatment.",
            ),
            (
                "undersized_touch_targets",
                "design.interaction-quality",
                "p2",
                "Undersized touch targets detected.",
                "Increase target size or separation.",
            ),
            (
                "contrast_failures",
                "design.typography-quality",
                "major",
                "Contrast failures detected.",
                "Correct semantic foreground/background tokens.",
            ),
            (
                "unreadable_text_blocks",
                "design.technical-content-quality",
                "p2",
                "Unreadable text blocks detected.",
                "Repair text scale, line length, hierarchy, or density.",
            ),
            (
                "inconsistent_components",
                "design.component-consistency",
                "p2",
                "Component inconsistency detected.",
                "Use the established component and token language.",
            ),
            (
                "missing_alt_text",
                "design.accessibility",
                "major",
                "Meaningful visual content lacks text alternatives.",
                "Provide meaningful alternatives or mark pure decoration as such.",
            ),
            (
                "unlabeled_icon_controls",
                "design.accessibility",
                "major",
                "Icon-only controls lack accessible names.",
                "Provide programmatic labels without changing visual hierarchy.",
            ),
            (
                "hover_only_interactions",
                "design.interaction-quality",
                "p2",
                "Interaction depends on hover alone.",
                "Provide keyboard, touch, and persistent affordance equivalents.",
            ),
            (
                "form_label_failures",
                "design.form-feedback",
                "major",
                "Form controls lack persistent labels.",
                "Use visible labels associated with the corresponding control.",
            ),
            (
                "field_feedback_failures",
                "design.form-feedback",
                "p2",
                "Validation or error feedback is detached from its field.",
                "Place actionable feedback at the source and manage focus when needed.",
            ),
            (
                "layout_shift_failures",
                "design.performance-quality",
                "p2",
                "Visible layout instability was observed.",
                "Reserve space and remove avoidable layout-shifting behavior.",
            ),
            (
                "navigation_hierarchy_failures",
                "design.navigation-quality",
                "major",
                "Navigation hierarchy or back behavior is inconsistent.",
                "Restore predictable hierarchy, state, and route behavior.",
            ),
            (
                "chart_accessibility_failures",
                "design.data-visualization",
                "p2",
                "Data visualization relies on inaccessible encoding.",
                "Provide labels, legends, non-color encoding, and accessible data context.",
            ),
            (
                "input_feedback_failures",
                "design.interaction-response",
                "p2",
                "Interactive input feedback is delayed or discontinuous.",
                "Respond at interaction start and keep feedback continuous while the input is active.",
            ),
            (
                "gesture_tracking_failures",
                "design.gesture-continuity",
                "p2",
                "Gesture-driven content does not track the active input continuously.",
                "Keep direct-manipulation state synchronized with pointer or touch movement.",
            ),
            (
                "non_interruptible_motion_failures",
                "design.motion-quality",
                "p2",
                "User-driven motion cannot be safely interrupted or redirected.",
                "Retarget from the current presented state without locking interaction during motion.",
            ),
            (
                "velocity_handoff_failures",
                "design.motion-quality",
                "p2",
                "Gesture release introduces a visible motion discontinuity.",
                "Preserve measured interaction momentum when transitioning to settled motion.",
            ),
            (
                "spatial_transition_failures",
                "design.motion-quality",
                "p2",
                "Enter, exit, or reversible transitions break spatial continuity.",
                "Keep reversible transitions anchored to the same spatial source and path.",
            ),
            (
                "scroll_jank_failures",
                "design.motion-performance",
                "p2",
                "Scroll-linked motion introduces visible jank or blocking work.",
                "Move scroll work to bounded animation-frame updates and compositor-friendly properties.",
            ),
            (
                "pointer_tracking_failures",
                "design.interaction-quality",
                "p2",
                "Pointer-driven presentation loses continuity or exceeds its bounded surface.",
                "Keep pointer effects local, interruptible, and synchronized with the active surface.",
            ),
            (
                "motion_budget_failures",
                "design.motion-performance",
                "p2",
                "Motion exceeds the accepted runtime performance budget.",
                "Reduce continuous work, animated area, or dependency cost before acceptance.",
            ),
            (
                "showcase_fallback_failures",
                "design.motion-accessibility",
                "major",
                "Interactive showcase lacks an equivalent static or reduced-motion fallback.",
                "Provide a complete non-motion representation with the same information and actions.",
            ),
            (
                "text_scaling_failures",
                "design.typography-quality",
                "p2",
                "Text scaling breaks hierarchy, legibility, or layout.",
                "Use scale-aware typography and spacing that survives user text-size changes.",
            ),
        )
        out = [
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
            out.append(
                self._finding(
                    row,
                    "design.motion-quality",
                    "p2",
                    "Reduced-motion behavior is missing.",
                    {"reduced_motion_supported": False},
                    "Honor prefers-reduced-motion.",
                    1.0,
                )
            )
        if not row.reduced_transparency_supported:
            out.append(
                self._finding(
                    row,
                    "design.accessibility",
                    "p2",
                    "A required reduced-transparency fallback is missing.",
                    {"reduced_transparency_supported": False},
                    "When translucent surfaces are used, provide a legible reduced-transparency fallback.",
                    1.0,
                )
            )
        if not row.increased_contrast_supported:
            out.append(
                self._finding(
                    row,
                    "design.accessibility",
                    "p2",
                    "A required increased-contrast fallback is missing.",
                    {"increased_contrast_supported": False},
                    "Provide higher-contrast treatment where the platform requests increased contrast.",
                    1.0,
                )
            )
        if row.unexplained_decorative_patterns >= 3:
            out.append(
                self._finding(
                    row,
                    "design.anti-generic-ai",
                    "minor",
                    "Repeated decorative patterns need contextual review.",
                    {"count": row.unexplained_decorative_patterns},
                    "Keep only purposeful decoration.",
                    0.75,
                )
            )
        if row.repeated_equal_card_groups >= 3 and row.repeated_centered_sections >= 2:
            out.append(
                self._finding(
                    row,
                    "design.anti-generic-ai",
                    "p2",
                    "Repeated equal-card and centered-section structure is generic.",
                    {
                        "card_groups": row.repeated_equal_card_groups,
                        "centered_sections": row.repeated_centered_sections,
                    },
                    "Use content-specific compositions.",
                    0.95,
                )
            )
        return out

    def _finding(
        self,
        row: DesignObservation,
        category: str,
        severity: str,
        finding: str,
        evidence: Mapping[str, object],
        recommendation: str,
        confidence: float,
    ) -> DesignFinding:
        return DesignFinding(
            self.evaluator_id,
            self.version,
            row.route,
            row.viewport,
            category,
            severity,
            finding,
            evidence,
            recommendation,
            confidence,
        )
