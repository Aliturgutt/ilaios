"""Tests for the deterministic enterprise App Factory product-spec foundation."""

import pytest

from services.app_product_spec import (
    AppProductSpecError,
    admit_project,
    build_product_spec,
    classify_risk,
    resolve_capabilities,
)


def test_admission_and_product_spec_are_deterministic() -> None:
    first_admission = admit_project(
        project_id="project-mobile",
        intent="reference",
        objective="Build a governed cross-platform operations client.",
        platforms=("android", "ios"),
        reference_asset_ids=("ref-home", "ref-workflows"),
    )
    second_admission = admit_project(
        project_id="project-mobile",
        intent="reference",
        objective="Build a governed cross-platform operations client.",
        platforms=("android", "ios"),
        reference_asset_ids=("ref-home", "ref-workflows"),
    )
    first = build_product_spec(
        admission=first_admission,
        product_name="Operations Mobile",
        actors=("owner", "reviewer"),
        screens=("home", "workflows", "approvals"),
        capabilities=("authentication", "rbac", "realtime", "files"),
        locales=("en", "tr"),
        offline_required=True,
    )
    second = build_product_spec(
        admission=second_admission,
        product_name="Operations Mobile",
        actors=("owner", "reviewer"),
        screens=("home", "workflows", "approvals"),
        capabilities=("authentication", "rbac", "realtime", "files"),
        locales=("en", "tr"),
        offline_required=True,
    )

    assert first_admission.admission_sha256 == second_admission.admission_sha256
    assert first.spec_sha256 == second.spec_sha256
    assert len(first.spec_sha256) == 64


def test_admission_intent_requirements_fail_closed() -> None:
    with pytest.raises(AppProductSpecError, match="requires an immutable source_asset_id"):
        admit_project(
            project_id="revision",
            intent="revision",
            objective="Revise the existing app.",
            platforms=("android",),
        )
    with pytest.raises(AppProductSpecError, match="requires at least one reference asset"):
        admit_project(
            project_id="reference",
            intent="reference",
            objective="Reconstruct from references.",
            platforms=("ios",),
        )
    with pytest.raises(AppProductSpecError, match="new intent cannot include"):
        admit_project(
            project_id="new",
            intent="new",
            objective="Create a new app.",
            platforms=("windows",),
            source_asset_id="source-existing",
        )


def test_capability_resolution_never_invents_availability() -> None:
    admission = admit_project(
        project_id="project-capabilities",
        intent="new",
        objective="Create a bounded application.",
        platforms=("android",),
    )
    spec = build_product_spec(
        admission=admission,
        product_name="Capability App",
        actors=("user",),
        screens=("home",),
        capabilities=("authentication", "camera", "payments", "custom-domain"),
    )
    assessments = resolve_capabilities(
        spec,
        available=frozenset({"authentication"}),
        external_dependencies=frozenset({"payments"}),
        blocked=frozenset({"custom-domain"}),
    )

    assert [(item.capability, item.status) for item in assessments] == [
        ("authentication", "AVAILABLE"),
        ("camera", "NEEDS_IMPLEMENTATION"),
        ("payments", "EXTERNAL_DEPENDENCY"),
        ("custom-domain", "BLOCKED"),
    ]


def test_capability_status_sets_must_be_disjoint() -> None:
    admission = admit_project(
        project_id="project-overlap",
        intent="new",
        objective="Create a bounded application.",
        platforms=("android",),
    )
    spec = build_product_spec(
        admission=admission,
        product_name="Overlap App",
        actors=("user",),
        screens=("home",),
        capabilities=("authentication",),
    )
    with pytest.raises(AppProductSpecError, match="mutually exclusive"):
        resolve_capabilities(
            spec,
            available=frozenset({"authentication"}),
            blocked=frozenset({"authentication"}),
        )


def test_enterprise_cross_store_risk_is_derived_from_explicit_spec_signals() -> None:
    admission = admit_project(
        project_id="project-enterprise",
        intent="new",
        objective="Create an enterprise mobile product.",
        platforms=("android", "ios"),
    )
    spec = build_product_spec(
        admission=admission,
        product_name="Enterprise Mobile",
        actors=("owner", "admin", "operator", "reviewer"),
        screens=("home", "projects", "workflows", "approvals", "evidence", "outputs", "settings"),
        capabilities=(
            "authentication",
            "rbac",
            "realtime",
            "files",
            "camera",
            "photos",
            "integrations",
            "external-api",
            "notifications",
            "offline-sync",
            "payments",
            "analytics",
        ),
        monetization="subscription",
    )
    assessment = classify_risk(spec)

    assert assessment.complexity == "enterprise"
    assert assessment.security == "high"
    assert assessment.privacy == "high"
    assert assessment.commerce == "high"
    assert assessment.external_integration == "high"
    assert assessment.store == "high"
    assert len(assessment.assessment_sha256) == 64
