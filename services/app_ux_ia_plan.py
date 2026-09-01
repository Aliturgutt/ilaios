"""Deterministic Stage-2 enterprise UX/IA planning contracts.

This module is specification/planning only. It does not render UI, mutate routes,
authorize users, execute transitions, publish runtime events, deploy, sign, submit,
or create a second runtime authority. Implementation remains downstream through the
canonical ExecutionCoordinator, Software Factory, Policy/Approval/Tool Gateway,
validation, audit and evidence boundaries.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Literal

from services.app_architecture_plan import ApplicationArchitecturePlan
from services.app_product_spec import ProductSpec
from services.app_state_machine_plan import AppStateMachinePlan


NavigationMode = Literal["sidebar", "drawer", "bottom-tabs", "top-tabs", "stack", "hybrid"]
ScreenPresentation = Literal[
    "page", "detail", "modal", "sheet", "search", "settings", "onboarding"
]


class AppUxIaPlanError(ValueError):
    """UX/IA planning input is invalid, ambiguous, or unsafe."""


@dataclass(frozen=True, slots=True)
class ScreenRequirement:
    screen_id: str
    route: str
    presentation: ScreenPresentation = "page"
    parent_screen_id: str | None = None
    primary_navigation: bool = False
    searchable: bool = False
    recovery_required: bool = False


@dataclass(frozen=True, slots=True)
class NavigationItem:
    navigation_id: str
    screen_id: str
    label: str
    order: int


@dataclass(frozen=True, slots=True)
class UxIaPlan:
    project_id: str
    spec_sha256: str
    architecture_plan_sha256: str
    state_machine_plan_sha256: str
    navigation_mode: NavigationMode
    screens: tuple[ScreenRequirement, ...]
    navigation_items: tuple[NavigationItem, ...]
    route_count: int
    search_entry_screen_id: str | None
    onboarding_screen_id: str | None
    settings_screen_id: str | None
    error_recovery_required: bool
    mobile_native_navigation_required: bool
    implementation_authority: Literal["software-factory"]
    ui_is_authorization: Literal[False]
    direct_route_publication_allowed: Literal[False]
    plan_sha256: str


def build_ux_ia_plan(
    *,
    spec: ProductSpec,
    architecture: ApplicationArchitecturePlan,
    state_machines: AppStateMachinePlan,
    navigation_mode: NavigationMode,
    screens: tuple[ScreenRequirement, ...],
    navigation_items: tuple[NavigationItem, ...],
    search_entry_screen_id: str | None = None,
    onboarding_screen_id: str | None = None,
    settings_screen_id: str | None = None,
) -> UxIaPlan:
    """Compile deterministic UX/IA without granting rendering or auth authority."""
    if architecture.project_id != spec.project_id or architecture.spec_sha256 != spec.spec_sha256:
        raise AppUxIaPlanError("architecture plan must be bound to the supplied ProductSpec")
    if (
        state_machines.project_id != spec.project_id
        or state_machines.spec_sha256 != spec.spec_sha256
        or state_machines.architecture_plan_sha256 != architecture.plan_sha256
    ):
        raise AppUxIaPlanError(
            "state-machine plan must be bound to the supplied ProductSpec and architecture"
        )
    if not screens:
        raise AppUxIaPlanError("at least one screen is required")

    screen_ids = tuple(screen.screen_id for screen in screens)
    if screen_ids != spec.screens:
        raise AppUxIaPlanError("UX/IA screens must exactly match ProductSpec screen ordering")
    _require_unique(screen_ids, "screen_id")

    known_screens = frozenset(screen_ids)
    routes = tuple(screen.route for screen in screens)
    _require_unique(routes, "route")
    for screen in screens:
        _token(screen.screen_id, "screen_id")
        _route(screen.route)
        _validate_parent(screen, known_screens)

    _require_unique(tuple(item.navigation_id for item in navigation_items), "navigation_id")
    _require_unique(tuple(item.order for item in navigation_items), "navigation order")
    _require_unique(tuple(item.screen_id for item in navigation_items), "navigation screen")
    for item in navigation_items:
        _token(item.navigation_id, "navigation_id")
        _text(item.label, "navigation label")
        if item.order < 0:
            raise AppUxIaPlanError("navigation order cannot be negative")
        if item.screen_id not in known_screens:
            raise AppUxIaPlanError("navigation item references an unknown screen")

    navigation_targets = frozenset(item.screen_id for item in navigation_items)
    for screen in screens:
        if screen.primary_navigation and screen.screen_id not in navigation_targets:
            raise AppUxIaPlanError("primary-navigation screen requires a navigation item")

    mobile_platform = any(platform in {"android", "ios"} for platform in spec.platforms)
    if mobile_platform and navigation_mode == "sidebar":
        raise AppUxIaPlanError("mobile UX cannot use desktop sidebar-only navigation")

    _validate_special_screen(
        screen_id=search_entry_screen_id,
        required="search" in spec.capabilities,
        expected_presentation="search",
        label="search",
        screens=screens,
    )
    _validate_special_screen(
        screen_id=onboarding_screen_id,
        required="onboarding" in spec.capabilities,
        expected_presentation="onboarding",
        label="onboarding",
        screens=screens,
    )
    _validate_special_screen(
        screen_id=settings_screen_id,
        required="settings" in spec.capabilities,
        expected_presentation="settings",
        label="settings",
        screens=screens,
    )

    if search_entry_screen_id is not None:
        search_screen = _screen_by_id(screens, search_entry_screen_id)
        if not search_screen.searchable:
            raise AppUxIaPlanError("search entry screen must be marked searchable")

    error_recovery_required = spec.accessibility_required
    if error_recovery_required and not any(screen.recovery_required for screen in screens):
        raise AppUxIaPlanError(
            "accessible UX requires at least one explicit error-recovery surface"
        )

    ordered_navigation = tuple(sorted(navigation_items, key=lambda item: item.order))
    canonical: dict[str, object] = {
        "architecture_plan_sha256": architecture.plan_sha256,
        "direct_route_publication_allowed": False,
        "error_recovery_required": error_recovery_required,
        "implementation_authority": "software-factory",
        "mobile_native_navigation_required": mobile_platform,
        "navigation_items": [_navigation_payload(item) for item in ordered_navigation],
        "navigation_mode": navigation_mode,
        "onboarding_screen_id": onboarding_screen_id,
        "project_id": spec.project_id,
        "route_count": len(routes),
        "screens": [_screen_payload(screen) for screen in screens],
        "search_entry_screen_id": search_entry_screen_id,
        "settings_screen_id": settings_screen_id,
        "spec_sha256": spec.spec_sha256,
        "state_machine_plan_sha256": state_machines.plan_sha256,
        "ui_is_authorization": False,
    }
    return UxIaPlan(
        project_id=spec.project_id,
        spec_sha256=spec.spec_sha256,
        architecture_plan_sha256=architecture.plan_sha256,
        state_machine_plan_sha256=state_machines.plan_sha256,
        navigation_mode=navigation_mode,
        screens=screens,
        navigation_items=ordered_navigation,
        route_count=len(routes),
        search_entry_screen_id=search_entry_screen_id,
        onboarding_screen_id=onboarding_screen_id,
        settings_screen_id=settings_screen_id,
        error_recovery_required=error_recovery_required,
        mobile_native_navigation_required=mobile_platform,
        implementation_authority="software-factory",
        ui_is_authorization=False,
        direct_route_publication_allowed=False,
        plan_sha256=_sha256_json(canonical),
    )


def _validate_parent(screen: ScreenRequirement, known_screens: frozenset[str]) -> None:
    needs_parent = screen.presentation in {"detail", "modal", "sheet"}
    if needs_parent and screen.parent_screen_id is None:
        raise AppUxIaPlanError(f"{screen.presentation} screen requires a parent screen")
    if screen.parent_screen_id is None:
        return
    if screen.parent_screen_id == screen.screen_id:
        raise AppUxIaPlanError("screen cannot be its own parent")
    if screen.parent_screen_id not in known_screens:
        raise AppUxIaPlanError("screen parent references an unknown screen")


def _validate_special_screen(
    *,
    screen_id: str | None,
    required: bool,
    expected_presentation: ScreenPresentation,
    label: str,
    screens: tuple[ScreenRequirement, ...],
) -> None:
    if required and screen_id is None:
        raise AppUxIaPlanError(f"{label} capability requires an explicit {label} screen")
    if not required and screen_id is not None:
        raise AppUxIaPlanError(f"{label} screen cannot be invented without ProductSpec capability")
    if screen_id is None:
        return
    screen = _screen_by_id(screens, screen_id)
    if screen.presentation != expected_presentation:
        raise AppUxIaPlanError(
            f"{label} screen must use {expected_presentation} presentation"
        )


def _screen_by_id(
    screens: tuple[ScreenRequirement, ...], screen_id: str
) -> ScreenRequirement:
    for screen in screens:
        if screen.screen_id == screen_id:
            return screen
    raise AppUxIaPlanError("special screen references an unknown screen")


def _screen_payload(screen: ScreenRequirement) -> dict[str, object]:
    return {
        "parent_screen_id": screen.parent_screen_id,
        "presentation": screen.presentation,
        "primary_navigation": screen.primary_navigation,
        "recovery_required": screen.recovery_required,
        "route": screen.route,
        "screen_id": screen.screen_id,
        "searchable": screen.searchable,
    }


def _navigation_payload(item: NavigationItem) -> dict[str, object]:
    return {
        "label": item.label,
        "navigation_id": item.navigation_id,
        "order": item.order,
        "screen_id": item.screen_id,
    }


def _route(value: str) -> None:
    if not value.startswith("/") or any(character.isspace() for character in value):
        raise AppUxIaPlanError("route must be an absolute whitespace-free application route")
    if "?" in value or "#" in value:
        raise AppUxIaPlanError("route cannot contain query or fragment state")
    if len(value) > 1 and value.endswith("/"):
        raise AppUxIaPlanError("route cannot end with a trailing slash")


def _token(value: str, label: str) -> None:
    if not value or value != value.strip() or any(character.isspace() for character in value):
        raise AppUxIaPlanError(f"{label} must be a non-empty whitespace-free token")


def _text(value: str, label: str) -> None:
    if not value.strip():
        raise AppUxIaPlanError(f"{label} must be non-empty")


def _require_unique(values: tuple[object, ...], label: str) -> None:
    if len(values) != len(set(values)):
        raise AppUxIaPlanError(f"{label} values must be unique")


def _sha256_json(payload: dict[str, object]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
