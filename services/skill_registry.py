"""ILAIOS-native skill metadata registry.

Skills are owned by ILAIOS and describe bounded domain knowledge or execution
procedures. They never grant tool, provider, policy, approval, routing, tenant,
or evidence authority. Runtime authority remains in the canonical governed
platform capabilities declared by ``services.capability_registry``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from services.capability_registry import CAPABILITIES

SkillKind = Literal["engineering", "factory", "capability", "assurance"]
RiskClass = Literal["low", "medium", "high"]


class SkillRegistryError(ValueError):
    """The ILAIOS skill registry violates a canonical boundary."""


@dataclass(frozen=True, slots=True)
class SkillDefinition:
    skill_id: str
    kind: SkillKind
    family: str
    capability_dependencies: frozenset[str]
    risk_class: RiskClass
    requires_approval: bool = False


SKILLS: tuple[SkillDefinition, ...] = (
    SkillDefinition(
        "ilaios.skill.engineering.create",
        "engineering",
        "skill-engineering",
        frozenset({"ilaios.capability.policy-governance", "ilaios.capability.evidence-audit"}),
        "medium",
    ),
    SkillDefinition(
        "ilaios.skill.factory.web.production-qa",
        "factory",
        "web",
        frozenset(
            {
                "ilaios.capability.web-factory",
                "ilaios.capability.policy-governance",
                "ilaios.capability.evidence-audit",
            }
        ),
        "medium",
    ),
    SkillDefinition(
        "ilaios.skill.capability.browser.production-verify",
        "capability",
        "browser",
        frozenset(
            {
                "ilaios.capability.workflow-runtime",
                "ilaios.capability.policy-governance",
                "ilaios.capability.evidence-audit",
            }
        ),
        "high",
        requires_approval=True,
    ),
    SkillDefinition(
        "ilaios.skill.assurance.security-review",
        "assurance",
        "security",
        frozenset(
            {
                "ilaios.capability.agent-governance",
                "ilaios.capability.policy-governance",
                "ilaios.capability.evidence-audit",
            }
        ),
        "high",
    ),
)


def validate_skill_registry(skills: tuple[SkillDefinition, ...] = SKILLS) -> None:
    ids = [skill.skill_id for skill in skills]
    if len(ids) != len(set(ids)):
        raise SkillRegistryError("skill IDs must be globally unique")

    known_capabilities = {item.capability_id for item in CAPABILITIES}
    forbidden_tokens = (
        "openai",
        "anthropic",
        "claude",
        "gemini",
        "seedance",
        "vercel",
        "playwright",
        "huggingface",
    )

    for skill in skills:
        if not skill.skill_id.startswith("ilaios.skill."):
            raise SkillRegistryError("active skills must use the ILAIOS namespace")
        if any(token in skill.skill_id.casefold() for token in forbidden_tokens):
            raise SkillRegistryError("provider or vendor identity must not leak into skill IDs")
        unknown = skill.capability_dependencies - known_capabilities
        if unknown:
            raise SkillRegistryError(
                f"unknown capability dependencies for {skill.skill_id}: {sorted(unknown)}"
            )
        if "ilaios.capability.evidence-audit" not in skill.capability_dependencies:
            raise SkillRegistryError(f"{skill.skill_id} must preserve evidence authority")
        if skill.kind in {"factory", "capability", "assurance"} and (
            "ilaios.capability.policy-governance" not in skill.capability_dependencies
        ):
            raise SkillRegistryError(f"{skill.skill_id} must preserve policy governance")


def skill(skill_id: str) -> SkillDefinition:
    for definition in SKILLS:
        if definition.skill_id == skill_id:
            return definition
    raise KeyError(skill_id)


def skills_for_family(family: str) -> tuple[SkillDefinition, ...]:
    return tuple(item for item in SKILLS if item.family == family)


validate_skill_registry()
