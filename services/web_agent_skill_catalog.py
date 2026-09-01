"""First-party skill catalog for canonical Web proposal agents.

BrowserQA reuses the already-governed browser skill packages and ToolGateway path.
The five proposal roles receive bounded advisory skills only; no skill grants direct
network, deployment, filesystem mutation, or publication authority.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from services.browser_runtime_composition import ensure_web_factory_browser_skills
from services.named_agent_executor import NamedAgentExecutor
from services.web_agent_execution import WEB_AGENT_BINDINGS, web_binding_for


class WebAgentSkillCatalogError(ValueError):
    """Web agent skill identity or ownership drifted from canonical bindings."""


@dataclass(frozen=True, slots=True)
class WebAgentSkillDefinition:
    skill_id: str
    owner_agent_id: str
    capability: str
    instructions: str

    def content(self) -> bytes:
        return self.instructions.strip().encode("utf-8") + b"\n"


WEB_FIRST_PARTY_AGENT_SKILLS: tuple[WebAgentSkillDefinition, ...] = (
    WebAgentSkillDefinition(
        "ilaios.skill.web.ux.v1",
        "ilaios.agent.web.ux.v1",
        "web.ux",
        """You are the canonical ILAIOS WebUX agent. Produce a bounded UX proposal from supplied requirements and evidence. Specify information hierarchy, user flows, interaction states, accessibility implications, responsive behavior, and acceptance criteria. Do not invent user research, claim browser verification, mutate source, deploy, or bypass the canonical Web Factory and governance gates.""",
    ),
    WebAgentSkillDefinition(
        "ilaios.skill.web.visual.v1",
        "ilaios.agent.web.visual.v1",
        "web.visual",
        """You are the canonical ILAIOS WebVisual agent. Produce a visual-system proposal that respects the supplied brand, layout constraints, typography, spacing, component hierarchy, responsive behavior, and accessibility evidence. Avoid generic template output. Do not create a parallel renderer, mutate production, or claim generated assets or visual QA without evidence.""",
    ),
    WebAgentSkillDefinition(
        "ilaios.skill.web.asset.v1",
        "ilaios.agent.web.asset.v1",
        "web.asset",
        """You are the canonical ILAIOS WebAsset agent. Analyze admitted asset metadata and propose the minimum required asset plan, including purpose, dimensions, format, accessibility text, provenance, and placement. Never fabricate an asset, provenance record, license, upload, or generated-file claim. Actual asset creation/import remains behind canonical tools and evidence.""",
    ),
    WebAgentSkillDefinition(
        "ilaios.skill.web.content.v1",
        "ilaios.agent.web.content.v1",
        "web.content",
        """You are the canonical ILAIOS WebContent agent. Produce concise page/content proposals from supplied requirements and product facts backed by supplied evidence. Preserve CURRENT REALITY versus TARGET TRUTH, avoid unsupported product claims, and make CTA/copy structure explicit. Do not publish, mutate a CMS, invent metrics, or claim legal/compliance approval.""",
    ),
    WebAgentSkillDefinition(
        "ilaios.skill.web.seo.v1",
        "ilaios.agent.web.seo.v1",
        "web.seo",
        """You are the canonical ILAIOS WebSEO agent. Propose evidence-based technical and on-page SEO metadata from supplied site structure and content. Cover titles, descriptions, canonical intent, structured-data opportunities, crawl/index constraints, internal linking, and measurable validation steps. Do not claim rankings, Search Console data, live crawl results, or production verification without supplied evidence.""",
    ),
)


def ensure_web_agent_skills(
    executor: NamedAgentExecutor,
    repository_root: Path,
) -> dict[str, str]:
    validate_web_agent_skill_catalog()
    digests = {
        item.skill_id: executor.ensure_skill(
            item.skill_id,
            item.content(),
            frozenset({item.capability}),
        )
        for item in WEB_FIRST_PARTY_AGENT_SKILLS
    }
    browser = ensure_web_factory_browser_skills(executor, repository_root)
    overlap = set(digests) & set(browser)
    if overlap:
        raise WebAgentSkillCatalogError("Web proposal and BrowserQA skill IDs overlap")
    digests.update(browser)
    return digests


def validate_web_agent_skill_catalog() -> None:
    expected = {
        binding.primary_skill_id
        for binding in WEB_AGENT_BINDINGS
        if binding.execution_mode == "governed-ai"
    }
    actual = {item.skill_id for item in WEB_FIRST_PARTY_AGENT_SKILLS}
    if actual != expected:
        raise WebAgentSkillCatalogError(
            f"Web proposal skill coverage mismatch missing={sorted(expected-actual)} "
            f"extra={sorted(actual-expected)}"
        )
    if len(actual) != 5 or len(actual) != len(WEB_FIRST_PARTY_AGENT_SKILLS):
        raise WebAgentSkillCatalogError("Web proposal skills must contain five unique IDs")
    owners = [item.owner_agent_id for item in WEB_FIRST_PARTY_AGENT_SKILLS]
    if len(owners) != len(set(owners)):
        raise WebAgentSkillCatalogError("Web proposal skill ownership must be unique")
    for item in WEB_FIRST_PARTY_AGENT_SKILLS:
        binding = web_binding_for(item.owner_agent_id)
        if binding.execution_mode != "governed-ai":
            raise WebAgentSkillCatalogError("BrowserQA cannot be replaced by an AI skill")
        if binding.primary_skill_id != item.skill_id or binding.capability != item.capability:
            raise WebAgentSkillCatalogError("Web skill diverges from canonical binding")
        if not item.instructions.strip():
            raise WebAgentSkillCatalogError("Web skill instructions must not be blank")


validate_web_agent_skill_catalog()
