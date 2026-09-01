from services.agent_registry import INDEPENDENT_VERIFIER_ID
from services.operations_meta_agent_execution import (
    OPERATIONS_META_AGENT_BINDINGS,
    operations_meta_binding_for,
)
from services.operations_meta_agent_skill_catalog import (
    OPERATIONS_META_FIRST_PARTY_SKILLS,
    validate_operations_meta_skill_catalog,
)
from services.p0_agent_execution import P0_AGENT_BINDINGS


def test_operations_meta_provider_skills_are_unique_and_exactly_seven() -> None:
    validate_operations_meta_skill_catalog()
    ids = {item.skill_id for item in OPERATIONS_META_FIRST_PARTY_SKILLS}
    owners = {item.owner_agent_id for item in OPERATIONS_META_FIRST_PARTY_SKILLS}
    assert len(ids) == 7
    assert len(owners) == 7
    assert INDEPENDENT_VERIFIER_ID not in owners


def test_operations_meta_provider_skills_do_not_reuse_p0_primary_skill_ids() -> None:
    p0_skill_ids = {binding.primary_skill_id for binding in P0_AGENT_BINDINGS}
    operations_meta_ids = {
        binding.primary_skill_id
        for binding in OPERATIONS_META_AGENT_BINDINGS
        if binding.execution_mode == "governed-ai"
    }
    assert operations_meta_ids.isdisjoint(p0_skill_ids)


def test_operations_meta_skill_authority_matches_each_owner_manifest() -> None:
    for item in OPERATIONS_META_FIRST_PARTY_SKILLS:
        binding = operations_meta_binding_for(item.owner_agent_id)
        assert binding.primary_skill_id == item.skill_id
        assert binding.capability == item.capability


def test_independent_verifier_reuses_only_canonical_verifier_skill() -> None:
    verifier = operations_meta_binding_for(INDEPENDENT_VERIFIER_ID)
    assert verifier.primary_skill_id == "ilaios.skill.meta.independent-verification.v1"
    assert verifier.execution_mode == "independent-verification"
