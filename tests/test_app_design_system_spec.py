from __future__ import annotations

from dataclasses import replace

import pytest

from services.app_design_system_spec import (
    AppDesignSystemSpecError,
    ColorToken,
    ComponentVariant,
    DesignSystemSpec,
    TypographyToken,
    build_design_system_spec,
)
from services.app_product_spec import ProductSpec
from services.app_ux_ia_plan import UxIaPlan


def _product_spec() -> ProductSpec:
    return ProductSpec(
        project_id="proj-design",
        product_name="design-product",
        objective="governed product design",
        platforms=("android", "ios"),
        actors=("member", "admin"),
        screens=("home", "settings"),
        capabilities=("authentication", "settings"),
        locales=("en", "tr"),
        accessibility_required=True,
        offline_required=False,
        monetization="free",
        spec_sha256="spec-sha",
    )


def _ux() -> UxIaPlan:
    return UxIaPlan(
        project_id="proj-design",
        spec_sha256="spec-sha",
        architecture_plan_sha256="architecture-sha",
        state_machine_plan_sha256="state-sha",
        navigation_mode="bottom-tabs",
        screens=(),
        navigation_items=(),
        route_count=2,
        search_entry_screen_id=None,
        onboarding_screen_id=None,
        settings_screen_id="settings",
        error_recovery_required=True,
        mobile_native_navigation_required=True,
        implementation_authority="software-factory",
        ui_is_authorization=False,
        direct_route_publication_allowed=False,
        plan_sha256="ux-sha",
    )


def _colors() -> tuple[ColorToken, ...]:
    values = {
        "surface": ("#FFFFFF", "#111111"),
        "surface-muted": ("#F5F5F5", "#202020"),
        "text-primary": ("#111111", "#FFFFFF"),
        "text-secondary": ("#444444", "#CCCCCC"),
        "border": ("#DDDDDD", "#444444"),
        "accent": ("#005FCC", "#66AFFF"),
        "success": ("#16794A", "#6BD69E"),
        "warning": ("#8A5A00", "#F0C36A"),
        "danger": ("#B42318", "#FF8A80"),
        "focus": ("#005FCC", "#66AFFF"),
    }
    return tuple(ColorToken(name, light, dark) for name, (light, dark) in values.items())


def _typography() -> tuple[TypographyToken, ...]:
    return (
        TypographyToken("body", 16, 24, 400),
        TypographyToken("label", 14, 20, 500),
        TypographyToken("title", 24, 32, 600),
        TypographyToken("display", 40, 48, 700),
    )


def _components() -> tuple[ComponentVariant, ...]:
    return (
        ComponentVariant("button", ("primary", "secondary")),
        ComponentVariant("input", ("default",)),
        ComponentVariant("card", ("default",), empty_state=True),
        ComponentVariant("navigation", ("primary",)),
        ComponentVariant("dialog", ("confirmation",)),
    )


def _build(**overrides: object) -> DesignSystemSpec:
    values: dict[str, object] = {
        "product_spec": _product_spec(),
        "ux_ia": _ux(),
        "density": "comfortable",
        "colors": _colors(),
        "typography": _typography(),
        "spacing_scale_px": (4, 8, 12, 16, 24, 32),
        "radius_scale_px": (0, 4, 8, 12),
        "icon_sizes_px": (16, 20, 24, 32),
        "grid_columns": 12,
        "components": _components(),
        "touch_target_min_px": 44,
        "focus_ring_min_px": 2,
        "reduced_motion_supported": True,
        "responsive_breakpoints_px": (360, 600, 1024, 1440),
    }
    values.update(overrides)
    return build_design_system_spec(**values)  # type: ignore[arg-type]


def test_design_system_is_deterministic_and_grants_zero_runtime_authority() -> None:
    first = _build()
    second = _build()

    assert first == second
    assert first.implementation_authority == "software-factory"
    assert first.ui_is_authorization is False
    assert first.direct_runtime_mutation_allowed is False
    assert first.supported_themes == ("light", "dark")
    assert len(first.spec_sha256) == 64


def test_ux_binding_mismatch_fails_closed() -> None:
    with pytest.raises(AppDesignSystemSpecError, match="bound to the supplied ProductSpec"):
        _build(ux_ia=replace(_ux(), spec_sha256="wrong"))


def test_required_semantic_tokens_fail_closed() -> None:
    with pytest.raises(AppDesignSystemSpecError, match="missing required semantic color"):
        _build(colors=_colors()[:-1])

    with pytest.raises(AppDesignSystemSpecError, match="missing required typography"):
        _build(typography=_typography()[:-1])

    with pytest.raises(AppDesignSystemSpecError, match="missing required component"):
        _build(components=_components()[:-1])


def test_mobile_touch_target_and_accessibility_contracts_fail_closed() -> None:
    with pytest.raises(AppDesignSystemSpecError, match="at least 44px"):
        _build(touch_target_min_px=40)

    with pytest.raises(AppDesignSystemSpecError, match="focus ring"):
        _build(focus_ring_min_px=1)

    with pytest.raises(AppDesignSystemSpecError, match="reduced-motion"):
        _build(reduced_motion_supported=False)


def test_scales_and_themes_are_deterministic_and_complete() -> None:
    with pytest.raises(AppDesignSystemSpecError, match="strictly increasing"):
        _build(spacing_scale_px=(4, 8, 8, 16))

    with pytest.raises(AppDesignSystemSpecError, match="both light and dark"):
        _build(supported_themes=("light",))


def test_color_and_component_contract_validation_is_fail_closed() -> None:
    bad_colors = list(_colors())
    bad_colors[0] = replace(bad_colors[0], light="white")
    with pytest.raises(AppDesignSystemSpecError, match="#RRGGBB"):
        _build(colors=tuple(bad_colors))

    bad_components = list(_components())
    bad_components[0] = replace(bad_components[0], error_state=False)
    with pytest.raises(AppDesignSystemSpecError, match="error-state"):
        _build(components=tuple(bad_components))
