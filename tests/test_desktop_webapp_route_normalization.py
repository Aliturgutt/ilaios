from __future__ import annotations

import pytest

from services.desktop_execution_coordinator import normalize_desktop_execution_objective
from services.execution_coordinator import (
    ExecutionCoordinatorError,
    ExecutionRoute,
    classify_execution_route,
)


def _route_after_desktop_normalization(objective: str) -> ExecutionRoute:
    return classify_execution_route(normalize_desktop_execution_objective(objective))


def test_explicit_web_app_aliases_select_existing_canonical_web_route() -> None:
    objectives = (
        "Build a Web App dashboard for projects",
        "Create a web application for internal operations",
        "Bu referanslarla bir web uygulaması oluştur",
        "Create an admin panel for orders",
        "Create a management dashboard for operations",
        "Bu görsellerden bir yönetim paneli oluştur",
        "Create a customer portal for bookings",
    )
    for objective in objectives:
        normalized = normalize_desktop_execution_objective(objective)
        assert normalized.startswith("website ")
        route = classify_execution_route(normalized)
        assert route.capability_id == "ilaios.capability.web-factory"


def test_existing_canonical_web_objective_is_not_double_prefixed() -> None:
    objective = "Build a website dashboard for projects"
    normalized = normalize_desktop_execution_objective(objective)
    assert normalized == objective
    assert _route_after_desktop_normalization(objective).capability_id == (
        "ilaios.capability.web-factory"
    )


def test_mobile_and_desktop_app_dashboard_terms_are_not_rewritten_as_web() -> None:
    for objective in (
        "Build a mobile app dashboard for field teams",
        "Build a Windows desktop app dashboard",
    ):
        normalized = normalize_desktop_execution_objective(objective)
        assert not normalized.startswith("website ")
        route = classify_execution_route(normalized)
        assert route.capability_id == "ilaios.capability.app-factory"


def test_video_plus_dashboard_becomes_explicit_multi_capability_and_fails_closed() -> None:
    normalized = normalize_desktop_execution_objective(
        "Video creation task: create a launch video showing a dashboard"
    )
    assert normalized.startswith("website ")
    with pytest.raises(ExecutionCoordinatorError, match="multiple capabilities"):
        classify_execution_route(normalized)


def test_unknown_generic_objective_stays_unknown() -> None:
    objective = "Make something excellent"
    assert normalize_desktop_execution_objective(objective) == objective
    with pytest.raises(ExecutionCoordinatorError, match="could not be selected"):
        _route_after_desktop_normalization(objective)
