"""Completion proofs for the canonical ILAIOS Skill Engineering source packages."""
from __future__ import annotations

from pathlib import Path

from services.skill_engineering_catalog import (
    SkillEngineeringCatalog,
    default_skill_engineering_root,
)
from services.skill_taxonomy import resolve_logical_skill


REQUIRED_RUNTIME_BACKINGS = {
    "skill-create": "skill-engineering/create",
    "skill-validate": "skill-engineering/validate",
    "skill-evaluate": "skill-engineering/evaluate",
    "skill-benchmark": "skill-engineering/benchmark",
    "skill-regression": "skill-engineering/regression",
}


def test_core_skill_engineering_packages_are_catalog_backed() -> None:
    repository_root = Path(__file__).resolve().parents[1]
    catalog = SkillEngineeringCatalog(default_skill_engineering_root(repository_root))
    assert REQUIRED_RUNTIME_BACKINGS.keys() <= set(catalog.skill_ids)
    for skill_id, logical_id in REQUIRED_RUNTIME_BACKINGS.items():
        package = catalog.resolve(skill_id)
        assert package.logical_id == logical_id
        assert package.maturity == "IMPLEMENTED"
        assert package.independent_review_required is True
        assert package.eval_kinds == {
            "GOLDEN",
            "NEGATIVE",
            "ADVERSARIAL",
            "MALFORMED",
            "REGRESSION",
        }


def test_admitted_source_packages_map_to_exact_runtime_backings() -> None:
    for skill_id, logical_id in REQUIRED_RUNTIME_BACKINGS.items():
        node = resolve_logical_skill(logical_id)
        assert node.layer == "skill-engineering"
        assert node.backing_skill_ids == (skill_id,)


def test_unimplemented_lifecycle_nodes_still_claim_no_runtime_backing() -> None:
    for logical_id in (
        "skill-engineering/lint",
        "skill-engineering/security-scan",
        "skill-engineering/compatibility",
        "skill-engineering/promote",
    ):
        node = resolve_logical_skill(logical_id)
        assert node.layer == "skill-engineering"
        assert node.backing_skill_ids == ()
