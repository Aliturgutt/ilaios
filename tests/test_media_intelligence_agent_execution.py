from services.agent_registry import CANONICAL_AGENT_REGISTRY, registration_for
from services.media_intelligence_agent_execution import (
    MEDIA_INTELLIGENCE_AGENT_BINDINGS,
    MEDIA_INTELLIGENCE_GOVERNED_AI_CAPABILITIES,
    media_intelligence_binding_for,
)


def test_media_intelligence_bindings_cover_exact_canonical_8_plus_4() -> None:
    expected = {
        item.manifest.agent_id
        for item in CANONICAL_AGENT_REGISTRY
        if item.manifest.team in {"media", "intelligence"}
    }
    assert len(expected) == 12
    assert {item.agent_id for item in MEDIA_INTELLIGENCE_AGENT_BINDINGS} == expected
    assert len(MEDIA_INTELLIGENCE_GOVERNED_AI_CAPABILITIES) == 12


def test_bindings_never_exceed_manifest_capability_or_permission() -> None:
    for binding in MEDIA_INTELLIGENCE_AGENT_BINDINGS:
        manifest = registration_for(binding.agent_id).manifest
        assert binding.capability in manifest.capabilities
        assert binding.permission in manifest.permissions
        assert binding.execution_mode == "governed-ai"


def test_media_generation_and_publishing_remain_proposal_only() -> None:
    generation = media_intelligence_binding_for("ilaios.agent.media.generation.v1")
    publishing = media_intelligence_binding_for("ilaios.agent.media.publishing.v1")
    assert generation.capability == "media.generate"
    assert generation.permission == "shot-plan.read"
    assert generation.primary_skill_id.endswith("generation-proposal.v1")
    assert publishing.capability == "social.publish-propose"
    assert publishing.permission == "artifact.read"
    assert publishing.primary_skill_id.endswith("publishing-proposal.v1")
    assert "social.publish" not in MEDIA_INTELLIGENCE_GOVERNED_AI_CAPABILITIES


def test_intelligence_reuses_research_primary_skills_and_adds_data_analyst() -> None:
    assert media_intelligence_binding_for(
        "ilaios.agent.intelligence.research.v1"
    ).primary_skill_id == "ilaios-research"
    assert media_intelligence_binding_for(
        "ilaios.agent.intelligence.fact-check.v1"
    ).primary_skill_id == "ilaios-source-validation"
    assert media_intelligence_binding_for(
        "ilaios.agent.intelligence.knowledge.v1"
    ).primary_skill_id == "ilaios-research-synthesis"
    assert media_intelligence_binding_for(
        "ilaios.agent.intelligence.data-analyst.v1"
    ).primary_skill_id == "ilaios.skill.intelligence.data-analyst.v1"
