"""Additive Research Factory skill composition on the canonical runtime.

This is not a second runtime/router/provider registry. It provisions the existing
Intelligence identities plus the six first-party Research skills into a supplied
GovernedRuntime. Provider/network capability remains separately configured and
source acquisition remains outside this composition.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from services.agent_governance import GrantAuthorizer
from services.named_agent_executor import NamedAgentExecutor
from services.research_factory_skills import (
    RESEARCH_FACTORY_SKILLS,
    default_research_skills_root,
    ensure_research_factory_skills,
)
from services.runtime import GovernedRuntime


@dataclass(frozen=True, slots=True)
class ResearchRuntimeComposition:
    named_executor: NamedAgentExecutor
    agent_count: int
    skill_count: int


def compose_research_runtime(
    runtime: GovernedRuntime,
    grants: GrantAuthorizer,
    *,
    repository_root: Path,
) -> ResearchRuntimeComposition:
    """Provision bounded Research skills without inventing source/network authority."""

    named = NamedAgentExecutor(runtime, grants)
    digests = ensure_research_factory_skills(
        named,
        default_research_skills_root(repository_root.resolve()),
    )
    owner_ids = {binding.owner_agent_id for binding in RESEARCH_FACTORY_SKILLS}
    if len(digests) != 6 or set(digests) != {
        binding.skill_id for binding in RESEARCH_FACTORY_SKILLS
    }:
        raise ValueError("Research runtime skill composition drifted")
    if len(owner_ids) != 3:
        raise ValueError("Research runtime owner composition drifted")
    return ResearchRuntimeComposition(
        named_executor=named,
        agent_count=len(owner_ids),
        skill_count=len(digests),
    )


__all__ = ["ResearchRuntimeComposition", "compose_research_runtime"]
