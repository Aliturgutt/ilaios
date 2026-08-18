"""Regression proofs for the ILAIOS-native skill boundary."""

import pytest

from services.skill_registry import (
    SKILLS,
    SkillDefinition,
    SkillRegistryError,
    skill,
    skills_for_family,
    validate_skill_registry,
)


def test_native_skill_ids_are_unique_and_vendor_neutral() -> None:
    validate_skill_registry()
    assert SKILLS
    assert all(item.skill_id.startswith("ilaios.skill.") for item in SKILLS)
    forbidden = ("openai", "anthropic", "claude", "gemini", "seedance", "vercel")
    assert all(
        token not in item.skill_id.casefold()
        for item in SKILLS
        for token in forbidden
    )


def test_every_registered_skill_preserves_evidence_authority() -> None:
    for item in SKILLS:
        assert "ilaios.capability.evidence-audit" in item.capability_dependencies


def test_executable_and_assurance_skills_preserve_policy_governance() -> None:
    for item in SKILLS:
        if item.kind in {"factory", "capability", "assurance"}:
            assert "ilaios.capability.policy-governance" in item.capability_dependencies


def test_browser_production_verification_is_high_risk_and_approval_bounded() -> None:
    definition = skill("ilaios.skill.capability.browser.production-verify")
    assert definition.risk_class == "high"
    assert definition.requires_approval is True


def test_family_lookup_does_not_create_parallel_registry_state() -> None:
    assert skills_for_family("web") == (
        skill("ilaios.skill.factory.web.production-qa"),
    )


def test_registry_fails_closed_on_unknown_capability_dependency() -> None:
    invalid = SkillDefinition(
        "ilaios.skill.factory.web.invalid",
        "factory",
        "web",
        frozenset(
            {
                "ilaios.capability.policy-governance",
                "ilaios.capability.evidence-audit",
                "ilaios.capability.does-not-exist",
            }
        ),
        "high",
    )
    with pytest.raises(SkillRegistryError, match="unknown capability dependencies"):
        validate_skill_registry((invalid,))
