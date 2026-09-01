"""Canonical logical taxonomy for first-party ILAIOS skills.

This module is intentionally not an executor. It classifies skills and maps
logical taxonomy nodes to existing governed runtime skill IDs without moving,
rewriting, or bypassing the canonical Core/runtime boundaries.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final

from services.research_factory_skills import RESEARCH_FACTORY_SKILL_IDS
from services.software_factory_skills import REQUIRED_SKILL_IDS
from services.web_factory_skills import (
    WEB_FACTORY_BROWSER_SKILL_IDS,
    WEB_FACTORY_NATIVE_SKILL_IDS,
)
from src.video_automation.video_lifecycle_skill_manifests import VIDEO_LIFECYCLE_SKILLS
from src.video_automation.video_prompting_skill_manifests import VIDEO_PROMPTING_SKILLS
from src.video_automation.video_skills import VIDEO_SKILLS

_ALLOWED_LAYERS: Final = frozenset(
    {"skill-engineering", "factories", "capabilities", "assurance"}
)
_ALLOWED_FACTORY_FAMILIES: Final = frozenset(
    {"web", "software", "video", "research"}
)
_ALLOWED_CAPABILITY_FAMILIES: Final = frozenset({"browser"})
_SKILL_ENGINEERING_RUNTIME_SKILL_IDS: Final = frozenset(
    {
        "skill-create",
        "skill-validate",
        "skill-evaluate",
        "skill-benchmark",
        "skill-regression",
    }
)
_SECURITY_REVIEW_SKILL_ID: Final = "ilaios-security-review"
_DIFFERENTIAL_REVIEW_SKILL_ID: Final = "ilaios-differential-review"
_AGENTIC_ACTION_AUDIT_SKILL_ID: Final = "ilaios-agentic-action-audit"
_THREAT_MODEL_SKILL_ID: Final = "ilaios-threat-model"
_SUPPLY_CHAIN_AUDIT_SKILL_ID: Final = "ilaios-supply-chain-audit"
_SECURITY_METHODOLOGY_SKILL_IDS: Final = frozenset(
    {
        _SECURITY_REVIEW_SKILL_ID,
        _DIFFERENTIAL_REVIEW_SKILL_ID,
        _AGENTIC_ACTION_AUDIT_SKILL_ID,
        _THREAT_MODEL_SKILL_ID,
        _SUPPLY_CHAIN_AUDIT_SKILL_ID,
    }
)
_VIDEO_RUNTIME_SKILL_IDS: Final = frozenset(
    skill.skill_id
    for skill in (*VIDEO_SKILLS, *VIDEO_PROMPTING_SKILLS, *VIDEO_LIFECYCLE_SKILLS)
)
_RESEARCH_RUNTIME_SKILL_IDS: Final = frozenset(RESEARCH_FACTORY_SKILL_IDS)
_PROTECTED_AUTHORITY_SEGMENTS: Final = frozenset(
    {
        "approval",
        "approval-engine",
        "audit",
        "audit-engine",
        "authorization",
        "core",
        "evidence-chain",
        "execution-dag",
        "model-routing",
        "planner",
        "policy",
        "policy-engine",
        "provider-routing",
        "router",
        "routing",
        "tenant",
        "tool-gateway",
        "validation-pipeline",
    }
)
_SEGMENT = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


@dataclass(frozen=True, slots=True)
class SkillTaxonomyNode:
    """One logical skill node.

    ``backing_skill_ids`` references already-existing governed runtime skills.
    An empty tuple means no governed runtime backing is declared. The logical
    node may still have a source/spec package, but an empty mapping does not
    imply runtime integration, verification, deployment, or production.
    """

    path: tuple[str, ...]
    backing_skill_ids: tuple[str, ...] = ()

    @property
    def logical_id(self) -> str:
        return "/".join(self.path)

    @property
    def layer(self) -> str:
        return self.path[0]


def _node(*path: str, backing_skill_ids: tuple[str, ...] = ()) -> SkillTaxonomyNode:
    return SkillTaxonomyNode(tuple(path), backing_skill_ids)


SKILL_TAXONOMY: Final[tuple[SkillTaxonomyNode, ...]] = (
    _node("skill-engineering", "create", backing_skill_ids=("skill-create",)),
    _node("skill-engineering", "lint"),
    _node("skill-engineering", "validate", backing_skill_ids=("skill-validate",)),
    _node("skill-engineering", "security-scan"),
    _node("skill-engineering", "evaluate", backing_skill_ids=("skill-evaluate",)),
    _node("skill-engineering", "benchmark", backing_skill_ids=("skill-benchmark",)),
    _node("skill-engineering", "regression", backing_skill_ids=("skill-regression",)),
    _node("skill-engineering", "compatibility"),
    _node("skill-engineering", "promote"),
    _node(
        "factories",
        "web",
        "architecture",
        backing_skill_ids=("ilaios-web-architecture",),
    ),
    _node(
        "factories",
        "web",
        "design",
        backing_skill_ids=(
            "ilaios-web-design",
            "ilaios-web-motion-design",
            "ilaios-web-interaction-design",
            "ilaios-web-scroll-composition",
            "ilaios-web-interactive-showcase",
            "ilaios-web-motion-accessibility",
            "ilaios-web-motion-qa",
        ),
    ),
    _node(
        "factories",
        "web",
        "accessibility",
        backing_skill_ids=("ilaios-web-accessibility",),
    ),
    _node(
        "factories",
        "web",
        "performance",
        backing_skill_ids=("ilaios-web-performance",),
    ),
    _node(
        "factories",
        "web",
        "validation",
        backing_skill_ids=("ilaios-web-validation",),
    ),
    _node(
        "factories",
        "web",
        "production-qa",
        backing_skill_ids=("ilaios-web-production-qa",),
    ),
    _node(
        "factories",
        "software",
        "spec",
        backing_skill_ids=("sf-requirements-analysis", "sf-implementation-planning"),
    ),
    _node(
        "factories",
        "software",
        "architecture",
        backing_skill_ids=("sf-architecture-planning",),
    ),
    _node(
        "factories",
        "software",
        "implementation",
        backing_skill_ids=(
            "sf-core-engineering",
            "sf-backend-engineering",
            "sf-frontend-engineering",
            "sf-windows-desktop",
            "sf-integration-engineering",
            "sf-database-migration",
            "sf-api-contract",
            "sf-refactor",
            "sf-migration",
        ),
    ),
    _node(
        "factories",
        "software",
        "test",
        backing_skill_ids=("sf-test-design", "sf-test-generation", "sf-runtime-qa"),
    ),
    _node(
        "factories",
        "software",
        "review",
        backing_skill_ids=("sf-code-review",),
    ),
    _node(
        "factories",
        "software",
        "release-validation",
        backing_skill_ids=("sf-build", "sf-release-readiness", "sf-recovery"),
    ),
    _node(
        "factories",
        "video",
        "director",
        backing_skill_ids=("ilaios.skill.video.direction.cinematography",),
    ),
    _node(
        "factories",
        "video",
        "prompt",
        backing_skill_ids=("ilaios.skill.video.prompt.compose",),
    ),
    _node(
        "factories",
        "video",
        "reference-assets",
        backing_skill_ids=("ilaios.skill.video.reference-assets.inspect",),
    ),
    _node(
        "factories",
        "video",
        "model-fit",
        backing_skill_ids=("ilaios.skill.video.model-fit.analyze",),
    ),
    _node(
        "factories",
        "video",
        "continuity",
        backing_skill_ids=("ilaios.skill.video.continuity.track",),
    ),
    _node(
        "factories",
        "video",
        "generation",
        backing_skill_ids=("ilaios.skill.video.generation.execute",),
    ),
    _node(
        "factories",
        "video",
        "edit",
        backing_skill_ids=(
            "ilaios.skill.video.edit.trim",
            "ilaios.skill.video.edit.concatenate",
            "ilaios.skill.video.edit.overlay",
            "ilaios.skill.video.edit.crop",
            "ilaios.skill.video.edit.scale",
            "ilaios.skill.video.edit.audio-mix",
        ),
    ),
    _node(
        "factories",
        "video",
        "captions",
        backing_skill_ids=("ilaios.skill.video.captions.export",),
    ),
    _node(
        "factories",
        "video",
        "composition",
        backing_skill_ids=("ilaios.skill.video.composition.prepare",),
    ),
    _node(
        "factories",
        "video",
        "render",
        backing_skill_ids=("ilaios.skill.video.render.execute",),
    ),
    _node(
        "factories",
        "video",
        "output-verify",
        backing_skill_ids=("ilaios.skill.video.qa.evaluate",),
    ),
    _node(
        "factories",
        "research",
        "planning",
        backing_skill_ids=("ilaios-research-planning",),
    ),
    _node(
        "factories",
        "research",
        "research",
        backing_skill_ids=("ilaios-research",),
    ),
    _node(
        "factories",
        "research",
        "source-validation",
        backing_skill_ids=("ilaios-source-validation",),
    ),
    _node(
        "factories",
        "research",
        "contradiction-check",
        backing_skill_ids=("ilaios-contradiction-check",),
    ),
    _node(
        "factories",
        "research",
        "citation-validation",
        backing_skill_ids=("ilaios-citation-validation",),
    ),
    _node(
        "factories",
        "research",
        "synthesis",
        backing_skill_ids=("ilaios-research-synthesis",),
    ),
    _node(
        "capabilities",
        "browser",
        "navigate",
        backing_skill_ids=("ilaios-browser",),
    ),
    _node(
        "capabilities",
        "browser",
        "inspect",
        backing_skill_ids=("ilaios-browser",),
    ),
    _node(
        "capabilities",
        "browser",
        "automate",
        backing_skill_ids=("ilaios-browser-automate",),
    ),
    _node(
        "capabilities",
        "browser",
        "e2e",
        backing_skill_ids=("ilaios-web-e2e",),
    ),
    _node(
        "capabilities",
        "browser",
        "visual-qa",
        backing_skill_ids=("ilaios-visual-qa",),
    ),
    _node(
        "capabilities",
        "browser",
        "production-verify",
        backing_skill_ids=("ilaios-production-verification",),
    ),
    _node(
        "assurance",
        "security-review",
        backing_skill_ids=(_SECURITY_REVIEW_SKILL_ID, "sf-security-review"),
    ),
    _node(
        "assurance",
        "differential-review",
        backing_skill_ids=(_DIFFERENTIAL_REVIEW_SKILL_ID,),
    ),
    _node(
        "assurance",
        "agentic-action-audit",
        backing_skill_ids=(_AGENTIC_ACTION_AUDIT_SKILL_ID,),
    ),
    _node(
        "assurance",
        "threat-model",
        backing_skill_ids=(_THREAT_MODEL_SKILL_ID,),
    ),
    _node(
        "assurance",
        "supply-chain-audit",
        backing_skill_ids=(
            _SUPPLY_CHAIN_AUDIT_SKILL_ID,
            "sf-dependency-governance",
            "sf-license-provenance",
        ),
    ),
    _node(
        "assurance",
        "dependency-audit",
        backing_skill_ids=("sf-dependency-governance",),
    ),
    _node(
        "assurance",
        "release-readiness",
        backing_skill_ids=("sf-release-readiness",),
    ),
)


def resolve_logical_skill(logical_id: str) -> SkillTaxonomyNode:
    for node in SKILL_TAXONOMY:
        if node.logical_id == logical_id:
            return node
    raise KeyError(f"unknown ILAIOS logical skill: {logical_id}")


def nodes_for_prefix(prefix: str) -> tuple[SkillTaxonomyNode, ...]:
    normalized = prefix.rstrip("/")
    return tuple(
        node
        for node in SKILL_TAXONOMY
        if node.logical_id == normalized
        or node.logical_id.startswith(normalized + "/")
    )


def validate_skill_taxonomy() -> None:
    logical_ids = [node.logical_id for node in SKILL_TAXONOMY]
    if len(logical_ids) != len(set(logical_ids)):
        raise ValueError("ILAIOS skill taxonomy logical IDs must be unique")

    runtime_skill_ids = (
        set(REQUIRED_SKILL_IDS)
        | set(WEB_FACTORY_NATIVE_SKILL_IDS)
        | set(WEB_FACTORY_BROWSER_SKILL_IDS)
        | set(_SKILL_ENGINEERING_RUNTIME_SKILL_IDS)
        | set(_SECURITY_METHODOLOGY_SKILL_IDS)
        | set(_VIDEO_RUNTIME_SKILL_IDS)
        | set(_RESEARCH_RUNTIME_SKILL_IDS)
    )
    for node in SKILL_TAXONOMY:
        if node.layer not in _ALLOWED_LAYERS:
            raise ValueError(f"invalid ILAIOS skill layer: {node.layer}")
        if not all(_SEGMENT.fullmatch(segment) for segment in node.path):
            raise ValueError(f"invalid ILAIOS skill path: {node.logical_id}")
        if _PROTECTED_AUTHORITY_SEGMENTS.intersection(node.path):
            raise ValueError(
                f"skill taxonomy cannot own protected Core authority: {node.logical_id}"
            )
        if node.layer in {"skill-engineering", "assurance"} and len(node.path) != 2:
            raise ValueError(f"invalid two-level taxonomy node: {node.logical_id}")
        if node.layer == "factories":
            if len(node.path) != 3 or node.path[1] not in _ALLOWED_FACTORY_FAMILIES:
                raise ValueError(f"invalid factory skill node: {node.logical_id}")
        if node.layer == "capabilities":
            if (
                len(node.path) != 3
                or node.path[1] not in _ALLOWED_CAPABILITY_FAMILIES
            ):
                raise ValueError(f"invalid capability skill node: {node.logical_id}")
        unknown_backing = set(node.backing_skill_ids) - runtime_skill_ids
        if unknown_backing:
            raise ValueError(
                f"unknown existing runtime skill mapping for {node.logical_id}: "
                f"{sorted(unknown_backing)}"
            )


validate_skill_taxonomy()
