from __future__ import annotations

from services.desktop_identity_server import _reference_factory_count


def test_reference_intent_targets_exactly_one_factory() -> None:
    assert _reference_factory_count("Build a premium website for a furniture company") == 1
    assert _reference_factory_count("Video creation task: Create a product reveal") == 1
    assert _reference_factory_count("Create a product image") == 0
    assert (
        _reference_factory_count(
            "Video creation task: Create a launch video and a website landing page"
        )
        == 2
    )


def test_reference_intent_accepts_bounded_web_app_phrasing() -> None:
    web_objectives = (
        "Build a Web App dashboard from these screenshots",
        "Create a web application for internal operations",
        "Bu referanslarla bir web uygulaması oluştur",
        "Bu referanslarla bir web uygulamasi olustur",
        "Rebuild this dashboard with the same information hierarchy",
        "Create an admin panel using these reference images",
        "Create a management dashboard for operations",
        "Bu görsellerden bir yönetim paneli oluştur",
        "Bu gorsellerden bir yonetim paneli olustur",
    )
    for objective in web_objectives:
        assert _reference_factory_count(objective) == 1


def test_reference_intent_does_not_treat_generic_app_as_web_factory() -> None:
    assert _reference_factory_count("Build a mobile app from these screenshots") == 0
    assert _reference_factory_count("Create a desktop app") == 0
    assert _reference_factory_count("Design a control panel illustration") == 0


def test_reference_intent_fails_ambiguous_video_plus_dashboard_closed() -> None:
    assert (
        _reference_factory_count(
            "Video creation task: Create a product video showing a dashboard"
        )
        == 2
    )
