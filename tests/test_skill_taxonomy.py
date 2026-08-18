import json
import shutil
from pathlib import Path
from typing import cast

import pytest

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
    assert all("tool-gateway" not in logical_id for logical_id in logical_ids)
    assert all("policy-engine" not in logical_id for logical_id in logical_ids)


def test_browser_is_shared_capability_not_factory() -> None:
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


def test_software_logical_nodes_only_map_to_existing_runtime_skills() -> None:
    existing = set(REQUIRED_SKILL_IDS)
    software = nodes_for_prefix("factories/software")
    assert software
    assert all(set(node.backing_skill_ids).issubset(existing) for node in software)
    assert resolve_logical_skill("factories/software/review").backing_skill_ids == (
        "sf-code-review",
    )


def test_assurance_is_cross_cutting_and_reuses_existing_evidence_gates() -> None:
    assurance = nodes_for_prefix("assurance")
    assert {node.path[-1] for node in assurance} == {
        "security-review",
        "differential-review",
        "threat-model",
        "supply-chain-audit",
        "dependency-audit",
        "release-readiness",
    }
    assert resolve_logical_skill("assurance/release-readiness").backing_skill_ids == (
        "sf-release-readiness",
    )


def test_skill_create_package_is_fail_closed_and_reviewed() -> None:
    repository_root = Path(__file__).resolve().parents[1]
    catalog = SkillEngineeringCatalog(
        default_skill_engineering_root(repository_root)
    )
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
        {"GOLDEN", "NEGATIVE", "ADVERSARIAL", "REGRESSION"}
    )


def test_skill_engineering_catalog_rejects_cross_layer_identity(
    tmp_path: Path,
) -> None:
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

    with pytest.raises(
        ValueError,
        match="logical_id must stay in skill-engineering",
    ):
        SkillEngineeringCatalog(copied_root)


def test_skill_engineering_catalog_rejects_source_verified_claim(
    tmp_path: Path,
) -> None:
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
