import pytest

from services.integrations.video_prompting_skills import GovernedVideoPromptingSkills
from services.integrations.video_skill_governance import (
    ALL_VIDEO_SKILLS,
    approve_video_skills,
)
from services.runtime.routing import AgentProfile, RuntimeError, SkillRegistry
from src.video_automation.video_prompting_skills import DirectorBrief


def _brief() -> DirectorBrief:
    return DirectorBrief(
        "brief-1",
        "reveal the product",
        "a brushed-metal device",
        "a neutral studio",
        ("the device rotates slowly", "the device settles facing camera"),
        "slow dolly-in",
        "soft neutral key light",
        "faint room tone",
        "the device is centered and still",
        ("same product geometry",),
    )


def _agent() -> AgentProfile:
    authorities = frozenset(
        permission for skill in ALL_VIDEO_SKILLS for permission in skill.permissions
    )
    return AgentProfile("video-worker", authorities)


def test_prompting_adapter_fails_closed_before_skill_approval() -> None:
    adapter = GovernedVideoPromptingSkills(SkillRegistry(), _agent())
    with pytest.raises(RuntimeError, match="not approved"):
        adapter.direct(_brief())


def test_prompting_adapter_executes_after_canonical_governance() -> None:
    registry = SkillRegistry()
    approve_video_skills(registry)
    result = GovernedVideoPromptingSkills(registry, _agent()).direct(_brief())
    assert result.brief_id == "brief-1"
    assert result.continuity_invariants == ("same product geometry",)
