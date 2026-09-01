from __future__ import annotations

import pytest

from services.web_app_spec import WebAppSpecError, derive_web_app_spec
from services.web_reference_semantics import (
    WebReferenceSemanticBrief,
    WebSemanticObservation,
)


def _semantic() -> WebReferenceSemanticBrief:
    return WebReferenceSemanticBrief(
        schema_version="ilaios.web.reference-semantics.v1",
        observations=(
            WebSemanticObservation("layout", "Persistent left navigation and a wide workspace."),
            WebSemanticObservation("component", "Dense metric cards sit above a data table."),
            WebSemanticObservation("responsive", "Navigation collapses at compact widths."),
        ),
        reference_sha256s=("1" * 64,),
        analyzer_id="governed-web-visual:test",
        analysis_sha256="a" * 64,
    )


def test_dashboard_spec_derives_explicit_auth_crud_table_chart_and_api_requirements() -> None:
    spec = derive_web_app_spec(
        "request-dashboard-1",
        "Build a Web App dashboard with login, CRUD project management, a data table, analytics charts, and an external API integration.",
        semantic_brief=_semantic(),
    )

    assert spec.app_kind == "dashboard"
    assert spec.auth_required is True
    assert [(item.name, item.operations) for item in spec.resources] == [
        ("projects", ("create", "read", "update", "delete"))
    ]
    assert spec.tables_required is True
    assert spec.charts_required is True
    assert spec.external_api_required is True
    assert spec.reference_semantic_sha256 == "a" * 64
    assert len(spec.reference_design_constraints) == 3
    assert spec.requested_capabilities == (
        "web-app",
        "responsive-ui",
        "auth",
        "data",
        "crud",
        "tables",
        "charts",
        "external-api",
    )
    assert len(spec.spec_sha256) == 64
    assert any("unauthenticated" in item for item in spec.acceptance_requirements)
    assert any("visual-fidelity" in item for item in spec.acceptance_requirements)


def test_admin_spec_supports_multiple_explicit_resources_and_turkish() -> None:
    spec = derive_web_app_spec(
        "request-admin-tr",
        "Türkçe yönetim paneli: kullanıcılar, sipariş ve ürünler için ekle düzenle sil; tablo ve grafik göster.",
    )

    assert spec.app_kind == "admin"
    assert spec.locales == ("tr",)
    assert [item.name for item in spec.resources] == ["users", "orders", "products"]
    assert all(
        item.operations == ("create", "read", "update", "delete")
        for item in spec.resources
    )
    assert spec.tables_required is True
    assert spec.charts_required is True


def test_read_only_dashboard_does_not_invent_crud() -> None:
    spec = derive_web_app_spec(
        "request-readonly",
        "Build a dashboard that lists projects in a table and shows project metrics charts.",
    )

    assert [(item.name, item.operations) for item in spec.resources] == [
        ("projects", ("read",))
    ]
    assert "data" in spec.requested_capabilities
    assert "crud" not in spec.requested_capabilities
    assert "create" not in spec.resources[0].operations


def test_crud_without_explicit_resource_fails_closed() -> None:
    with pytest.raises(WebAppSpecError, match="without an explicit bounded resource"):
        derive_web_app_spec(
            "request-ambiguous-crud",
            "Build a Web App dashboard with login and CRUD record management.",
        )


def test_generic_mobile_or_desktop_app_is_not_misclassified_as_web_app() -> None:
    for objective in (
        "Build a mobile app dashboard for field teams",
        "Build a desktop app for Windows",
    ):
        with pytest.raises(WebAppSpecError, match="non-Web application platform"):
            derive_web_app_spec("request-not-web", objective)


def test_commerce_requires_explicit_products_or_orders() -> None:
    with pytest.raises(WebAppSpecError, match="without explicit products or orders"):
        derive_web_app_spec(
            "request-commerce",
            "Build a Web App with checkout and payment for customers.",
        )


def test_booking_adds_bounded_booking_resource() -> None:
    spec = derive_web_app_spec(
        "request-booking",
        "Build a customer portal for appointment booking with login and a table.",
    )

    assert spec.booking_required is True
    assert [item.name for item in spec.resources] == ["bookings"]
    assert spec.resources[0].operations == ("create", "read")
    assert "booking" in spec.requested_capabilities
    assert "crud" not in spec.requested_capabilities


def test_realtime_and_cms_are_requirements_not_readiness_claims() -> None:
    spec = derive_web_app_spec(
        "request-realtime-cms",
        "Build a Web Application CMS dashboard with realtime live updates and document management.",
    )

    assert spec.realtime_required is True
    assert spec.cms_required is True
    assert [item.name for item in spec.resources] == ["documents"]
    assert "realtime" in spec.requested_capabilities
    assert "cms" in spec.requested_capabilities
    assert any("realtime disconnect" in item for item in spec.acceptance_requirements)


def test_spec_hash_is_deterministic() -> None:
    first = derive_web_app_spec(
        "request-deterministic",
        "Build a Web App dashboard that lists tasks in a table.",
    )
    second = derive_web_app_spec(
        "request-deterministic",
        "Build a Web App dashboard that lists tasks in a table.",
    )

    assert first == second
    assert first.spec_sha256 == second.spec_sha256
