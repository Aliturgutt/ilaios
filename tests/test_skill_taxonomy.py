import json
import shutil
from pathlib import Path
from typing import cast

import pytest

from services.research_factory_skills import RESEARCH_FACTORY_SKILL_IDS
from services.security_methodology_skills import (
    AGENTIC_ACTION_AUDIT_SKILL_ID,
    DIFFERENTIAL_REVIEW_SKILL_ID,
    SECURITY_REVIEW_SKILL_ID,
    SUPPLY_CHAIN_AUDIT_SKILL_ID,
    THREAT_MODEL_SKILL_ID,
)
from services.skill_engineering_catalog import (
    SkillEngineeringCatalog,
    default_skill_engineering_root,
)
from services.skill_taxonomy import (
    SKILL_TAXONOMY,
    nodes_for_prefix,
    resolve_logical_skill,
    validate_skill_taxonomy,
)
from services.software_factory_skills import REQUIRED_SKILL_IDS
from services.web_factory_skills import (
    WEB_FACTORY_BROWSER_SKILL_IDS,
    WEB_FACTORY_NATIVE_SKILL_IDS,
)


def test_taxonomy_has_expected_top_level_families() -> None:
    validate_skill_taxonomy()
    assert {node.layer for node in SKILL_TAXONOMY} == {
        "skill-engineering",
        "factories",
        "capabilities",
        "assurance",
    }


def test_skill_engineering_lifecycle_is_complete() -> None:
    assert {node.path[-1] for node in nodes_for_prefix("skill-engineering")} == {
        "create",
        "lint",
        "validate",
        "security-scan",
        "evaluate",
        "benchmark",
        "regression",
        "compatibility",
        "promote",
    }


def test_factories_are_domain_skills_not_core_authorities() -> None:
    factory_families = {
        node.path[1] for node in nodes_for_prefix("factories") if len(node.path) == 3
    }
    assert factory_families == {"web", "software", "video", "research"}
    logical_ids = {node.logical_id for node in SKILL_TAXONOMY}
    assert "factories/video/model-routing" not in logical_ids
    assert "factories/video/model-fit" in logical_ids
    assert all("tool-gateway" not in logical_id for logical_id in logical_ids)
    assert all("policy-engine" not in logical_id for logical_id in logical_ids)


def test_web_taxonomy_maps_exactly_to_native_runtime_skills() -> None:
    web = nodes_for_prefix("factories/web")
    assert {node.path[-1] for node in web} == {
        "architecture",
        "design",
        "accessibility",
        "performance",
        "validation",
        "production-qa",
    }
    assert tuple(
        backing_skill_id
        for node in web
        for backing_skill_id in node.backing_skill_ids
    ) == WEB_FACTORY_NATIVE_SKILL_IDS
    logical_ids = {node.logical_id for node in web}
    assert "factories/web/build" not in logical_ids
    assert "factories/web/test" not in logical_ids


def test_video_taxonomy_maps_current_governed_runtime_skills() -> None:
    assert resolve_logical_skill("factories/video/director").backing_skill_ids == (
        "ilaios.skill.video.direction.cinematography",
    )
    assert resolve_logical_skill("factories/video/prompt").backing_skill_ids == (
        "ilaios.skill.video.prompt.compose",
    )
    assert resolve_logical_skill("factories/video/reference-assets").backing_skill_ids == (
        "ilaios.skill.video.reference-assets.inspect",
    )
    assert resolve_logical_skill("factories/video/model-fit").backing_skill_ids == (
        "ilaios.skill.video.model-fit.analyze",
    )
    assert resolve_logical_skill("factories/video/continuity").backing_skill_ids == (
        "ilaios.skill.video.continuity.track",
    )
    assert resolve_logical_skill("factories/video/generation").backing_skill_ids == (
        "ilaios.skill.video.generation.execute",
    )
    assert resolve_logical_skill("factories/video/edit").backing_skill_ids == (
        "ilaios.skill.video.edit.trim",
        "ilaios.skill.video.edit.concatenate",
        "ilaios.skill.video.edit.overlay",
        "ilaios.skill.video.edit.crop",
        "ilaios.skill.video.edit.scale",
        "ilaios.skill.video.edit.audio-mix",
    )
    assert resolve_logical_skill("factories/video/captions").backing_skill_ids == (
        "ilaios.skill.video.captions.export",
    )
    assert resolve_logical_skill("factories/video/composition").backing_skill_ids == (
        "ilaios.skill.video.composition.prepare",
    )
    assert resolve_logical_skill("factories/video/render").backing_skill_ids == (
        "ilaios.skill.video.render.execute",
    )
    assert resolve_logical_skill("factories/video/output-verify").backing_skill_ids == (
        "ilaios.skill.video.qa.evaluate",
    )


def test_research_taxonomy_maps_bounded_native_runtime_skills() -> None:
    research = nodes_for_prefix("factories/research")
    assert {node.path[-1] for node in research} == {
        "planning",
        "research",
        "source-validation",
        "contradiction-check",
        "citation-validation",
        "synthesis",
    }
    assert tuple(
        backing_skill_id
        for node in research
        for backing_skill_id in node.backing_skill_ids
    ) == RESEARCH_FACTORY_SKILL_IDS


def test_browser_is_shared_capability_with_bounded_runtime_backing() -> None:
    browser = nodes_for_prefix("capabilities/browser")
    assert {node.path[-1] for node in browser} == {
        "navigate",
        "inspect",
        "automate",
        "e2e",
        "visual-qa",
        "production-verify",
    }
    assert not nodes_for_prefix("factories/browser")
    assert WEB_FACTORY_BROWSER_SKILL_IDS == (
        "ilaios-browser",
        "ilaios-browser-automate",
        "ilaios-web-e2e",
        "ilaios-visual-qa",
        "ilaios-production-verification",
    )
    assert resolve_logical_skill("capabilities/browser/navigate").backing_skill_ids == (
        "ilaios-browser",
    )
    assert resolve_logical_skill("capabilities/browser/inspect").backing_skill_ids == (
        "ilaios-browser",
    )
    assert resolve_logical_skill("capabilities/browser/automate").backing_skill_ids == (
        "ilaios-browser-automate",
    )
    assert resolve_logical_skill("capabilities/browser/e2e").backing_skill_ids == (
        "ilaios-web-e2e",
    )
    assert resolve_logical_skill("capabilities/browser/visual-qa").backing_skill_ids == (
        "ilaios-visual-qa",
    )
    assert resolve_logical_skill(
        "capabilities/browser/production-verify"
    ).backing_skill_ids == ("ilaios-production-verification",)


def test_software_logical_nodes_only_map_to_existing_runtime_skills() -> None:
    existing = set(REQUIRED_SKILL_IDS)
    software = nodes_for_prefix("factories/software")
    assert software
    assert all(set(node.backing_skill_ids).issubset(existing) for node in software)
    assert resolve_logical_skill("factories/software/review").backing_skill_ids == (
        "sf-code-review",
    )


def test_assurance_maps_native_security_and_existing_software_gates() -> None:
    assurance = nodes_for_prefix("assurance")
    assert {node.path[-1] for node in assurance} == {
        "security-review",
        "differential-review",
        "agentic-action-audit",
        "threat-model",
        "supply-chain-audit",
        "dependency-audit",
        "release-readiness",
    }
    assert resolve_logical_skill("assurance/security-review").backing_skill_ids == (
        SECURITY_REVIEW_SKILL_ID,
        "sf-security-review",
    )
    assert resolve_logical_skill("assurance/differential-review").backing_skill_ids == (
        DIFFERENTIAL_REVIEW_SKILL_ID,
    )
    assert resolve_logical_skill("assurance/agentic-action-audit").backing_skill_ids == (
        AGENTIC_ACTION_AUDIT_SKILL_ID,
    )
    assert resolve_logical_skill("assurance/threat-model").backing_skill_ids == (
        THREAT_MODEL_SKILL_ID,
    )
    assert resolve_logical_skill("assurance/supply-chain-audit").backing_skill_ids == (
        SUPPLY_CHAIN_AUDIT_SKILL_ID,
        "sf-dependency-governance",
        "sf-license-provenance",
    )
    assert resolve_logical_skill("assurance/release-readiness").backing_skill_ids == (
        "sf-release-readiness",
    )


def test_skill_create_package_is_fail_closed_and_reviewed() -> None:
    repository_root = Path(__file__).resolve().parents[1]
    catalog = SkillEngineeringCatalog(default_skill_engineering_root(repository_root))
    package = catalog.resolve("skill-create")
    assert package.logical_id == "skill-engineering/create"
    assert package.maturity == "IMPLEMENTED"
    assert package.required_capabilities == frozenset(
        {"repository_intelligence", "governance", "evidence_chain"}
    )
    assert package.allowed_tools == frozenset(
        {"repository_intelligence", "governance", "evidence_chain"}
    )
    assert package.independent_review_required is True
    assert package.eval_kinds == frozenset(
        {"GOLDEN", "NEGATIVE", "ADVERSARIAL", "MALFORMED", "REGRESSION"}
    )


def test_skill_engineering_catalog_rejects_cross_layer_identity(tmp_path: Path) -> None:
    repository_root = Path(__file__).resolve().parents[1]
    source = default_skill_engineering_root(repository_root) / "skill-create"
    copied_root = tmp_path / "skills"
    copied = copied_root / "skill-create"
    shutil.copytree(source, copied)

    manifest_path = copied / "manifest.yaml"
    raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest = cast(dict[str, object], raw)
    manifest["logical_id"] = "assurance/security-review"
    manifest_path.write_text(
        json.dumps(manifest, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="logical_id must stay in skill-engineering"):
        SkillEngineeringCatalog(copied_root)


def test_skill_engineering_catalog_rejects_source_verified_claim(tmp_path: Path) -> None:
    repository_root = Path(__file__).resolve().parents[1]
    source = default_skill_engineering_root(repository_root) / "skill-create"
    copied_root = tmp_path / "skills"
    copied = copied_root / "skill-create"
    shutil.copytree(source, copied)

    manifest_path = copied / "manifest.yaml"
    raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest = cast(dict[str, object], raw)
    manifest["maturity"] = "VERIFIED"
    manifest_path.write_text(
        json.dumps(manifest, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="source maturity cannot claim tested or verified",
    ):
        SkillEngineeringCatalog(copied_root)
