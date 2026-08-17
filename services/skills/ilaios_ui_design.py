"""ILAIOS-native UI design resolution skill.

This is a clean-room implementation informed by general design-system and
component-taxonomy concepts. It does not import, execute, or copy a third-party
skill at runtime. The output is a bounded machine-readable specification for a
coding agent and the existing ILAIOS design-quality gates.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Final

from services.runtime.skill_runtime import (
    NativeSkillRegistry,
    NativeSkillRuntime,
    SkillManifest,
    SkillMatch,
    SkillRequest,
    SkillRuntimeError,
)


@dataclass(frozen=True, slots=True)
class UIComponentPattern:
    component: str
    category: str
    aliases: tuple[str, ...]
    placement: str
    desktop_size: str
    compact_behavior: str
    interactions: tuple[str, ...]
    accessibility: tuple[str, ...]


PATTERNS: Final[tuple[UIComponentPattern, ...]] = (
    UIComponentPattern(
        "drawer",
        "overlay",
        (
            "drawer",
            "side panel",
            "settings panel",
            "yan panel",
            "sagdan ayarlar",
            "sagdan panel",
            "soldan panel",
            "kenardan acilan panel",
        ),
        "right",
        "420px",
        "full-screen sheet",
        ("escape-close", "close-button", "restore-trigger-focus"),
        ("focus-trap", "dialog-semantics", "keyboard-operable"),
    ),
    UIComponentPattern(
        "multi-select",
        "input",
        (
            "multi select",
            "multiselect",
            "multiple options",
            "birden fazla secenek",
            "coklu secim",
            "coklu secenek",
        ),
        "inline",
        "content-sized",
        "wrap selected values; avoid horizontal overflow",
        ("open-list", "toggle-option", "clear-selection"),
        ("labelled-control", "keyboard-navigation", "announced-selection-state"),
    ),
    UIComponentPattern(
        "avatar-group",
        "display",
        (
            "avatar group",
            "stacked avatars",
            "overlapping avatars",
            "ust uste avatar",
            "ust uste kucuk kullanici resimleri",
            "kullanici resimleri",
        ),
        "inline",
        "content-sized",
        "cap visible avatars and expose remaining count",
        ("show-overflow-count",),
        ("meaningful-alt-or-hidden-decoration", "non-color-only-identity"),
    ),
    UIComponentPattern(
        "text-truncation",
        "content",
        (
            "ellipsis",
            "text truncation",
            "truncate text",
            "uc nokta",
            "uzun metin",
            "metin kisalt",
        ),
        "inline",
        "container-bound",
        "truncate only where full text remains discoverable",
        ("reveal-full-value-on-demand",),
        ("full-value-accessible", "no-essential-information-loss"),
    ),
    UIComponentPattern(
        "dialog",
        "overlay",
        ("dialog", "modal", "onay penceresi", "acilir pencere"),
        "center",
        "min(560px, calc(100vw - 32px))",
        "near-full-width dialog with safe viewport margins",
        ("escape-close", "explicit-primary-secondary-actions", "restore-trigger-focus"),
        ("focus-trap", "dialog-semantics", "labelled-title", "keyboard-operable"),
    ),
    UIComponentPattern(
        "tabs",
        "navigation",
        ("tabs", "tab bar", "sekmeler", "sekme", "tab navigation"),
        "inline",
        "container-width",
        "scroll or transform navigation intentionally on compact surfaces",
        ("activate-tab", "preserve-selected-state"),
        ("tablist-semantics", "arrow-key-navigation", "visible-focus"),
    ),
    UIComponentPattern(
        "command-palette",
        "navigation",
        (
            "command palette",
            "command menu",
            "komut paleti",
            "hizli komut",
            "quick command",
        ),
        "center",
        "640px",
        "full-width overlay with bounded height",
        ("type-to-filter", "escape-close", "keyboard-select"),
        ("combobox-semantics", "active-option-announcement", "visible-focus"),
    ),
    UIComponentPattern(
        "data-table",
        "data-display",
        (
            "data table",
            "table",
            "tablo",
            "veri tablosu",
            "satir sutun",
        ),
        "inline",
        "container-width",
        "preserve critical columns; transform secondary data deliberately",
        ("sort-when-supported", "filter-when-supported", "row-action-affordance"),
        ("header-association", "keyboard-operable-actions", "non-color-only-status"),
    ),
    UIComponentPattern(
        "toast",
        "feedback",
        ("toast", "notification toast", "bildirim", "gecici bildirim"),
        "bottom-right",
        "360px",
        "respect safe areas and avoid covering primary controls",
        ("auto-dismiss-only-if-safe", "manual-dismiss-when-actionable"),
        ("live-region", "sufficient-reading-time", "keyboard-operable-action"),
    ),
    UIComponentPattern(
        "surface-layout",
        "layout",
        (
            "ui design",
            "interface design",
            "arayuz tasarimi",
            "ekran tasarimi",
            "dashboard design",
            "kontrol paneli",
            "desktop ui",
            "web ui",
        ),
        "page",
        "responsive container",
        "derive compact/tablet/wide composition instead of stacking blindly",
        ("preserve-hierarchy", "preserve-primary-action"),
        ("logical-focus-order", "landmarks-or-native-semantics", "visible-focus"),
    ),
)

_GENERIC_UI_SIGNALS: Final[tuple[str, ...]] = (
    "ui",
    "interface",
    "arayuz",
    "ekran",
    "component",
    "bilesen",
    "panel",
    "modal",
    "drawer",
    "tablo",
    "secenek",
    "avatar",
    "metin",
    "bildirim",
    "dashboard",
)

_ARTIFACT_PAYLOAD: Final[bytes] = json.dumps(
    {
        "skill_id": "ilaios.skill.ui-design",
        "version": "1.0.0",
        "schema": "ilaios.ui-spec.v1",
        "patterns": [pattern.component for pattern in PATTERNS],
        "runtime": "deterministic-clean-room",
    },
    sort_keys=True,
    separators=(",", ":"),
).encode("utf-8")


class ILAIOSUIDesignSkill:
    """Resolve UI intent into a deterministic implementation specification."""

    manifest = SkillManifest(
        skill_id="ilaios.skill.ui-design",
        version="1.0.0",
        description="Resolve product UI intent into governed component and quality specs.",
        authorities=frozenset(),
    )

    @property
    def artifact_content(self) -> bytes:
        return _ARTIFACT_PAYLOAD

    def match(self, normalized_prompt: str) -> SkillMatch:
        pattern, component_score, matched = _resolve_pattern(normalized_prompt)
        if pattern is not None:
            score = min(0.98, component_score)
            return SkillMatch(score, tuple(f"component:{item}" for item in matched))

        generic = tuple(
            signal for signal in _GENERIC_UI_SIGNALS if signal in normalized_prompt
        )
        if not generic:
            return SkillMatch(0.0, ())
        score = min(0.75, 0.44 + (0.08 * len(generic)))
        return SkillMatch(score, tuple(f"ui-signal:{item}" for item in generic))

    def execute(self, request: SkillRequest) -> dict[str, object]:
        pattern, score, matched = _resolve_pattern(request.normalized_prompt)
        if pattern is None:
            if any(signal in request.normalized_prompt for signal in _GENERIC_UI_SIGNALS):
                pattern = next(item for item in PATTERNS if item.component == "surface-layout")
                score = 0.55
                matched = ("generic-ui-intent",)
            else:
                raise SkillRuntimeError("ui-design skill could not resolve a UI intent")

        placement = _infer_placement(request.normalized_prompt, pattern.placement)
        design_profile = _infer_design_profile(request.normalized_prompt)
        product = request.context.get("product")
        brand_policy = (
            "ILAIOS-canonical-tokens"
            if isinstance(product, str) and product.casefold() == "ilaios"
            else "inherit-existing-project-brand"
        )

        return {
            "schema_version": "ilaios.ui-spec.v1",
            "status": "SPECIFIED",
            "intent": request.prompt,
            "component": pattern.component,
            "category": pattern.category,
            "confidence": round(score, 3),
            "evidence": list(matched),
            "design_read": design_profile,
            "layout": {
                "placement": placement,
                "desktop_size": pattern.desktop_size,
                "compact_behavior": pattern.compact_behavior,
            },
            "interaction": list(pattern.interactions),
            "accessibility": list(pattern.accessibility),
            "design_system": {
                "policy": "reuse-existing-component-system-first",
                "brand_policy": brand_policy,
                "dependency_rule": "inspect-project-before-importing-any-ui-package",
                "single_system_rule": True,
            },
            "quality_gates": [
                "no-clipping-or-overlap",
                "visible-focus",
                "required-interaction-states",
                "keyboard-operable",
                "reduced-motion-when-motion-exists",
                "intentional-compact-wide-adaptation",
                "no-unexplained-generic-ai-decoration",
            ],
            "codegen_hints": [
                "treat-this-spec-as-constraints-not-copyable-markup",
                "use-existing-project-tokens-and-primitives-before-new-dependencies",
                "do-not-invent-product-claims-or-interactions",
                "validate-generated-surface-with-existing-ILAIOS-design-quality-gates",
            ],
        }


def build_default_skill_runtime() -> NativeSkillRuntime:
    """Build the default executable native skill runtime."""
    registry = NativeSkillRegistry()
    registry.register(ILAIOSUIDesignSkill())
    return NativeSkillRuntime(registry)


def _resolve_pattern(
    normalized_prompt: str,
) -> tuple[UIComponentPattern | None, float, tuple[str, ...]]:
    best_pattern: UIComponentPattern | None = None
    best_score = 0.0
    best_matches: tuple[str, ...] = ()
    for pattern in PATTERNS:
        matches = tuple(alias for alias in pattern.aliases if alias in normalized_prompt)
        if not matches:
            continue
        longest = max(len(alias.split()) for alias in matches)
        score = min(0.98, 0.68 + (0.07 * min(longest, 4)) + (0.03 * (len(matches) - 1)))
        if score > best_score or (
            score == best_score
            and best_pattern is not None
            and pattern.component < best_pattern.component
        ):
            best_pattern = pattern
            best_score = score
            best_matches = matches
    return best_pattern, best_score, best_matches


def _infer_placement(prompt: str, default: str) -> str:
    if any(term in prompt for term in ("soldan", "left side", "left panel")):
        return "left"
    if any(term in prompt for term in ("sagdan", "right side", "right panel")):
        return "right"
    if any(term in prompt for term in ("alttan", "bottom sheet")):
        return "bottom"
    return default


def _infer_design_profile(prompt: str) -> dict[str, object]:
    variance, motion, density = 4, 3, 6
    language = "product-system"
    if any(term in prompt for term in ("minimal", "sade", "calm", "temiz")):
        variance, motion, density, language = 3, 2, 4, "restrained-minimal"
    elif any(term in prompt for term in ("premium", "luxury", "luk")):
        variance, motion, density, language = 5, 4, 4, "premium-restrained"
    elif any(term in prompt for term in ("dashboard", "kontrol paneli", "cockpit")):
        variance, motion, density, language = 4, 3, 8, "dense-operational"
    elif any(term in prompt for term in ("experimental", "playful", "yaratici")):
        variance, motion, density, language = 7, 6, 4, "expressive-bounded"

    return {
        "language": language,
        "design_variance": variance,
        "motion_intensity": motion,
        "visual_density": density,
        "anti_default": "derive visual choices from context; do not default to gradients, glass, card walls, or decorative motion",
    }
