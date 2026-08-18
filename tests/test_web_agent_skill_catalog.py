from pathlib import Path

from services.web_agent_execution import WEB_AGENT_BINDINGS
from services.web_agent_skill_catalog import WEB_FIRST_PARTY_AGENT_SKILLS

ROOT = Path(__file__).resolve().parents[1]


def test_web_proposal_skill_catalog_matches_five_provider_backed_bindings() -> None:
    expected = {
        binding.primary_skill_id
        for binding in WEB_AGENT_BINDINGS
        if binding.execution_mode == "governed-ai"
    }
    assert {skill.skill_id for skill in WEB_FIRST_PARTY_AGENT_SKILLS} == expected
    assert len(WEB_FIRST_PARTY_AGENT_SKILLS) == 5
    assert len({skill.owner_agent_id for skill in WEB_FIRST_PARTY_AGENT_SKILLS}) == 5


def test_web_agent_skills_are_bounded_proposal_instructions() -> None:
    for skill in WEB_FIRST_PARTY_AGENT_SKILLS:
        assert skill.instructions.strip()
        assert skill.capability.startswith("web.")
        assert skill.owner_agent_id.startswith("ilaios.agent.web.")
        content = skill.content()
        lower = content.lower()
        assert content.endswith(b"\n")
        assert b"do not" in lower or b"never" in lower


def test_browserqa_is_not_redeclared_as_provider_backed_skill() -> None:
    assert all(
        skill.owner_agent_id != "ilaios.agent.web.browser-qa.v1"
        for skill in WEB_FIRST_PARTY_AGENT_SKILLS
    )
    assert (ROOT / "tools" / "web-factory" / "browser-skills" / "ilaios-web-e2e").is_dir()
