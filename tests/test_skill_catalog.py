"""Repository-backed ILAIOS-native skill catalog proofs."""

from pathlib import Path

import pytest

from services.skill_catalog import (
    NATIVE_SKILLS,
    NativeSkillDefinition,
    SkillCatalogError,
    native_skill,
    validate_skill_catalog,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_native_skill_catalog_is_unique_and_repository_backed() -> None:
    validate_skill_catalog(REPO_ROOT)
    assert len(NATIVE_SKILLS) == 5
    assert {item.skill_id for item in NATIVE_SKILLS} == {
        "ilaios.skill.engineering.create",
        "ilaios.skill.engineering.validate",
        "ilaios.skill.engineering.evaluate",
        "ilaios.skill.engineering.benchmark",
        "ilaios.skill.engineering.regression",
    }


def test_native_skill_lookup_returns_canonical_package() -> None:
    definition = native_skill("ilaios.skill.engineering.evaluate")
    assert definition.package_path == "skills/skill-engineering/evaluate"
    assert definition.capability_id == "ilaios.capability.evidence-audit"


def test_native_skill_definition_rejects_noncanonical_identity() -> None:
    with pytest.raises(SkillCatalogError, match="namespace"):
        NativeSkillDefinition(
            "external.skill.evaluate",
            "skills/skill-engineering/evaluate",
            "ilaios.capability.evidence-audit",
        )
