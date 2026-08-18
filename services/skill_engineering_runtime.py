"""Bounded runtime wiring for explicitly admitted Skill Engineering packages.

This module does not create a second runtime, registry, router, policy engine, or
agent identity. It maps a deliberately small allowlist of first-party
Skill Engineering packages onto existing canonical Engineering agent authority.
Source packages that are not listed here remain source/spec only.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from services.agent_registry import registration_for
from services.named_agent_executor import NamedAgentExecutor
from services.skill_engineering_catalog import SkillEngineeringCatalog


class SkillEngineeringRuntimeError(ValueError):
    """Skill Engineering runtime wiring violated a canonical authority boundary."""


@dataclass(frozen=True, slots=True)
class SkillEngineeringRuntimeBinding:
    skill_id: str
    logical_id: str
    owner_agent_id: str
    capability: str
    permission: str


SKILL_ENGINEERING_RUNTIME_BINDINGS: tuple[SkillEngineeringRuntimeBinding, ...] = (
    SkillEngineeringRuntimeBinding(
        skill_id="skill-create",
        logical_id="skill-engineering/create",
        owner_agent_id="ilaios.agent.engineering.architect.v1",
        capability="architecture.propose",
        permission="repository.read",
    ),
    SkillEngineeringRuntimeBinding(
        skill_id="skill-validate",
        logical_id="skill-engineering/validate",
        owner_agent_id="ilaios.agent.engineering.test.v1",
        capability="test.execute",
        permission="repository.read",
    ),
    SkillEngineeringRuntimeBinding(
        skill_id="skill-evaluate",
        logical_id="skill-engineering/evaluate",
        owner_agent_id="ilaios.agent.engineering.review.v1",
        capability="code.review",
        permission="repository.read",
    ),
    SkillEngineeringRuntimeBinding(
        skill_id="skill-benchmark",
        logical_id="skill-engineering/benchmark",
        owner_agent_id="ilaios.agent.engineering.test.v1",
        capability="test.execute",
        permission="repository.read",
    ),
    SkillEngineeringRuntimeBinding(
        skill_id="skill-regression",
        logical_id="skill-engineering/regression",
        owner_agent_id="ilaios.agent.engineering.test.v1",
        capability="test.execute",
        permission="repository.read",
    ),
)

_BINDINGS_BY_SKILL_ID = {
    binding.skill_id: binding for binding in SKILL_ENGINEERING_RUNTIME_BINDINGS
}


def runtime_binding_for(skill_id: str) -> SkillEngineeringRuntimeBinding:
    try:
        return _BINDINGS_BY_SKILL_ID[skill_id]
    except KeyError as exc:
        raise SkillEngineeringRuntimeError(
            f"skill-engineering package has no runtime admission: {skill_id}"
        ) from exc


def ensure_skill_engineering_runtime_skills(
    executor: NamedAgentExecutor,
    skills_root: Path,
) -> dict[str, str]:
    """Provision only explicitly admitted Skill Engineering instructions.

    Manifest capabilities/tools remain package dependency declarations. Runtime
    authority is derived only from the existing canonical owner-agent capability
    in ``SKILL_ENGINEERING_RUNTIME_BINDINGS``; package text cannot widen it.
    """
    catalog = SkillEngineeringCatalog(skills_root.resolve())
    validate_skill_engineering_runtime_bindings(catalog)
    digests: dict[str, str] = {}
    for binding in SKILL_ENGINEERING_RUNTIME_BINDINGS:
        package = catalog.resolve(binding.skill_id)
        instructions = (package.root / "SKILL.md").read_bytes()
        if not instructions.strip():
            raise SkillEngineeringRuntimeError(
                f"empty skill-engineering instructions: {binding.skill_id}"
            )
        digests[binding.skill_id] = executor.ensure_skill(
            binding.skill_id,
            instructions,
            frozenset({binding.capability}),
        )
    return digests


def validate_skill_engineering_runtime_bindings(
    catalog: SkillEngineeringCatalog,
) -> None:
    bindings = SKILL_ENGINEERING_RUNTIME_BINDINGS
    ids = [binding.skill_id for binding in bindings]
    if len(ids) != len(set(ids)):
        raise SkillEngineeringRuntimeError(
            "skill-engineering runtime bindings must be unique"
        )
    for binding in bindings:
        package = catalog.resolve(binding.skill_id)
        if package.logical_id != binding.logical_id:
            raise SkillEngineeringRuntimeError(
                f"skill-engineering logical identity drifted: {binding.skill_id}"
            )
        if not package.independent_review_required:
            raise SkillEngineeringRuntimeError(
                f"runtime skill requires independent review: {binding.skill_id}"
            )
        registration = registration_for(binding.owner_agent_id)
        manifest = registration.manifest
        if manifest.team != "engineering":
            raise SkillEngineeringRuntimeError(
                "skill-engineering runtime owner must be an Engineering agent"
            )
        if binding.capability not in manifest.capabilities:
            raise SkillEngineeringRuntimeError(
                f"runtime capability exceeds owner manifest: {binding.skill_id}"
            )
        if binding.permission not in manifest.permissions:
            raise SkillEngineeringRuntimeError(
                f"runtime permission exceeds owner manifest: {binding.skill_id}"
            )


__all__ = [
    "SKILL_ENGINEERING_RUNTIME_BINDINGS",
    "SkillEngineeringRuntimeBinding",
    "SkillEngineeringRuntimeError",
    "ensure_skill_engineering_runtime_skills",
    "runtime_binding_for",
    "validate_skill_engineering_runtime_bindings",
]
