"""Canonical logical taxonomy for first-party ILAIOS skills.

This module is intentionally not an executor. It classifies skills and maps
logical taxonomy nodes to existing governed runtime skill IDs without moving,
rewriting, or bypassing the canonical Core/runtime boundaries.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final

from services.software_factory_skills import REQUIRED_SKILL_IDS

_ALLOWED_LAYERS: Final = frozenset(
    {"skill-engineering", "factories", "capabilities", "assurance"}
)
_ALLOWED_FACTORY_FAMILIES: Final = frozenset(
    {"web", "software", "video", "research"}
)
_ALLOWED_CAPABILITY_FAMILIES: Final = frozenset({"browser"})
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
    An empty tuple means the logical node is target taxonomy only; it does not
    imply implementation, runtime integration, verification, or production.
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
    _node("skill-engineering", "create"),
    _node("skill-engineering", "lint"),
    _node("skill-engineering", "validate"),
    _node("skill-engineering", "security-scan"),
    _node("skill-engineering", "evaluate"),
    _node("skill-engineering", "benchmark"),
    _node("skill-engineering", "regression"),
    _node("skill-engineering", "compatibility"),
    _node("skill-engineering", "promote"),
    _node("factories", "web", "architecture"),
    _node("factories", "web", "design"),
    _node("factories", "web", "build"),
    _node("factories", "web", "accessibility"),
    _node("factories", "web", "performance"),
    _node("factories", "web", "test"),
    _node("factories", "web", "production-qa"),
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
    _node("factories", "video", "director"),
    _node("factories", "video", "prompt"),
    _node("factories", "video", "reference-assets"),
    _node("factories", "video", "continuity"),
    _node("factories", "video", "generation"),
    _node("factories", "video", "edit"),
    _node("factories", "video", "captions"),
    _node("factories", "video", "composition"),
    _node("factories", "video", "render"),
    _node("factories", "video", "output-verify"),
    _node("factories", "research", "planning"),
    _node("factories", "research", "research"),
    _node("factories", "research", "source-validation"),
    _node("factories", "research", "contradiction-check"),
    _node("factories", "research", "citation-validation"),
    _node("factories", "research", "synthesis"),
    _node("capabilities", "browser", "navigate"),
    _node("capabilities", "browser", "inspect"),
    _node("capabilities", "browser", "automate"),
    _node("capabilities", "browser", "e2e"),
    _node("capabilities", "browser", "visual-qa"),
    _node("capabilities", "browser", "production-verify"),
    _node(
        "assurance",
        "security-review",
        backing_skill_ids=("sf-security-review",),
    ),
    _node("assurance", "differential-review"),
    _node("assurance", "threat-model"),
    _node(
        "assurance",
        "supply-chain-audit",
        backing_skill_ids=("sf-dependency-governance", "sf-license-provenance"),
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

    software_skill_ids = set(REQUIRED_SKILL_IDS)
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
        unknown_backing = set(node.backing_skill_ids) - software_skill_ids
        if unknown_backing:
            raise ValueError(
                f"unknown existing runtime skill mapping for {node.logical_id}: "
                f"{sorted(unknown_backing)}"
            )


validate_skill_taxonomy()
