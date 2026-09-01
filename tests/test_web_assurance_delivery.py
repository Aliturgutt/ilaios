"""Closure tests for Web source assurance, repair and delivery boundaries."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import cast

import pytest

from services.control_plane import ControlPlane, ControlPlaneConfig
from services.control_plane.workflows import WorkflowStore, WorkflowStoreConfig
from services.evidence import EvidenceStore
from services.execution_adapters import register_web_runtime
from services.execution_coordinator import ExecutionCoordinator, ExecutionState
from services.governance import GovernedRuntimeGateway
from services.integrations import DeterministicLocalVideoRuntime, DurableVideoProductRuntime
from services.integrations.web_assurance import WebAssuranceError, certify_with_bounded_repair
from services.integrations.web_delivery import LocalWebDeploymentAdapter, tree_sha256
from services.integrations.web_factory import WebsiteSpec
from services.integrations.web_product_runtime_recovery import RecoverableWebProductRuntime
from services.integrations.web_project import materialize_next_project
from services.runtime import DurableGrantPolicy, DurableWorkerScheduler, GovernedRuntime


def _spec(*, features: tuple[str, ...] = ("contact-form",)) -> WebsiteSpec:
    return WebsiteSpec(
        site_id="site-assurance-test",
        business_name="Northstar Legal",
        business_category="law firm",
        audience="corporate and enterprise decision makers",
        primary_goal="present a credible finished website",
        conversion_objective="contact conversion",
        locales=("en", "tr"),
        pages=("home", "expertise", "about", "contact"),
        features=features,
        brand_personality=("premium", "confident", "clear"),
        trust_requirement="high",
        visual_asset_availability="standard",
        information_density="medium",
    )


def test_design_strategy_materializes_into_generated_react_source(tmp_path: Path) -> None:
    strategy = {
        "primary_composition": "minimal-institutional",
        "secondary_compositions": ("evidence-trust", "structured-comparison"),
        "type_behavior": "editorial-readable",
    }
    source = materialize_next_project(
        _spec(), strategy, tmp_path / "source-projects"
    )
    root = Path(source.root_path)
    home = (root / "app/en/page.tsx").read_text(encoding="utf-8")
    shell = (root / "components/PageShell.tsx").read_text(encoding="utf-8")
    css = (root / "app/globals.css").read_text(encoding="utf-8")
    assert '"primaryComposition": "minimal-institutional"' in home
    assert '"evidence-trust"' in home
    assert "data-composition={props.primaryComposition}" in shell
    assert "ContextSections" in shell
    assert ".composition-minimal-institutional" in css
    assert ".composition-technical-flow" in css
    assert ".composition-visual-portfolio" in css


def test_source_assurance_repairs_into_new_content_addressed_project(tmp_path: Path) -> None:
    source = materialize_next_project(
        _spec(features=("contact-form", "content", "newsletter", "search")),
        {
            "primary_composition": "minimal-institutional",
            "secondary_compositions": ("evidence-trust", "structured-comparison"),
        },
        tmp_path / "source-projects",
    )
    original = Path(source.root_path)
    assert not (original / "app/robots.ts").exists()

    receipt = certify_with_bounded_repair(original, max_attempts=2)

    assert receipt["passed"] is True
    assert receipt["repair_attempt_count"] == 1
    certified = Path(str(receipt["certified_project_path"]))
    assert certified != original
    assert certified.is_dir()
    assert not (original / "app/robots.ts").exists(), (
        "original content-addressed source must stay immutable"
    )
    assert (certified / "app/robots.ts").is_file()
    assert (certified / "app/sitemap.ts").is_file()
    assert (certified / "app/api/contact/route.ts").is_file()
    assert (certified / "app/api/newsletter/route.ts").is_file()
    assert (certified / "app/en/insights/page.tsx").is_file()
    assert (certified / "app/tr/search/page.tsx").is_file()
    assert tree_sha256(certified) == receipt["source_project_digest"]

    routes = cast(list[str], receipt["certified_routes"])
    accessibility = cast(dict[str, object], receipt["accessibility"])
    seo = cast(dict[str, object], receipt["seo"])
    security = cast(dict[str, object], receipt["security"])
    performance = cast(dict[str, object], receipt["performance"])
    design = cast(dict[str, object], receipt["design"])
    assert "/en/insights" in routes
    assert "/tr/search" in routes
    assert accessibility["status"] == "PASS"
    assert seo["status"] == "PASS"
    assert security["status"] == "PASS"
    assert performance["status"] == "PASS"
    assert design["status"] == "PASS"


def test_source_assurance_fails_closed_on_unrepairable_unsafe_source(tmp_path: Path) -> None:
    source = materialize_next_project(
        _spec(),
        {
            "primary_composition": "minimal-institutional",
            "secondary_compositions": ("evidence-trust",),
        },
        tmp_path / "source-projects",
    )
    root = Path(source.root_path)
    shell = root / "components/PageShell.tsx"
    shell.write_text(
        shell.read_text(encoding="utf-8")
        + '\nconst unsafe = "javascript:alert(1)";\n',
        encoding="utf-8",
    )

    with pytest.raises(WebAssuranceError, match="bounded assurance"):
        certify_with_bounded_repair(root, max_attempts=2)


def test_local_deployment_is_content_bound_and_rolls_back(tmp_path: Path) -> None:
    source = tmp_path / "project"
    source.mkdir()
    (source / "index.txt").write_text("version-one", encoding="utf-8")
    adapter = LocalWebDeploymentAdapter(tmp_path / "deployments")
    sha = "a" * 40

    first = adapter.deploy(source, source_commit_sha=sha)
    assert first.health == "HEALTHY_LOCAL_PRODUCTION_LIKE"
    assert first.public_production_proven is False
    assert first.rollback_reference is None

    (source / "index.txt").write_text("version-two", encoding="utf-8")
    second = adapter.deploy(source, source_commit_sha=sha)
    assert second.rollback_reference == first.deployment_id
    assert second.deployment_id != first.deployment_id

    rollback = adapter.rollback(first.deployment_id, source_commit_sha=sha)
    assert rollback.health == "HEALTHY_LOCAL_ROLLBACK"
    assert rollback.deployment_id == first.deployment_id
    current = adapter.current()
    assert current is not None
    assert current["deployment_id"] == first.deployment_id


def _coordinator(
    tmp_path: Path,
) -> tuple[ExecutionCoordinator, RecoverableWebProductRuntime]:
    state = tmp_path / "state.sqlite3"
    control = ControlPlane(ControlPlaneConfig(state, "token"))
    workflows = WorkflowStore(WorkflowStoreConfig(state))
    scheduler = DurableWorkerScheduler(state, lease_duration=timedelta(seconds=30))
    grants = DurableGrantPolicy(state)
    evidence = EvidenceStore(tmp_path / "evidence")
    governance = GovernedRuntimeGateway(
        tmp_path / "governance.sqlite3",
        GovernedRuntime(state),
        hard_cap_minor=100,
    )
    video = DeterministicLocalVideoRuntime(
        tmp_path / "video", grants, governance, evidence
    )
    video_product = DurableVideoProductRuntime(
        tmp_path / "video-product.sqlite3",
        control,
        workflows,
        scheduler,
        grants,
        governance,
        video,
    )
    web = RecoverableWebProductRuntime(
        tmp_path / "web-product.sqlite3",
        control,
        grants,
        governance,
        tmp_path / "web",
    )
    coordinator = ExecutionCoordinator(
        tmp_path / "coordinator.sqlite3",
        control,
        governance,
        grants,
        video_product,
        evidence,
    )
    register_web_runtime(coordinator, web)
    return coordinator, web


def test_recoverable_runtime_accepts_bounded_content_newsletter_and_search(
    tmp_path: Path,
) -> None:
    coordinator, _ = _coordinator(tmp_path)
    now = datetime(2026, 8, 16, 16, 0, tzinfo=timezone.utc)
    prepared = coordinator.prepare(
        "web-rich-bounded",
        "Build a premium bilingual Turkish/English website for a corporate law firm "
        "with a blog, articles, newsletter and site search",
        token="token",
        principal_id="oidc|web@example.test",
        tenant_id="tenant/web",
        now=now,
    )
    assert prepared["execution_status"] == ExecutionState.ADMITTED.value
    manifest = coordinator.resume(
        "web-rich-bounded",
        token="token",
        now=now + timedelta(seconds=1),
        principal_id="oidc|web@example.test",
        tenant_id="tenant/web",
    )

    assert manifest["accepted"] is True
    features = cast(list[str] | tuple[str, ...], manifest["functional_features"])
    assert set(features) == {
        "contact-form",
        "content",
        "newsletter",
        "search",
    }
    assurance = cast(dict[str, object], manifest["source_assurance"])
    build_result = cast(dict[str, object], manifest["build_result"])
    accessibility = cast(dict[str, object], manifest["accessibility_evidence"])
    seo = cast(dict[str, object], manifest["seo_evidence"])
    security = cast(dict[str, object], manifest["security_evidence"])
    performance = cast(dict[str, object], manifest["performance_evidence"])
    design = cast(dict[str, object], manifest["design_acceptance"])
    routes = cast(list[str], manifest["certified_routes"])
    assert assurance["passed"] is True
    assert assurance["repair_attempt_count"] == 1
    assert build_result["status"] == "SOURCE_CERTIFIED"
    assert accessibility["status"] == "PASS"
    assert seo["status"] == "PASS"
    assert security["status"] == "PASS"
    assert performance["status"] == "PASS"
    assert design["status"] == "PASS"
    assert "/en/insights" in routes
    assert "/tr/search" in routes
