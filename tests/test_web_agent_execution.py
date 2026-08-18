from services.agent_registry import registration_for
from services.web_agent_execution import (
    WEB_AGENT_BINDINGS,
    WEB_GOVERNED_AI_CAPABILITIES,
    web_binding_for,
)


def test_web_bindings_cover_exact_canonical_team() -> None:
    assert len(WEB_AGENT_BINDINGS) == 6
    assert len({binding.agent_id for binding in WEB_AGENT_BINDINGS}) == 6
    assert {registration_for(binding.agent_id).manifest.team for binding in WEB_AGENT_BINDINGS} == {
        "web"
    }
    for binding in WEB_AGENT_BINDINGS:
        manifest = registration_for(binding.agent_id).manifest
        assert binding.capability in manifest.capabilities
        assert binding.permission in manifest.permissions


def test_five_web_roles_are_governed_ai_proposal_roles() -> None:
    governed = tuple(
        binding for binding in WEB_AGENT_BINDINGS if binding.execution_mode == "governed-ai"
    )
    assert len(governed) == 5
    assert {binding.capability for binding in governed} == WEB_GOVERNED_AI_CAPABILITIES
    assert WEB_GOVERNED_AI_CAPABILITIES == frozenset(
        {"web.ux", "web.visual", "web.asset", "web.content", "web.seo"}
    )


def test_browserqa_remains_real_browser_tool_role() -> None:
    browser = web_binding_for("ilaios.agent.web.browser-qa.v1")
    assert browser.execution_mode == "browser-tool"
    assert browser.primary_skill_id == "ilaios-web-e2e"
    assert browser.capability == "web.verify"
    assert browser.permission == "authorized-site.read"
    assert "web.verify" not in WEB_GOVERNED_AI_CAPABILITIES
