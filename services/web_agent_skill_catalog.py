"""First-party advisory skills for the five proposal-oriented Web agents."""

from __future__ import annotations

from dataclasses import dataclass

from services.agent_registry import registration_for
from services.named_agent_executor import NamedAgentExecutor
from services.web_agent_execution import WEB_AGENT_BINDINGS, web_binding_for


class WebAgentSkillCatalogError(ValueError):
    """Web agent skill identity or authority drifted."""


@dataclass(frozen=True, slots=True)
class WebAgentSkillDefinition:
    skill_id: str
    owner_agent_id: str
    capability: str
    instructions: str

    def content(self) -> bytes:
        return self.instructions.strip().encode("utf-8") + b"\n"


WEB_AGENT_PROPOSAL_SKILLS: tuple[WebAgentSkillDefinition, ...] = (
    WebAgentSkillDefinition(
        "ilaios.skill.web.ux.v1",
        "ilaios.agent.web.ux.v1",
        "web.ux",
        """You are ILAIOS WebUX. Produce a bounded UX proposal from supplied requirements and evidence. Cover information architecture, flows, interaction states, accessibility implications and responsive behavior. You do not render, deploy, mutate source, claim browser verification, or override the canonical Web Factory. Clearly separate recommendation from observed evidence.""",
    ),
    WebAgentSkillDefinition(
        "ilaios.skill.web.visual.v1",
        "ilaios.agent.web.visual.v1",
        "web.visual",
        """You are ILAIOS WebVisual. Produce a bounded visual-system proposal from the admitted brief: hierarchy, typography, spacing, component rhythm, responsive composition and brand constraints. Do not invent assets, claim rendering, alter code, deploy, or bypass canonical Web Factory design/quality gates.""",
    ),
    WebAgentSkillDefinition(
        "ilaios.skill.web.asset.v1",
        "ilaios.agent.web.asset.v1",
        "web.asset",
        """You are ILAIOS WebAsset. Analyze supplied admitted asset metadata and propose an asset plan, placement, variants, accessibility text requirements and provenance constraints. Never fabricate asset existence, read arbitrary files, generate unapproved media, mutate storage, or claim an asset was produced without evidence.""",
    ),
    WebAgentSkillDefinition(
        "ilaios.skill.web.content.v1",
        "ilaios.agent.web.content.v1",
        "web.content",
        """You are ILAIOS WebContent. Produce concise page-content structure and copy recommendations from the admitted requirements. Preserve factual uncertainty, locale intent and brand constraints. Do not invent customer facts, publish content, mutate source, or claim a finished website without canonical Web Factory evidence.""",
    ),
    WebAgentSkillDefinition(
        "ilaios.skill.web.seo.v1",
        "ilaios.agent.web.seo.v1",
        "web.seo",
        """You are ILAIOS WebSEO. Produce a bounded technical/on-page SEO proposal from supplied site evidence: titles, descriptions, canonical strategy, semantic structure, crawl/index considerations and structured-data opportunities. Do not claim rankings, live indexing, deployment or browser verification without observed evidence.""",
    ),
)


def ensure_web_agent_proposal_skills(executor: NamedAgentExecutor) -> dict[str, str]:
    validate_web_agent_skill_catalog()
    return {
        item.skill_id: executor.ensure_skill(
            item.skill_id,
            item.content(),
            frozenset({item.capability}),
        )
        for item in WEB_AGENT_PROPOSAL_SKILLS
    }


def validate_web_agent_skill_catalog() -> None:
    expected = {
        binding.primary_skill_id
        for binding in WEB_AGENT_BINDINGS
        if binding.execution_mode == "governed-ai"
    }
    actual = {item.skill_id for item in WEB_AGENT_PROPOSAL_SKILLS}
    if len(WEB_AGENT_PROPOSAL_SKILLS) != 5 or actual != expected:
        raise WebAgentSkillCatalogError("Web proposal skill coverage drifted")
    owners = [item.owner_agent_id for item in WEB_AGENT_PROPOSAL_SKILLS]
    if len(set(owners)) != 5:
        raise WebAgentSkillCatalogError("Web proposal skill ownership must be unique")
    for item in WEB_AGENT_PROPOSAL_SKILLS:
        binding = web_binding_for(item.owner_agent_id)
        registration = registration_for(item.owner_agent_id)
        if binding.primary_skill_id != item.skill_id or binding.capability != item.capability:
            raise WebAgentSkillCatalogError("Web proposal skill diverges from binding")
        if item.capability not in registration.manifest.capabilities:
            raise WebAgentSkillCatalogError("Web proposal skill exceeds manifest")
        if not item.instructions.strip():
            raise WebAgentSkillCatalogError("Web proposal skill instructions are blank")


validate_web_agent_skill_catalog()
