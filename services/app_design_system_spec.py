"""Deterministic Stage-2 enterprise application design-system contracts.

This module is specification/planning only. It does not render UI, authorize users,
mutate routes, deploy, sign, submit, or create a second design/runtime authority.
Implementation remains downstream through the canonical ExecutionCoordinator,
Software Factory, Policy/Approval/Tool Gateway, validation, audit and evidence
boundaries.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Literal

from services.app_product_spec import ProductSpec
from services.app_ux_ia_plan import UxIaPlan


Density = Literal["comfortable", "compact"]
ThemeMode = Literal["light", "dark"]


class AppDesignSystemSpecError(ValueError):
    """Design-system input is invalid, ambiguous, or unsafe."""


@dataclass(frozen=True, slots=True)
class ColorToken:
    token: str
    light: str
    dark: str


@dataclass(frozen=True, slots=True)
class TypographyToken:
    token: str
    size_px: int
    line_height_px: int
    weight: int


@dataclass(frozen=True, slots=True)
class ComponentVariant:
    component: str
    variants: tuple[str, ...]
    loading_state: bool = True
    empty_state: bool = False
    error_state: bool = True


@dataclass(frozen=True, slots=True)
class DesignSystemSpec:
    project_id: str
    product_spec_sha256: str
    ux_ia_plan_sha256: str
    density: Density
    colors: tuple[ColorToken, ...]
    typography: tuple[TypographyToken, ...]
    spacing_scale_px: tuple[int, ...]
    radius_scale_px: tuple[int, ...]
    icon_sizes_px: tuple[int, ...]
    grid_columns: int
    components: tuple[ComponentVariant, ...]
    touch_target_min_px: int
    focus_ring_min_px: int
    reduced_motion_supported: bool
    responsive_breakpoints_px: tuple[int, ...]
    supported_themes: tuple[ThemeMode, ...]
    implementation_authority: Literal["software-factory"]
    ui_is_authorization: Literal[False]
    direct_runtime_mutation_allowed: Literal[False]
    spec_sha256: str


_REQUIRED_COLORS = frozenset(
    {
        "surface",
        "surface-muted",
        "text-primary",
        "text-secondary",
        "border",
        "accent",
        "success",
        "warning",
        "danger",
        "focus",
    }
)
_REQUIRED_TYPOGRAPHY = frozenset({"body", "label", "title", "display"})
_REQUIRED_COMPONENTS = frozenset({"button", "input", "card", "navigation", "dialog"})


def build_design_system_spec(
    *,
    product_spec: ProductSpec,
    ux_ia: UxIaPlan,
    density: Density,
    colors: tuple[ColorToken, ...],
    typography: tuple[TypographyToken, ...],
    spacing_scale_px: tuple[int, ...],
    radius_scale_px: tuple[int, ...],
    icon_sizes_px: tuple[int, ...],
    grid_columns: int,
    components: tuple[ComponentVariant, ...],
    touch_target_min_px: int,
    focus_ring_min_px: int,
    reduced_motion_supported: bool,
    responsive_breakpoints_px: tuple[int, ...],
    supported_themes: tuple[ThemeMode, ...] = ("light", "dark"),
) -> DesignSystemSpec:
    """Compile an auditable design system without granting UI/runtime authority."""
    if ux_ia.project_id != product_spec.project_id or ux_ia.spec_sha256 != product_spec.spec_sha256:
        raise AppDesignSystemSpecError("UX/IA plan must be bound to the supplied ProductSpec")

    _validate_colors(colors)
    _validate_typography(typography)
    _positive_sorted_unique(spacing_scale_px, "spacing scale")
    _nonnegative_sorted_unique(radius_scale_px, "radius scale")
    _positive_sorted_unique(icon_sizes_px, "icon sizes")
    _validate_components(components)
    _positive_sorted_unique(responsive_breakpoints_px, "responsive breakpoints")

    if grid_columns < 1 or grid_columns > 24:
        raise AppDesignSystemSpecError("grid columns must be between 1 and 24")
    if touch_target_min_px < 44 and any(platform in {"android", "ios"} for platform in product_spec.platforms):
        raise AppDesignSystemSpecError("mobile touch target minimum must be at least 44px")
    if product_spec.accessibility_required and focus_ring_min_px < 2:
        raise AppDesignSystemSpecError("accessible products require a focus ring of at least 2px")
    if product_spec.accessibility_required and not reduced_motion_supported:
        raise AppDesignSystemSpecError("accessible products require reduced-motion support")
    if set(supported_themes) != {"light", "dark"}:
        raise AppDesignSystemSpecError("design system must define both light and dark themes")

    canonical: dict[str, object] = {
        "colors": [_color_payload(token) for token in colors],
        "components": [_component_payload(component) for component in components],
        "density": density,
        "direct_runtime_mutation_allowed": False,
        "focus_ring_min_px": focus_ring_min_px,
        "grid_columns": grid_columns,
        "icon_sizes_px": list(icon_sizes_px),
        "implementation_authority": "software-factory",
        "product_spec_sha256": product_spec.spec_sha256,
        "project_id": product_spec.project_id,
        "radius_scale_px": list(radius_scale_px),
        "reduced_motion_supported": reduced_motion_supported,
        "responsive_breakpoints_px": list(responsive_breakpoints_px),
        "spacing_scale_px": list(spacing_scale_px),
        "supported_themes": list(supported_themes),
        "touch_target_min_px": touch_target_min_px,
        "typography": [_typography_payload(token) for token in typography],
        "ui_is_authorization": False,
        "ux_ia_plan_sha256": ux_ia.plan_sha256,
    }
    return DesignSystemSpec(
        project_id=product_spec.project_id,
        product_spec_sha256=product_spec.spec_sha256,
        ux_ia_plan_sha256=ux_ia.plan_sha256,
        density=density,
        colors=colors,
        typography=typography,
        spacing_scale_px=spacing_scale_px,
        radius_scale_px=radius_scale_px,
        icon_sizes_px=icon_sizes_px,
        grid_columns=grid_columns,
        components=components,
        touch_target_min_px=touch_target_min_px,
        focus_ring_min_px=focus_ring_min_px,
        reduced_motion_supported=reduced_motion_supported,
        responsive_breakpoints_px=responsive_breakpoints_px,
        supported_themes=supported_themes,
        implementation_authority="software-factory",
        ui_is_authorization=False,
        direct_runtime_mutation_allowed=False,
        spec_sha256=_sha256_json(canonical),
    )


def _validate_colors(colors: tuple[ColorToken, ...]) -> None:
    names = tuple(token.token for token in colors)
    _unique(names, "color token")
    if not _REQUIRED_COLORS.issubset(names):
        missing = sorted(_REQUIRED_COLORS.difference(names))
        raise AppDesignSystemSpecError(f"missing required semantic color tokens: {missing}")
    for token in colors:
        _token(token.token, "color token")
        _hex_color(token.light)
        _hex_color(token.dark)


def _validate_typography(typography: tuple[TypographyToken, ...]) -> None:
    names = tuple(token.token for token in typography)
    _unique(names, "typography token")
    if not _REQUIRED_TYPOGRAPHY.issubset(names):
        missing = sorted(_REQUIRED_TYPOGRAPHY.difference(names))
        raise AppDesignSystemSpecError(f"missing required typography tokens: {missing}")
    for token in typography:
        _token(token.token, "typography token")
        if token.size_px < 10 or token.line_height_px < token.size_px:
            raise AppDesignSystemSpecError("typography size/line-height contract is invalid")
        if token.weight < 100 or token.weight > 900 or token.weight % 100:
            raise AppDesignSystemSpecError("typography weight must be 100..900 in 100 increments")


def _validate_components(components: tuple[ComponentVariant, ...]) -> None:
    names = tuple(component.component for component in components)
    _unique(names, "component")
    if not _REQUIRED_COMPONENTS.issubset(names):
        missing = sorted(_REQUIRED_COMPONENTS.difference(names))
        raise AppDesignSystemSpecError(f"missing required component contracts: {missing}")
    for component in components:
        _token(component.component, "component")
        if not component.variants:
            raise AppDesignSystemSpecError("component must define at least one variant")
        _unique(component.variants, "component variant")
        for variant in component.variants:
            _token(variant, "component variant")
        if not component.error_state:
            raise AppDesignSystemSpecError("components must retain an explicit error-state contract")


def _positive_sorted_unique(values: tuple[int, ...], label: str) -> None:
    if not values or any(value <= 0 for value in values):
        raise AppDesignSystemSpecError(f"{label} values must be positive")
    if tuple(sorted(set(values))) != values:
        raise AppDesignSystemSpecError(f"{label} values must be strictly increasing and unique")


def _nonnegative_sorted_unique(values: tuple[int, ...], label: str) -> None:
    if not values or any(value < 0 for value in values):
        raise AppDesignSystemSpecError(f"{label} values must be non-negative")
    if tuple(sorted(set(values))) != values:
        raise AppDesignSystemSpecError(f"{label} values must be strictly increasing and unique")


def _hex_color(value: str) -> None:
    if len(value) != 7 or not value.startswith("#"):
        raise AppDesignSystemSpecError("colors must use six-digit #RRGGBB notation")
    try:
        int(value[1:], 16)
    except ValueError as exc:
        raise AppDesignSystemSpecError("colors must use six-digit #RRGGBB notation") from exc


def _token(value: str, label: str) -> None:
    if not value or value != value.strip() or any(character.isspace() for character in value):
        raise AppDesignSystemSpecError(f"{label} must be a non-empty whitespace-free token")


def _unique(values: tuple[object, ...], label: str) -> None:
    if len(values) != len(set(values)):
        raise AppDesignSystemSpecError(f"{label} values must be unique")


def _color_payload(token: ColorToken) -> dict[str, object]:
    return {"dark": token.dark, "light": token.light, "token": token.token}


def _typography_payload(token: TypographyToken) -> dict[str, object]:
    return {
        "line_height_px": token.line_height_px,
        "size_px": token.size_px,
        "token": token.token,
        "weight": token.weight,
    }


def _component_payload(component: ComponentVariant) -> dict[str, object]:
    return {
        "component": component.component,
        "empty_state": component.empty_state,
        "error_state": component.error_state,
        "loading_state": component.loading_state,
        "variants": list(component.variants),
    }


def _sha256_json(payload: dict[str, object]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
