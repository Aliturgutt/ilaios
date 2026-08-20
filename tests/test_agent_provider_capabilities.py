import pytest

from services.agent_provider_capabilities import (
    AGENT_GOVERNED_AI_CAPABILITIES,
    P0_GOVERNED_AI_CAPABILITIES,
    SKILL_ENGINEERING_GOVERNED_AI_CAPABILITIES,
)
from services.media_intelligence_agent_execution import (
    MEDIA_INTELLIGENCE_GOVERNED_AI_CAPABILITIES,
)
from services.web_agent_execution import WEB_GOVERNED_AI_CAPABILITIES


def test_provider_capability_union_is_exactly_p0_p1_and_skill_engineering() -> None:
    assert len(P0_GOVERNED_AI_CAPABILITIES) == 16
    assert len(WEB_GOVERNED_AI_CAPABILITIES) == 5
    assert len(MEDIA_INTELLIGENCE_GOVERNED_AI_CAPABILITIES) == 12
    assert P0_GOVERNED_AI_CAPABILITIES.isdisjoint(WEB_GOVERNED_AI_CAPABILITIES)
    assert P0_GOVERNED_AI_CAPABILITIES.isdisjoint(
        MEDIA_INTELLIGENCE_GOVERNED_AI_CAPABILITIES
    )
    assert WEB_GOVERNED_AI_CAPABILITIES.isdisjoint(
        MEDIA_INTELLIGENCE_GOVERNED_AI_CAPABILITIES
    )
    assert SKILL_ENGINEERING_GOVERNED_AI_CAPABILITIES == frozenset(
        {"architecture.propose", "code.review", "test.execute"}
    )
    assert (
        SKILL_ENGINEERING_GOVERNED_AI_CAPABILITIES - P0_GOVERNED_AI_CAPABILITIES
        == frozenset({"test.execute"})
    )
    assert AGENT_GOVERNED_AI_CAPABILITIES == frozenset(
        set(P0_GOVERNED_AI_CAPABILITIES)
        | set(WEB_GOVERNED_AI_CAPABILITIES)
        | set(MEDIA_INTELLIGENCE_GOVERNED_AI_CAPABILITIES)
        | set(SKILL_ENGINEERING_GOVERNED_AI_CAPABILITIES)
    )
    assert len(AGENT_GOVERNED_AI_CAPABILITIES) == 34


def test_tool_verifier_and_side_effect_capabilities_never_enter_external_ai_union() -> None:
    forbidden = {
        "web.verify",
        "evidence.verify",
        "security.verify",
        "provider.request",
        "media.write",
        "social.publish",
    }
    assert forbidden.isdisjoint(AGENT_GOVERNED_AI_CAPABILITIES)
    assert "social.publish-propose" in AGENT_GOVERNED_AI_CAPABILITIES
    assert "media.generate" in AGENT_GOVERNED_AI_CAPABILITIES


def test_union_is_immutable_frozenset() -> None:
    with pytest.raises(AttributeError):
        AGENT_GOVERNED_AI_CAPABILITIES.add("web.verify")  # type: ignore[attr-defined]
