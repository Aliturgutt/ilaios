"""Deterministic, fail-closed UI intent resolver.

User text is treated only as data. The resolver has no filesystem, network,
secret, shell, provider, deployment, or mutation authority.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass

from .models import UIDesignSpec

MAX_PROMPT_CHARS = 4096


class UIDesignError(ValueError):
    """Raised when UI intent cannot be resolved safely."""


@dataclass(frozen=True, slots=True)
class _Pattern:
    component: str
    category: str
    aliases: tuple[str, ...]
    placement: str
    desktop_size: str
    compact_behavior: str
    interactions: tuple[str, ...]
    accessibility: tuple[str, ...]


_PATTERNS = (
    _Pattern(
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
        "full-screen-sheet",
        ("escape-close", "close-button", "restore-trigger-focus"),
        ("focus-trap", "dialog-semantics", "keyboard-operable", "visible-focus"),
    ),
    _Pattern(
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
        "wrap-without-horizontal-overflow",
        ("open-list", "toggle-option", "clear-selection"),
        (
            "labelled-control",
            "keyboard-navigation",
            "announced-selection-state",
            "visible-focus",
        ),
    ),
    _Pattern(
        "avatar-group",
        "display",
        (
            "avatar group",
            "stacked avatars",
            "overlapping avatars",
            "ust uste avatar",
            "ust uste kucuk kullanici resimleri",
        ),
        "inline",
        "content-sized",
        "cap-visible-avatars-and-show-overflow-count",
        ("show-overflow-count",),
        ("meaningful-alt-or-hidden-decoration", "non-color-only-identity"),
    ),
    _Pattern(
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
        "preserve-full-value-discoverability",
        ("reveal-full-value-on-demand",),
        ("full-value-accessible", "no-essential-information-loss"),
    ),
    _Pattern(
        "dialog",
        "overlay",
        ("dialog", "modal", "onay penceresi", "acilir pencere"),
        "center",
        "min(560px,calc(100vw-32px))",
        "safe-near-full-width",
        ("escape-close", "explicit-actions", "restore-trigger-focus"),
        (
            "focus-trap",
            "dialog-semantics",
            "labelled-title",
            "keyboard-operable",
            "visible-focus",
        ),
    ),
    _Pattern(
        "tabs",
        "navigation",
        ("tabs", "tab bar", "sekmeler", "sekme", "tab navigation"),
        "inline",
        "container-width",
        "intentional-compact-navigation",
        ("activate-tab", "preserve-selected-state"),
        ("tablist-semantics", "arrow-key-navigation", "visible-focus"),
    ),
    _Pattern(
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
        "bounded-full-width-overlay",
        ("type-to-filter", "escape-close", "keyboard-select"),
        ("combobox-semantics", "active-option-announcement", "visible-focus"),
    ),
    _Pattern(
        "data-table",
        "data-display",
        ("data table", "veri tablosu", "tablo", "satir sutun"),
        "inline",
        "container-width",
        "preserve-critical-columns",
        ("sort-when-supported", "filter-when-supported", "row-action-affordance"),
        ("header-association", "keyboard-operable-actions", "non-color-only-status"),
    ),
    _Pattern(
        "toast",
        "feedback",
        ("toast", "notification toast", "bildirim", "gecici bildirim"),
        "bottom-right",
        "360px",
        "respect-safe-areas",
        ("auto-dismiss-only-if-safe", "manual-dismiss-when-actionable"),
        ("live-region", "sufficient-reading-time", "keyboard-operable-action"),
    ),
    _Pattern(
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
        "responsive-container",
        "intentional-compact-tablet-wide-composition",
        ("preserve-hierarchy", "preserve-primary-action"),
        ("logical-focus-order", "semantic-regions", "visible-focus"),
    ),
)

_DIAGRAM_SIGNALS = (
    "diagram",
    "flowchart",
    "flow chart",
    "architecture diagram",
    "mimari diyagram",
    "node graph",
    "dag",
    "sequence diagram",
    "class diagram",
    "system map",
)

_QUALITY_GATES = (
    "no-clipping-or-overlap",
    "visible-focus",
    "required-interaction-states",
    "keyboard-operable",
    "semantic-labels-and-alt-text-when-applicable",
    "form-feedback-near-source-when-applicable",
    "layout-stability",
    "non-color-only-data-encoding-when-applicable",
    "predictable-navigation-and-back-behavior",
    "safe-area-aware-when-applicable",
    "reduced-motion-when-motion-exists",
    "intentional-compact-wide-adaptation",
    "existing-ilaios-design-quality-authority",
)


def resolve_ui_design(prompt: str, *, product: str | None = None) -> UIDesignSpec:
    normalized = _normalize(prompt)
    diagram_hits = tuple(
        signal for signal in _DIAGRAM_SIGNALS if _contains(normalized, signal)
    )
    candidates: list[tuple[float, _Pattern, tuple[str, ...]]] = []
    for pattern in _PATTERNS:
        hits = tuple(alias for alias in pattern.aliases if _contains(normalized, alias))
        if hits:
            longest = max(len(hit.split()) for hit in hits)
            score = min(
                0.98,
                0.68
                + 0.07 * min(longest, 4)
                + 0.03 * (len(hits) - 1),
            )
            candidates.append((score, pattern, hits))

    candidates.sort(key=lambda item: (-item[0], item[1].component))
    if not candidates:
        raise UIDesignError("no UI design intent matched")
    if diagram_hits:
        raise UIDesignError(
            "ambiguous UI/diagram intent must be resolved before execution"
        )
    if len(candidates) > 1 and candidates[0][0] - candidates[1][0] <= 0.05:
        raise UIDesignError(
            "ambiguous UI component intent must be resolved before execution"
        )

    score, pattern, hits = candidates[0]
    placement = _placement(normalized, pattern.placement)
    brand_policy = (
        "ILAIOS-canonical-tokens"
        if product and product.casefold() == "ilaios"
        else "inherit-target-product-brand"
    )
    return UIDesignSpec(
        schema_version="ilaios.ui-spec.v1",
        component=pattern.component,
        category=pattern.category,
        placement=placement,
        desktop_size=pattern.desktop_size,
        compact_behavior=pattern.compact_behavior,
        interactions=pattern.interactions,
        accessibility=pattern.accessibility,
        quality_gates=_QUALITY_GATES,
        confidence=round(score, 3),
        evidence=hits,
        brand_policy=brand_policy,
    )


def _normalize(prompt: str) -> str:
    if not isinstance(prompt, str):
        raise UIDesignError("prompt must be text")
    if "\x00" in prompt:
        raise UIDesignError("prompt contains a NUL character")
    stripped = prompt.strip()
    if not stripped:
        raise UIDesignError("prompt must not be blank")
    if len(stripped) > MAX_PROMPT_CHARS:
        raise UIDesignError(f"prompt exceeds {MAX_PROMPT_CHARS} characters")
    decomposed = unicodedata.normalize("NFKD", stripped.casefold())
    without_marks = "".join(
        char for char in decomposed if unicodedata.category(char) != "Mn"
    ).replace("ı", "i")
    token_safe = "".join(char if char.isalnum() else " " for char in without_marks)
    return " ".join(token_safe.split())


def _contains(prompt: str, phrase: str) -> bool:
    return f" {phrase} " in f" {prompt} "


def _placement(prompt: str, default: str) -> str:
    if any(_contains(prompt, term) for term in ("soldan", "left side", "left panel")):
        return "left"
    if any(_contains(prompt, term) for term in ("sagdan", "right side", "right panel")):
        return "right"
    if any(_contains(prompt, term) for term in ("alttan", "bottom sheet")):
        return "bottom"
    return default
