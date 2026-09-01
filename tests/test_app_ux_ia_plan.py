from __future__ import annotations

from dataclasses import replace

import pytest

from services.app_architecture_plan import ApplicationArchitecturePlan
from services.app_product_spec import AppPlatform, ProductSpec
from services.app_state_machine_plan import AppStateMachinePlan
from services.app_ux_ia_plan import (
    AppUxIaPlanError,
    NavigationItem,
    NavigationMode,
    ScreenRequirement,
    UxIaPlan,
    build_ux_ia_plan,
)


def _spec(
    *,
    platforms: tuple[AppPlatform, ...] = ("android", "ios"),
    capabilities: tuple[str, ...] | None = None,
    accessibility_required: bool = True,
) -> ProductSpec:
    if capabilities is None:
        capabilities = (
            "authentication",
            "rbac",
            "workflows",
            "realtime",
            "notifications",
            "search",
            "settings",
        )
    return ProductSpec(
        project_id="proj-ux",
        product_name="ux-product",
        objective="governed product experience",
        platforms=platforms,
        actors=("member", "admin"),
        screens=("home", "request-detail", "search", "settings"),
        capabilities=capabilities,
        locales=("en",),
        accessibility_required=accessibility_required,
        offline_required=False,
        monetization="free",
        spec_sha256="spec-sha",
    )


def _architecture() -> ApplicationArchitecturePlan:
    return ApplicationArchitecturePlan(
        project_id="proj-ux",
        spec_sha256="spec-sha",
        architecture_tier="enterprise",
        persistence_mode="relational",
        realtime_mode="event-stream",
        file_mode="none",
        native_mode="mobile-capability-pack",
        requires_backend_api=True,
        requires_authentication=True,
        requires_authorization=True,
        requires_migrations=True,
        requires_external_integrations=False,
        requires_commerce_runtime=False,
        implementation_authority="software-factory",
        direct_publication_allowed=False,
        plan_sha256="architecture-sha",
    )


def _state_machines() -> AppStateMachinePlan:
    return AppStateMachinePlan(
        project_id="proj-ux",
        spec_sha256="spec-sha",
        architecture_plan_sha256="architecture-sha",
        auth_rbac_plan_sha256="auth-sha",
        machines=(),
        transition_count=2,
        policy_before_transition=True,
        approval_before_high_risk_transition=True,
        audit_after_transition=True,
        evidence_after_transition=True,
        runtime_authority="execution-coordinator",
        implementation_authority="software-factory",
        direct_state_mutation_allowed=False,
        direct_event_publication_allowed=False,
        plan_sha256="state-sha",
    )


def _screens() -> tuple[ScreenRequirement, ...]:
    return (
        ScreenRequirement(
            "home",
            "/",
            primary_navigation=True,
            recovery_required=True,
        ),
        ScreenRequirement(
            "request-detail",
            "/requests/detail",
            presentation="detail",
            parent_screen_id="home",
        ),
        ScreenRequirement(
            "search",
            "/search",
            presentation="search",
            primary_navigation=True,
            searchable=True,
        ),
        ScreenRequirement(
            "settings",
            "/settings",
            presentation="settings",
            primary_navigation=True,
        ),
    )


def _navigation() -> tuple[NavigationItem, ...]:
    return (
        NavigationItem("nav-home", "home", "Home", 0),
        NavigationItem("nav-search", "search", "Search", 1),
        NavigationItem("nav-settings", "settings", "Settings", 2),
    )


def _build(
    *,
    spec: ProductSpec | None = None,
    architecture: ApplicationArchitecturePlan | None = None,
    state_machines: AppStateMachinePlan | None = None,
    navigation_mode: NavigationMode = "bottom-tabs",
    screens: tuple[ScreenRequirement, ...] | None = None,
    navigation_items: tuple[NavigationItem, ...] | None = None,
    search_entry_screen_id: str | None = "search",
    settings_screen_id: str | None = "settings",
) -> UxIaPlan:
    return build_ux_ia_plan(
        spec=spec or _spec(),
        architecture=architecture or _architecture(),
        state_machines=state_machines or _state_machines(),
        navigation_mode=navigation_mode,
        screens=screens or _screens(),
        navigation_items=navigation_items or _navigation(),
        search_entry_screen_id=search_entry_screen_id,
        settings_screen_id=settings_screen_id,
    )


def test_plan_is_deterministic_and_grants_zero_runtime_authority() -> None:
    first = _build()
    second = _build()

    assert first == second
    assert first.route_count == 4
    assert first.error_recovery_required is True
    assert first.mobile_native_navigation_required is True
    assert first.implementation_authority == "software-factory"
    assert first.ui_is_authorization is False
    assert first.direct_route_publication_allowed is False
    assert len(first.plan_sha256) == 64


def test_binding_mismatch_fails_closed() -> None:
    with pytest.raises(AppUxIaPlanError, match="architecture plan"):
        _build(architecture=replace(_architecture(), spec_sha256="wrong"))

    with pytest.raises(AppUxIaPlanError, match="state-machine plan"):
        _build(
            state_machines=replace(
                _state_machines(),
                architecture_plan_sha256="wrong",
            )
        )


def test_product_spec_screen_coverage_and_route_uniqueness_fail_closed() -> None:
    missing = _screens()[:-1]
    with pytest.raises(AppUxIaPlanError, match="exactly match ProductSpec"):
        _build(screens=missing)

    duplicate_route = list(_screens())
    duplicate_route[1] = replace(duplicate_route[1], route="/")
    with pytest.raises(AppUxIaPlanError, match="route values must be unique"):
        _build(screens=tuple(duplicate_route))


def test_nested_surfaces_require_valid_parent() -> None:
    no_parent = list(_screens())
    no_parent[1] = replace(no_parent[1], parent_screen_id=None)
    with pytest.raises(AppUxIaPlanError, match="requires a parent screen"):
        _build(screens=tuple(no_parent))

    self_parent = list(_screens())
    self_parent[1] = replace(self_parent[1], parent_screen_id="request-detail")
    with pytest.raises(AppUxIaPlanError, match="own parent"):
        _build(screens=tuple(self_parent))


def test_mobile_cannot_be_shrunk_desktop_sidebar() -> None:
    with pytest.raises(AppUxIaPlanError, match="desktop sidebar-only"):
        _build(navigation_mode="sidebar")

    windows_spec = _spec(platforms=("windows",))
    plan = _build(spec=windows_spec, navigation_mode="sidebar")
    assert plan.navigation_mode == "sidebar"
    assert plan.mobile_native_navigation_required is False


def test_search_and_settings_require_declared_special_surfaces() -> None:
    with pytest.raises(AppUxIaPlanError, match="search capability"):
        _build(search_entry_screen_id=None)

    with pytest.raises(AppUxIaPlanError, match="settings capability"):
        _build(settings_screen_id=None)

    bad_search = list(_screens())
    bad_search[2] = replace(bad_search[2], searchable=False)
    with pytest.raises(AppUxIaPlanError, match="marked searchable"):
        _build(screens=tuple(bad_search))


def test_special_surface_cannot_be_invented_without_capability() -> None:
    capabilities = (
        "authentication",
        "rbac",
        "workflows",
        "realtime",
        "notifications",
    )
    spec = _spec(capabilities=capabilities)
    with pytest.raises(AppUxIaPlanError, match="cannot be invented"):
        _build(spec=spec)


def test_primary_navigation_and_navigation_targets_fail_closed() -> None:
    missing_primary = (
        NavigationItem("nav-search", "search", "Search", 0),
        NavigationItem("nav-settings", "settings", "Settings", 1),
    )
    with pytest.raises(AppUxIaPlanError, match="requires a navigation item"):
        _build(navigation_items=missing_primary)

    unknown = _navigation() + (NavigationItem("nav-ghost", "ghost", "Ghost", 3),)
    with pytest.raises(AppUxIaPlanError, match="unknown screen"):
        _build(navigation_items=unknown)


def test_accessible_product_requires_explicit_error_recovery_surface() -> None:
    no_recovery = tuple(replace(screen, recovery_required=False) for screen in _screens())
    with pytest.raises(AppUxIaPlanError, match="error-recovery"):
        _build(screens=no_recovery)

    plan = _build(spec=_spec(accessibility_required=False), screens=no_recovery)
    assert plan.error_recovery_required is False
