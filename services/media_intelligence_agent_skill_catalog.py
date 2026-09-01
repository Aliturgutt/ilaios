"""First-party proposal skills for canonical Media/Intelligence agents.

Existing Research Factory skills are reused for Research, FactCheck and Knowledge.
Media agent skills and DataAnalyst are ILAIOS-native proposal contracts; they do
not bypass the canonical Video/Research factories or grant side-effect authority.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from services.agent_registry import registration_for
from services.media_intelligence_agent_execution import (
    MEDIA_INTELLIGENCE_AGENT_BINDINGS,
    media_intelligence_binding_for,
)
from services.named_agent_executor import NamedAgentExecutor
from services.research_factory_skills import (
    RESEARCH_FACTORY_SKILLS,
    default_research_skills_root,
    ensure_research_factory_skills,
)


class MediaIntelligenceSkillCatalogError(ValueError):
    """Media/Intelligence skill identity or authority drifted."""


@dataclass(frozen=True, slots=True)
class MediaIntelligenceSkillDefinition:
    skill_id: str
    owner_agent_id: str
    capability: str
    instructions: str

    def content(self) -> bytes:
        return self.instructions.strip().encode("utf-8") + b"\n"


MEDIA_INTELLIGENCE_FIRST_PARTY_SKILLS: tuple[MediaIntelligenceSkillDefinition, ...] = (
    MediaIntelligenceSkillDefinition(
        "ilaios.skill.media.story.v1",
        "ilaios.agent.media.story.v1",
        "media.story",
        """You are the canonical ILAIOS Story agent. Turn an admitted brief into a bounded story proposal with objective, audience, narrative beats, continuity requirements and unresolved assumptions. Do not call media providers, mutate assets, spend budget, publish, or claim production. Real execution remains in the governed Video Factory and requires separate policy, grant and evidence gates.""",
    ),
    MediaIntelligenceSkillDefinition(
        "ilaios.skill.media.scene-director.v1",
        "ilaios.agent.media.scene-director.v1",
        "media.scene-plan",
        """You are the canonical ILAIOS SceneDirector. Convert admitted script/story evidence into a bounded shot and scene proposal. Preserve continuity, reference-asset constraints and explicit acceptance criteria. Do not generate media, invoke providers, edit files, or bypass the existing Video Factory director/prompting lifecycle.""",
    ),
    MediaIntelligenceSkillDefinition(
        "ilaios.skill.media.generation-proposal.v1",
        "ilaios.agent.media.generation.v1",
        "media.generate",
        """You are the canonical ILAIOS MediaGeneration planning agent. Produce only a governed generation proposal from the admitted shot plan, including required inputs, model-fit constraints, reference requirements and expected evidence. You have no direct provider.request or media.write authority. Actual generation is executed only by the existing governed Video Factory/provider runtime after admission and budget checks.""",
    ),
    MediaIntelligenceSkillDefinition(
        "ilaios.skill.media.voice-audio.v1",
        "ilaios.agent.media.voice-audio.v1",
        "media.audio",
        """You are the canonical ILAIOS VoiceAudio agent. Produce a bounded voice/audio proposal from admitted script evidence: voice intent, timing, music/SFX requirements, mix constraints and acceptance criteria. Do not synthesize audio, mutate media, call providers, or claim generated assets without runtime evidence.""",
    ),
    MediaIntelligenceSkillDefinition(
        "ilaios.skill.media.edit-proposal.v1",
        "ilaios.agent.media.editor.v1",
        "media.assemble",
        """You are the canonical ILAIOS Editor agent. Produce a bounded timeline/assembly proposal from admitted asset evidence. Describe cuts, ordering, transitions, caption/composition requirements and repair targets. Do not write media files or invoke render/edit tools directly; those side effects remain in the governed Video Factory.""",
    ),
    MediaIntelligenceSkillDefinition(
        "ilaios.skill.media.qa-proposal.v1",
        "ilaios.agent.media.qa.v1",
        "media.verify",
        """You are the canonical ILAIOS MediaQA agent. Evaluate only supplied artifact observations/evidence and propose findings against declared acceptance criteria. Never fabricate visual, audio, brand or technical observations. Do not self-certify VERIFIED state; IndependentVerifier and persisted runtime evidence remain authoritative.""",
    ),
    MediaIntelligenceSkillDefinition(
        "ilaios.skill.media.social-metadata.v1",
        "ilaios.agent.media.social-metadata.v1",
        "social.metadata",
        """You are the canonical ILAIOS SocialMetadata agent. Produce metadata proposals only from the admitted artifact and campaign brief: titles, descriptions, tags, accessibility text and platform-safe variants. Do not publish, access social accounts, or claim platform acceptance.""",
    ),
    MediaIntelligenceSkillDefinition(
        "ilaios.skill.media.publishing-proposal.v1",
        "ilaios.agent.media.publishing.v1",
        "social.publish-propose",
        """You are the canonical ILAIOS Publishing agent. Produce a publish proposal containing target platform, artifact identity, metadata reference, timing intent, required approvals and rollback evidence. Never call platform APIs, upload media, spend budget or bypass human/policy approval. Direct social.publish authority is explicitly outside this agent.""",
    ),
    MediaIntelligenceSkillDefinition(
        "ilaios.skill.intelligence.data-analyst.v1",
        "ilaios.agent.intelligence.data-analyst.v1",
        "data.analyze",
        """You are the canonical ILAIOS DataAnalyst. Analyze only admitted data/evidence supplied in the governed task. State transformations, assumptions, calculations, uncertainty and reproducibility requirements. Do not acquire external data, execute arbitrary code, mutate datasets, invent observations or promote conclusions beyond supplied evidence.""",
    ),
)

_RESEARCH_PRIMARY_SKILL_IDS = frozenset(
    {"ilaios-research", "ilaios-source-validation", "ilaios-research-synthesis"}
)


def ensure_media_intelligence_agent_skills(
    executor: NamedAgentExecutor,
    repository_root: Path,
) -> dict[str, str]:
    """Provision agent skills into the existing runtime without new authority."""
    validate_media_intelligence_skill_catalog()
    research = ensure_research_factory_skills(
        executor,
        default_research_skills_root(repository_root.resolve()),
    )
    if not _RESEARCH_PRIMARY_SKILL_IDS.issubset(research):
        raise MediaIntelligenceSkillCatalogError(
            "canonical Research primary skills are unavailable"
        )
    digests = dict(research)
    for item in MEDIA_INTELLIGENCE_FIRST_PARTY_SKILLS:
        executor.ensure_agent(item.owner_agent_id)
        digests[item.skill_id] = executor.ensure_skill(
            item.skill_id,
            item.content(),
            frozenset({item.capability}),
        )
    return digests


def validate_media_intelligence_skill_catalog() -> None:
    ids = [item.skill_id for item in MEDIA_INTELLIGENCE_FIRST_PARTY_SKILLS]
    owners = [item.owner_agent_id for item in MEDIA_INTELLIGENCE_FIRST_PARTY_SKILLS]
    if len(ids) != 9 or len(ids) != len(set(ids)):
        raise MediaIntelligenceSkillCatalogError(
            "Media/DataAnalyst first-party catalog must contain nine unique skills"
        )
    if len(owners) != 9 or len(owners) != len(set(owners)):
        raise MediaIntelligenceSkillCatalogError(
            "Media/DataAnalyst primary skill ownership must be one-to-one"
        )
    for item in MEDIA_INTELLIGENCE_FIRST_PARTY_SKILLS:
        binding = media_intelligence_binding_for(item.owner_agent_id)
        registration = registration_for(item.owner_agent_id)
        if binding.primary_skill_id != item.skill_id:
            raise MediaIntelligenceSkillCatalogError(
                "first-party skill identity diverges from agent binding"
            )
        if binding.capability != item.capability:
            raise MediaIntelligenceSkillCatalogError(
                "first-party skill capability diverges from agent binding"
            )
        if item.capability not in registration.manifest.capabilities:
            raise MediaIntelligenceSkillCatalogError(
                "first-party skill capability exceeds owner manifest"
            )
        if not item.instructions.strip():
            raise MediaIntelligenceSkillCatalogError("skill instructions cannot be blank")

    research_by_id = {item.skill_id: item for item in RESEARCH_FACTORY_SKILLS}
    for binding in MEDIA_INTELLIGENCE_AGENT_BINDINGS:
        if registration_for(binding.agent_id).manifest.team != "intelligence":
            continue
        if binding.primary_skill_id == "ilaios.skill.intelligence.data-analyst.v1":
            continue
        research_binding = research_by_id.get(binding.primary_skill_id)
        if research_binding is None:
            raise MediaIntelligenceSkillCatalogError(
                "Intelligence binding does not reuse canonical Research skill"
            )
        if research_binding.owner_agent_id != binding.agent_id:
            raise MediaIntelligenceSkillCatalogError(
                "Research skill owner diverges from Intelligence binding"
            )
        if research_binding.capability != binding.capability:
            raise MediaIntelligenceSkillCatalogError(
                "Research skill capability diverges from Intelligence binding"
            )
        if research_binding.permission != binding.permission:
            raise MediaIntelligenceSkillCatalogError(
                "Research skill permission diverges from Intelligence binding"
            )


validate_media_intelligence_skill_catalog()

__all__ = [
    "MEDIA_INTELLIGENCE_FIRST_PARTY_SKILLS",
    "MediaIntelligenceSkillCatalogError",
    "ensure_media_intelligence_agent_skills",
    "validate_media_intelligence_skill_catalog",
]
