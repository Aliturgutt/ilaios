from __future__ import annotations

import pytest

from services.web_app_design_contract import (
    WebAppDesignContractError,
    derive_web_app_design_contract,
)
from services.web_app_spec import WebAppSpec, derive_web_app_spec
from services.web_reference_semantics import (
    WebReferenceSemanticBrief,
    WebSemanticObservation,
)


def _semantic() -> WebReferenceSemanticBrief:
    return WebReferenceSemanticBrief(
        schema_version="ilaios.web.reference-semantics.v1",
        observations=(
            WebSemanticObservation("layout", "Persistent left navigation and a wide workspace."),
            WebSemanticObservation("component", "Dense cards, tables and right-side detail panels."),
            WebSemanticObservation("navigation", "Top bar includes project switcher, search and profile."),
            WebSemanticObservation("responsive", "Primary navigation collapses at compact widths."),
            WebSemanticObservation("fidelity", "Preserve dense enterprise information hierarchy."),
        ),
        reference_sha256s=("1" * 64,),
        analyzer_id="governed-web-visual:test",
        analysis_sha256="a" * 64,
    )


def _spec_with_reference() -> WebAppSpec:
    return derive_web_app_spec(
        "request-shell-design",
        "Build a Web App dashboard with login, CRUD project management, tables and analytics charts.",
        semantic_brief=_semantic(),
    )


def _measurements() -> dict[str, tuple[float, ...]]:
    return {
        "spacing_scale_px": (4, 8, 12, 16, 24, 32, 48, 64),
        "font_size_scale_px": (12, 14, 16, 20, 24, 32, 40),
        "line_height_scale": (1.2, 1.35, 1.5, 1.65),
        "font_weight_scale": (400, 500, 600, 700),
        "radius_scale_px": (4, 8, 12, 16),
        "table_row_height_px": (44,),
        "icon_size_scale_px": (16, 20, 24),
        "sidebar_width_px": (240,),
        "topbar_height_px": (64,),
        "content_max_width_px": (1600,),
        "grid_columns": (12,),
        "breakpoints_px": (480, 768, 1024, 1280, 1536),
    }


def test_enterprise_dashboard_shell_has_all_required_slots_and_states() -> None:
    semantic = _semantic()
    contract = derive_web_app_design_contract(
        _spec_with_reference(), semantic_brief=semantic
    )
    assert contract.shell.shell_profile == "enterprise-dashboard"
    assert contract.shell.required_slots == (
        "sidebar",
        "topbar",
        "project-switcher",
        "global-search",
        "notifications",
        "profile",
        "persistent-footer-status-bar",
        "nested-routes",
        "selected-navigation-state",
        "drawer-detail-panels",
    )
    assert contract.shell.route_model == "nested-routes-with-authenticated-layout-boundary"
    assert "selected" in contract.design_system.component_states
    assert "loading" in contract.design_system.component_states
    assert "empty" in contract.design_system.component_states
    assert "error" in contract.design_system.component_states
    assert contract.design_system.semantic_status_roles == (
        "info", "success", "warning", "danger", "neutral", "accent"
    )


def test_unmeasured_reference_stays_explicitly_not_reference_exact() -> None:
    contract = derive_web_app_design_contract(
        _spec_with_reference(), semantic_brief=_semantic()
    )
    assert contract.design_system.measurements.source == "baseline"
    assert contract.design_system.reference_fidelity_status == "BASELINE_ONLY_NOT_REFERENCE_EXACT"
    assert any("unproven" in item for item in contract.acceptance_requirements)


def test_exact_measurements_bind_to_semantic_digest_and_are_deterministic() -> None:
    semantic = _semantic()
    first = derive_web_app_design_contract(
        _spec_with_reference(), semantic_brief=semantic, measurements=_measurements()
    )
    second = derive_web_app_design_contract(
        _spec_with_reference(), semantic_brief=semantic, measurements=_measurements()
    )
    assert first.design_system.measurements.source == "reference-measurement"
    assert first.design_system.measurements.semantic_analysis_sha256 == "a" * 64
    assert first.design_system.reference_fidelity_status == "MEASURED_REFERENCE_CONTRACT"
    assert len(first.contract_sha256) == 64
    assert first == second
    assert first.contract_sha256 == second.contract_sha256


def test_reference_bound_spec_requires_exact_semantic_brief() -> None:
    with pytest.raises(WebAppDesignContractError, match="requires the exact semantic brief"):
        derive_web_app_design_contract(_spec_with_reference())
    wrong = WebReferenceSemanticBrief(
        schema_version="ilaios.web.reference-semantics.v1",
        observations=(WebSemanticObservation("layout", "Wide workspace."),),
        reference_sha256s=("2" * 64,),
        analyzer_id="governed-web-visual:test",
        analysis_sha256="b" * 64,
    )
    with pytest.raises(WebAppDesignContractError, match="does not match"):
        derive_web_app_design_contract(_spec_with_reference(), semantic_brief=wrong)


def test_measurements_fail_closed_on_missing_unknown_or_non_monotonic_values() -> None:
    semantic = _semantic()
    missing = _measurements()
    missing.pop("grid_columns")
    with pytest.raises(WebAppDesignContractError, match="incomplete"):
        derive_web_app_design_contract(
            _spec_with_reference(), semantic_brief=semantic, measurements=missing
        )
    unknown = _measurements()
    unknown["shadow_blur_px"] = (8,)
    with pytest.raises(WebAppDesignContractError, match="unsupported"):
        derive_web_app_design_contract(
            _spec_with_reference(), semantic_brief=semantic, measurements=unknown
        )
    non_monotonic = _measurements()
    non_monotonic["spacing_scale_px"] = (4, 8, 8, 16)
    with pytest.raises(WebAppDesignContractError, match="strictly increasing"):
        derive_web_app_design_contract(
            _spec_with_reference(), semantic_brief=semantic, measurements=non_monotonic
        )


def test_non_reference_spec_rejects_unbound_reference_measurements() -> None:
    spec = derive_web_app_spec(
        "request-no-reference",
        "Build a Web App dashboard that lists projects in a table.",
    )
    with pytest.raises(WebAppDesignContractError, match="reference measurements require"):
        derive_web_app_design_contract(spec, measurements=_measurements())
