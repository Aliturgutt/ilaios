"""Completion proofs for the canonical ILAIOS Skill Engineering source packages."""
from __future__ import annotations

from pathlib import Path

from services.skill_engineering_catalog import (
    SkillEngineeringCatalog,
    default_skill_engineering_root,
)
from services.skill_taxonomy import resolve_logical_skill


REQUIRED_SOURCE_PACKAGES = {
    "skill-create": "skill-engineering/create",
    "skill-lint": "skill-engineering/lint",
    "skill-validate": "skill-engineering/validate",
    "skill-security-scan": "skill-engineering/security-scan",
    "skill-evaluate": "skill-engineering/evaluate",
    "skill-benchmark": "skill-engineering/benchmark",
    "skill-regression": "skill-engineering/regression",
    "skill-compatibility": "skill-engineering/compatibility",
    "skill-promote": "skill-engineering/promote",
}

REQUIRED_RUNTIME_BACKINGS = {
    "skill-create": "skill-engineering/create",
    "skill-validate": "skill-engineering/validate",
    "skill-evaluate": "skill-engineering/evaluate",
    "skill-benchmark": "skill-engineering/benchmark",
    "skill-regression": "skill-engineering/regression",
}

SOURCE_ONLY_PACKAGES = {
    skill_id: logical_id
    for skill_id, logical_id in REQUIRED_SOURCE_PACKAGES.items()
    if skill_id not in REQUIRED_RUNTIME_BACKINGS
}


def test_complete_skill_engineering_lifecycle_is_catalog_backed() -> None:
    repository_root = Path(__file__).resolve().parents[1]
    catalog = SkillEngineeringCatalog(default_skill_engineering_root(repository_root))
    assert set(catalog.skill_ids) == set(REQUIRED_SOURCE_PACKAGES)
    for skill_id, logical_id in REQUIRED_SOURCE_PACKAGES.items():
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


def test_new_source_packages_do_not_gain_runtime_authority_implicitly() -> None:
    for skill_id, logical_id in SOURCE_ONLY_PACKAGES.items():
        node = resolve_logical_skill(logical_id)
        assert node.layer == "skill-engineering"
        assert node.backing_skill_ids == (), skill_id


def test_source_and_runtime_truth_are_not_conflated() -> None:
    assert len(REQUIRED_SOURCE_PACKAGES) == 9
    assert len(REQUIRED_RUNTIME_BACKINGS) == 5
    assert len(SOURCE_ONLY_PACKAGES) == 4
