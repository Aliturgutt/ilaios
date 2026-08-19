"""Canonical first-party Research Factory skill bindings.

These bindings reuse the existing Intelligence agent identities and canonical
runtime. They do not fetch arbitrary external data, create a second research
engine, or grant network/provider authority. Source material must already be
admitted by the surrounding product/factory boundary.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from services.agent_registry import registration_for
from services.named_agent_executor import NamedAgentExecutor


class ResearchFactorySkillError(ValueError):
    """A Research Factory skill binding violated a canonical boundary."""


@dataclass(frozen=True, slots=True)
class ResearchFactorySkillBinding:
    skill_id: str
    logical_id: str
    owner_agent_id: str
    capability: str
    permission: str


RESEARCH_FACTORY_SKILLS: tuple[ResearchFactorySkillBinding, ...] = (
    ResearchFactorySkillBinding(
        "ilaios-research-planning",
        "factories/research/planning",
        "ilaios.agent.intelligence.research.v1",
        "research.collect",
        "source.read",
    ),
    ResearchFactorySkillBinding(
        "ilaios-research",
        "factories/research/research",
        "ilaios.agent.intelligence.research.v1",
        "research.collect",
        "source.read",
    ),
    ResearchFactorySkillBinding(
        "ilaios-source-validation",
        "factories/research/source-validation",
        "ilaios.agent.intelligence.fact-check.v1",
        "research.verify",
        "source.read",
    ),
    ResearchFactorySkillBinding(
        "ilaios-contradiction-check",
        "factories/research/contradiction-check",
        "ilaios.agent.intelligence.fact-check.v1",
        "research.verify",
        "source.read",
    ),
    ResearchFactorySkillBinding(
        "ilaios-citation-validation",
        "factories/research/citation-validation",
        "ilaios.agent.intelligence.fact-check.v1",
        "research.verify",
        "source.read",
    ),
    ResearchFactorySkillBinding(
        "ilaios-research-synthesis",
        "factories/research/synthesis",
        "ilaios.agent.intelligence.knowledge.v1",
        "knowledge.curate",
        "evidence.read",
    ),
)

RESEARCH_FACTORY_SKILL_IDS: tuple[str, ...] = tuple(
    binding.skill_id for binding in RESEARCH_FACTORY_SKILLS
)


def default_research_skills_root(repository_root: Path) -> Path:
    return repository_root / "tools" / "research-factory" / "skills"


def validate_research_factory_skills(skills_root: Path) -> None:
    ids = [binding.skill_id for binding in RESEARCH_FACTORY_SKILLS]
    logical_ids = [binding.logical_id for binding in RESEARCH_FACTORY_SKILLS]
    if len(ids) != 6 or len(ids) != len(set(ids)):
        raise ResearchFactorySkillError("Research Factory requires six unique skills")
    if len(logical_ids) != len(set(logical_ids)):
        raise ResearchFactorySkillError("Research Factory logical IDs must be unique")

    root = skills_root.resolve()
    for binding in RESEARCH_FACTORY_SKILLS:
        registration = registration_for(binding.owner_agent_id)
        manifest = registration.manifest
        if manifest.team != "intelligence":
            raise ResearchFactorySkillError("Research skills require Intelligence owners")
        if binding.capability not in manifest.capabilities:
            raise ResearchFactorySkillError(
                f"Research skill capability exceeds owner manifest: {binding.skill_id}"
            )
        if binding.permission not in manifest.permissions:
            raise ResearchFactorySkillError(
                f"Research skill permission exceeds owner manifest: {binding.skill_id}"
            )
        skill_path = root / binding.skill_id / "SKILL.md"
        if not skill_path.is_file():
            raise ResearchFactorySkillError(
                f"Research skill package is unavailable: {binding.skill_id}"
            )
        text = skill_path.read_text(encoding="utf-8")
        required_markers = (
            f"name: {binding.skill_id}",
            "Status: IMPLEMENTED",
            "Owner: ILAIOS",
            "No direct network authority",
        )
        if not all(marker in text for marker in required_markers):
            raise ResearchFactorySkillError(
                f"Research skill package contract drifted: {binding.skill_id}"
            )


def ensure_research_factory_skills(
    executor: NamedAgentExecutor,
    skills_root: Path,
) -> dict[str, str]:
    """Provision six bounded skills into the existing canonical runtime."""

    validate_research_factory_skills(skills_root)
    digests: dict[str, str] = {}
    for binding in RESEARCH_FACTORY_SKILLS:
        executor.ensure_agent(binding.owner_agent_id)
        instructions = (skills_root / binding.skill_id / "SKILL.md").read_bytes()
        digests[binding.skill_id] = executor.ensure_skill(
            binding.skill_id,
            instructions,
            frozenset({binding.capability}),
        )
    return digests


__all__ = [
    "RESEARCH_FACTORY_SKILLS",
    "RESEARCH_FACTORY_SKILL_IDS",
    "ResearchFactorySkillBinding",
    "ResearchFactorySkillError",
    "default_research_skills_root",
    "ensure_research_factory_skills",
    "validate_research_factory_skills",
]
