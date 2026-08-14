import pytest

from services.integrations.knowledge_rag import (
    approve_knowledge_skills,
    validate_knowledge_skill,
)
from services.runtime.routing import AgentProfile, RuntimeError, SkillArtifact, SkillRegistry
from src.knowledge_rag.skills import KNOWLEDGE_SKILLS, knowledge_skill


def test_all_knowledge_skills_validate_in_one_canonical_registry() -> None:
    registry = SkillRegistry()
    approve_knowledge_skills(registry)
    agent = AgentProfile(
        agent_id="ilaios.agent.intelligence.knowledge.v1",
        authorities=frozenset({"knowledge:retrieve", "knowledge:provenance"}),
    )

    validated = tuple(
        validate_knowledge_skill(registry, agent, manifest.skill_id)
        for manifest in KNOWLEDGE_SKILLS
    )

    assert validated == KNOWLEDGE_SKILLS
    assert len({manifest.skill_id for manifest in validated}) == len(validated)


def test_knowledge_skill_cannot_expand_agent_authority() -> None:
    registry = SkillRegistry()
    approve_knowledge_skills(registry)
    agent = AgentProfile(
        agent_id="ilaios.agent.intelligence.readonly.v1",
        authorities=frozenset({"knowledge:provenance"}),
    )

    with pytest.raises(RuntimeError, match="expand agent authority"):
        validate_knowledge_skill(
            registry, agent, "ilaios.skill.knowledge.retrieve.authorized"
        )


def test_tampered_native_skill_digest_fails_closed() -> None:
    registry = SkillRegistry()
    approve_knowledge_skills(registry)
    manifest = knowledge_skill("ilaios.skill.knowledge.retrieve.authorized")
    agent = AgentProfile(
        agent_id="ilaios.agent.intelligence.knowledge.v1",
        authorities=frozenset({"knowledge:retrieve"}),
    )
    tampered = SkillArtifact(
        skill_id=manifest.skill_id,
        content=manifest.content + b"tampered",
        requested_authorities=manifest.authorities,
        owner=manifest.owner,
        license_id=manifest.license_id,
        source_provenance=manifest.source_provenance,
    )

    with pytest.raises(RuntimeError, match="digest"):
        registry.validate(tampered, agent)


def test_unknown_knowledge_skill_is_rejected() -> None:
    registry = SkillRegistry()
    approve_knowledge_skills(registry)
    agent = AgentProfile(
        agent_id="ilaios.agent.intelligence.knowledge.v1",
        authorities=frozenset({"knowledge:retrieve", "knowledge:provenance"}),
    )

    with pytest.raises(ValueError, match="unknown Knowledge/RAG skill"):
        validate_knowledge_skill(registry, agent, "ilaios.skill.knowledge.admin")
