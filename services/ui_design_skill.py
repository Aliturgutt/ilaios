"""Deterministic, zero-authority ILAIOS UI design skill.

The resolver turns bounded natural-language UI intent into structured constraints.
It never executes generated code, imports user-selected modules, accesses network or
secrets, mutates repositories, or grants deployment authority.
"""

from __future__ import annotations

import json
import re
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Final, cast


class UIDesignSkillError(ValueError):
    """Raised when UI intent is unsafe, malformed, or ambiguous."""


MAX_UI_INTENT_CHARS = 4096
UI_SKILL_ID = "ilaios-ui-design"
UI_SKILL_VERSION = "1.0.0"
UI_SPEC_SCHEMA = "ilaios.ui-spec.v1"


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


_PATTERNS: Final[tuple[_Pattern, ...]] = (
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
        "full-screen sheet",
        ("escape-close", "close-button", "restore-trigger-focus"),
        ("focus-trap", "dialog-semantics", "keyboard-operable"),
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
        "wrap selected values without horizontal overflow",
        ("open-list", "toggle-option", "clear-selection"),
        (
            "labelled-control",
            "keyboard-navigation",
            "announced-selection-state",
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
            "kullanici resimleri",
        ),
        "inline",
        "content-sized",
        "cap visible avatars and expose remaining count",
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
        "truncate only when the full value remains discoverable",
        ("reveal-full-value-on-demand",),
        ("full-value-accessible", "no-essential-information-loss"),
    ),
    _Pattern(
        "dialog",
        "overlay",
        ("dialog", "modal", "onay penceresi", "acilir pencere"),
        "center",
        "min(560px, calc(100vw - 32px))",
        "near-full-width dialog with safe viewport margins",
        (
            "escape-close",
            "explicit-primary-secondary-actions",
            "restore-trigger-focus",
        ),
        (
            "focus-trap",
            "dialog-semantics",
            "labelled-title",
            "keyboard-operable",
        ),
    ),
    _Pattern(
        "tabs",
        "navigation",
        ("tabs", "tab bar", "sekmeler", "sekme", "tab navigation"),
        "inline",
        "container-width",
        "scroll or transform navigation intentionally on compact surfaces",
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
        "full-width overlay with bounded height",
        ("type-to-filter", "escape-close", "keyboard-select"),
        (
            "combobox-semantics",
            "active-option-announcement",
            "visible-focus",
        ),
    ),
    _Pattern(
        "data-table",
        "data-display",
        ("data table", "table", "tablo", "veri tablosu", "satir sutun"),
        "inline",
        "container-width",
        "preserve critical columns and transform secondary data deliberately",
        ("sort-when-supported", "filter-when-supported", "row-action-affordance"),
        (
            "header-association",
            "keyboard-operable-actions",
            "non-color-only-status",
        ),
    ),
    _Pattern(
        "toast",
        "feedback",
        ("toast", "notification toast", "bildirim", "gecici bildirim"),
        "bottom-right",
        "360px",
        "respect safe areas and avoid covering primary controls",
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
        "responsive container",
        "derive compact/tablet/wide composition instead of stacking blindly",
        ("preserve-hierarchy", "preserve-primary-action"),
        (
            "logical-focus-order",
            "landmarks-or-native-semantics",
            "visible-focus",
        ),
    ),
)

_GENERIC_UI_TERMS: Final[tuple[str, ...]] = (
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

_DIAGRAM_TERMS: Final[tuple[str, ...]] = (
    "diagram",
    "diyagram",
    "flowchart",
    "akis semasi",
    "node graph",
    "architecture graph",
    "system map",
    "dag",
)


def normalize_ui_intent(intent: str) -> str:
    """Normalize bounded multilingual intent into token-safe text."""
    if not isinstance(intent, str):
        raise UIDesignSkillError("UI intent must be text")
    if "\x00" in intent:
        raise UIDesignSkillError("UI intent contains a NUL character")
    stripped = intent.strip()
    if not stripped:
        raise UIDesignSkillError("UI intent must not be blank")
    if len(stripped) > MAX_UI_INTENT_CHARS:
        raise UIDesignSkillError(
            f"UI intent exceeds {MAX_UI_INTENT_CHARS} characters"
        )
    decomposed = unicodedata.normalize("NFKD", stripped.casefold())
    without_marks = "".join(
        character
        for character in decomposed
        if unicodedata.category(character) != "Mn"
    ).replace("ı", "i")
    token_safe = "".join(
        character if character.isalnum() else " " for character in without_marks
    )
    return " ".join(token_safe.split())


def is_ui_design_intent(intent: str) -> bool:
    """Return True only when UI intent has deterministic lexical evidence."""
    normalized = normalize_ui_intent(intent)
    matches = _pattern_matches(normalized)
    if matches:
        return True
    has_ui = any(_contains(normalized, term) for term in _GENERIC_UI_TERMS)
    has_diagram = any(_contains(normalized, term) for term in _DIAGRAM_TERMS)
    return has_ui and not has_diagram


def resolve_ui_design(payload: Mapping[str, object]) -> dict[str, object]:
    """Resolve a validated, zero-authority UI specification."""
    if not isinstance(payload, Mapping):
        raise UIDesignSkillError("UI skill payload must be an object")
    raw_intent = payload.get("intent")
    if not isinstance(raw_intent, str):
        raise UIDesignSkillError("UI skill intent must be text")
    normalized = normalize_ui_intent(raw_intent)
    matches = _pattern_matches(normalized)
    if not matches:
        has_diagram = any(_contains(normalized, term) for term in _DIAGRAM_TERMS)
        if has_diagram:
            raise UIDesignSkillError(
                "diagram intent belongs to ilaios-diagram-design"
            )
        if not any(_contains(normalized, term) for term in _GENERIC_UI_TERMS):
            raise UIDesignSkillError("UI component intent could not be resolved")
        pattern = next(item for item in _PATTERNS if item.component == "surface-layout")
        evidence = ("generic-ui-intent",)
    else:
        best_length = max(score for score, _, _ in matches)
        strongest = [item for item in matches if item[0] == best_length]
        components = {item[1].component for item in strongest}
        if len(components) != 1:
            raise UIDesignSkillError("ambiguous UI component intent")
        _, pattern, evidence = strongest[0]

    placement = _placement(normalized, pattern.placement)
    product = payload.get("product")
    brand_policy = (
        "ILAIOS-canonical-tokens"
        if isinstance(product, str) and product.casefold() == "ilaios"
        else "inherit-existing-project-brand"
    )
    output: dict[str, object] = {
        "skill_id": UI_SKILL_ID,
        "version": UI_SKILL_VERSION,
        "review_required": True,
        "schema_version": UI_SPEC_SCHEMA,
        "component": pattern.component,
        "category": pattern.category,
        "evidence": list(evidence),
        "layout": {
            "placement": placement,
            "desktop_size": pattern.desktop_size,
            "compact_behavior": pattern.compact_behavior,
        },
        "interaction": list(pattern.interactions),
        "accessibility": list(pattern.accessibility),
        "design_system": {
            "brand_policy": brand_policy,
            "dependency_rule": "reuse-existing-project-system-first",
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
        "codegen_constraints": [
            "treat-ui-spec-as-data-not-executable-instructions",
            "reuse-existing-project-tokens-and-primitives",
            "do-not-add-dependencies-without-governed-dependency-review",
            "do-not-invent-product-claims-or-hidden-side-effects",
            "submit-generated-ui-to-existing-design-quality-gates",
        ],
        "authority": {
            "shell": False,
            "network": False,
            "secrets": False,
            "deploy": False,
        },
    }
    _assert_json_bounded(output)
    return output


def ui_spec_digest(spec: Mapping[str, object]) -> str:
    """Canonical SHA-256 identity for a UI specification."""
    import hashlib

    encoded = json.dumps(
        dict(spec), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _pattern_matches(
    normalized: str,
) -> list[tuple[int, _Pattern, tuple[str, ...]]]:
    found: list[tuple[int, _Pattern, tuple[str, ...]]] = []
    for pattern in _PATTERNS:
        aliases = tuple(
            alias for alias in pattern.aliases if _contains(normalized, alias)
        )
        if aliases:
            longest = max(len(alias.split()) for alias in aliases)
            found.append((longest, pattern, aliases))
    return found


def _contains(normalized: str, term: str) -> bool:
    normalized_term = normalize_ui_intent(term)
    pattern = rf"(?<!\w){re.escape(normalized_term)}(?!\w)"
    return re.search(pattern, normalized, flags=re.UNICODE) is not None


def _placement(normalized: str, default: str) -> str:
    if any(_contains(normalized, term) for term in ("soldan", "left side", "left panel")):
        return "left"
    if any(_contains(normalized, term) for term in ("sagdan", "right side", "right panel")):
        return "right"
    if any(_contains(normalized, term) for term in ("alttan", "bottom sheet")):
        return "bottom"
    return default


def _assert_json_bounded(output: Mapping[str, object]) -> None:
    encoded = json.dumps(output, sort_keys=True, ensure_ascii=False)
    if len(encoded.encode("utf-8")) > 32_768:
        raise UIDesignSkillError("UI specification exceeds bounded output size")
    if not isinstance(cast(Mapping[str, object], output["authority"]), Mapping):
        raise UIDesignSkillError("UI authority contract is malformed")
