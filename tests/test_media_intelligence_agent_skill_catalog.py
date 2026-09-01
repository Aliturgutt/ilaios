from pathlib import Path

from services.media_intelligence_agent_execution import media_intelligence_binding_for
from services.media_intelligence_agent_skill_catalog import (
    MEDIA_INTELLIGENCE_FIRST_PARTY_SKILLS,
    validate_media_intelligence_skill_catalog,
)
from services.research_factory_skills import (
    RESEARCH_FACTORY_SKILLS,
    default_research_skills_root,
    validate_research_factory_skills,
)

ROOT = Path(__file__).resolve().parents[1]


def test_first_party_catalog_is_nine_unique_proposal_skills() -> None:
    validate_media_intelligence_skill_catalog()
    ids = [item.skill_id for item in MEDIA_INTELLIGENCE_FIRST_PARTY_SKILLS]
    owners = [item.owner_agent_id for item in MEDIA_INTELLIGENCE_FIRST_PARTY_SKILLS]
    assert len(ids) == len(set(ids)) == 9
    assert len(owners) == len(set(owners)) == 9
    for item in MEDIA_INTELLIGENCE_FIRST_PARTY_SKILLS:
        binding = media_intelligence_binding_for(item.owner_agent_id)
        assert binding.primary_skill_id == item.skill_id
        assert binding.capability == item.capability
        assert item.content().strip()


def test_catalog_reuses_existing_research_factory_packages() -> None:
    root = default_research_skills_root(ROOT)
    validate_research_factory_skills(root)
    by_id = {item.skill_id: item for item in RESEARCH_FACTORY_SKILLS}
    assert by_id["ilaios-research"].owner_agent_id == "ilaios.agent.intelligence.research.v1"
    assert by_id["ilaios-source-validation"].owner_agent_id == (
        "ilaios.agent.intelligence.fact-check.v1"
    )
    assert by_id["ilaios-research-synthesis"].owner_agent_id == (
        "ilaios.agent.intelligence.knowledge.v1"
    )


def test_media_skill_instructions_preserve_side_effect_boundaries() -> None:
    text = "\n".join(
        item.instructions for item in MEDIA_INTELLIGENCE_FIRST_PARTY_SKILLS
    )
    assert "no direct provider.request" in text.lower()
    assert "direct social.publish authority" in text.lower()
    assert "do not acquire external data" in text.lower()
