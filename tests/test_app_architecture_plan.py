from __future__ import annotations

import pytest

from services.app_architecture_plan import (
    AppArchitecturePlanError,
    plan_application_architecture,
)
from services.app_product_spec import (
    AppPlatform,
    ProductSpec,
    admit_project,
    build_product_spec,
    classify_risk,
    resolve_capabilities,
)


def _build_spec(
    *,
    capabilities: tuple[str, ...],
    platforms: tuple[AppPlatform, ...] = ("android",),
) -> ProductSpec:
    admission = admit_project(
        project_id="project-architecture-test",
        intent="new",
        objective="Build a governed mobile application",
        platforms=platforms,
    )
    return build_product_spec(
        admission=admission,
        product_name="Architecture Test",
        actors=("owner", "member"),
        screens=("home", "settings"),
        capabilities=capabilities,
    )


def test_planner_derives_governed_service_backed_mobile_architecture() -> None:
    spec = _build_spec(
        capabilities=(
            "authentication",
            "rbac",
            "database",
            "realtime",
            "files",
            "integrations",
        )
    )
    assessments = resolve_capabilities(spec)
    risk = classify_risk(spec)

    plan = plan_application_architecture(
        spec=spec,
        capability_assessments=assessments,
        risk=risk,
    )

    assert plan.architecture_tier in {"service-backed", "enterprise"}
    assert plan.persistence_mode == "relational"
    assert plan.realtime_mode == "event-stream"
    assert plan.file_mode == "object-storage"
    assert plan.native_mode == "mobile-capability-pack"
    assert plan.requires_backend_api is True
    assert plan.requires_authentication is True
    assert plan.requires_authorization is True
    assert plan.requires_migrations is True
    assert plan.requires_external_integrations is True
    assert plan.implementation_authority == "software-factory"
    assert plan.direct_publication_allowed is False
    assert len(plan.plan_sha256) == 64


def test_planner_is_deterministic_for_identical_inputs() -> None:
    spec = _build_spec(capabilities=("database", "files"))
    assessments = resolve_capabilities(spec)
    risk = classify_risk(spec)

    first = plan_application_architecture(
        spec=spec,
        capability_assessments=assessments,
        risk=risk,
    )
    second = plan_application_architecture(
        spec=spec,
        capability_assessments=assessments,
        risk=risk,
    )

    assert first == second
    assert first.plan_sha256 == second.plan_sha256


def test_planner_fails_closed_on_blocked_capability() -> None:
    spec = _build_spec(capabilities=("database", "payments"))
    assessments = resolve_capabilities(spec, blocked=frozenset({"payments"}))

    with pytest.raises(AppArchitecturePlanError, match="blocked capabilities"):
        plan_application_architecture(
            spec=spec,
            capability_assessments=assessments,
            risk=classify_risk(spec),
        )


def test_planner_rejects_assessment_spec_mismatch() -> None:
    spec = _build_spec(capabilities=("database", "files"))
    assessments = resolve_capabilities(spec)

    with pytest.raises(AppArchitecturePlanError, match="must match ProductSpec"):
        plan_application_architecture(
            spec=spec,
            capability_assessments=tuple(reversed(assessments)),
            risk=classify_risk(spec),
        )


def test_simple_windows_app_has_no_invented_backend_or_native_runtime() -> None:
    spec = _build_spec(capabilities=("local-view",), platforms=("windows",))
    assessments = resolve_capabilities(spec)
    plan = plan_application_architecture(
        spec=spec,
        capability_assessments=assessments,
        risk=classify_risk(spec),
    )

    assert plan.architecture_tier == "simple"
    assert plan.persistence_mode == "none"
    assert plan.realtime_mode == "none"
    assert plan.file_mode == "none"
    assert plan.native_mode == "none"
    assert plan.requires_backend_api is False
    assert plan.requires_migrations is False
