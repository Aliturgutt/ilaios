"""Completion proofs for the canonical ILAIOS Skill Engineering source packages."""
from __future__ import annotations

from pathlib import Path

from services.skill_engineering_catalog import (
    SkillEngineeringCatalog,
    default_skill_engineering_root,
)
from services.skill_taxonomy import resolve_logical_skill


def test_core_skill_engineering_packages_are_catalog_backed() -> None:
    repository_root = Path(__file__).resolve().parents[1]
    catalog = SkillEngineeringCatalog(default_skill_engineering_root(repository_root))
    required = {
        "skill-create": "skill-engineering/create",
        "skill-validate": "skill-engineering/validate",
        "skill-evaluate": "skill-engineering/evaluate",
        "skill-benchmark": "skill-engineering/benchmark",
        "skill-regression": "skill-engineering/regression",
    }
    assert required.keys() <= set(catalog.skill_ids)
    for skill_id, logical_id in required.items():
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
        assert resolve_logical_skill(logical_id).backing_skill_ids == ()


def test_source_packages_do_not_claim_runtime_mapping() -> None:
    for logical_id in (
        "skill-engineering/create",
        "skill-engineering/validate",
        "skill-engineering/evaluate",
        "skill-engineering/benchmark",
        "skill-engineering/regression",
    ):
        node = resolve_logical_skill(logical_id)
        assert node.layer == "skill-engineering"
        assert node.backing_skill_ids == ()
