"""Validation and output-quality gates for ILAIOS diagram design."""

from __future__ import annotations

import re
from dataclasses import dataclass

from .models import DiagramKind, DiagramSpec


class DiagramValidationError(ValueError):
    """The requested diagram violates an ILAIOS skill contract."""


@dataclass(frozen=True, slots=True)
class ComplexityBudget:
    max_nodes: int
    max_edges: int
    max_focal_nodes: int = 2


_BUDGETS: dict[DiagramKind, ComplexityBudget] = {
    DiagramKind.ARCHITECTURE: ComplexityBudget(12, 18),
    DiagramKind.FLOWCHART: ComplexityBudget(12, 16),
    DiagramKind.SEQUENCE: ComplexityBudget(6, 16),
    DiagramKind.STATE_MACHINE: ComplexityBudget(10, 16),
    DiagramKind.DATA_FLOW: ComplexityBudget(12, 18),
    DiagramKind.DEPENDENCY: ComplexityBudget(12, 18),
    DiagramKind.TRUST_BOUNDARY: ComplexityBudget(12, 18),
    DiagramKind.CAPABILITY_MAP: ComplexityBudget(12, 18),
}

_NODE_ID = re.compile(r"^[A-Za-z][A-Za-z0-9._-]{0,63}$")
_HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")
_PROHIBITED_SVG = (
    "<script",
    "<foreignobject",
    "<filter",
    "<lineargradient",
    "<radialgradient",
    "javascript:",
    "url(http",
    'href="http',
    "xlink:href=",
)


def _has_control_characters(value: str) -> bool:
    return any(ord(char) < 32 and char not in "\t\n\r" for char in value)


def validate_spec(spec: DiagramSpec) -> None:
    """Fail closed before layout or rendering."""

    if not spec.title.strip() or len(spec.title) > 120:
        raise DiagramValidationError("title must contain 1-120 characters")
    if len(spec.description) > 320:
        raise DiagramValidationError("description must be at most 320 characters")
    if spec.width < 640 or spec.width > 1920 or spec.width % 8:
        raise DiagramValidationError("width must be an 8px-grid value between 640 and 1920")
    if spec.height < 480 or spec.height > 1200 or spec.height % 8:
        raise DiagramValidationError("height must be an 8px-grid value between 480 and 1200")
    if not spec.nodes:
        raise DiagramValidationError("at least one node is required")

    budget = _BUDGETS[spec.kind]
    if len(spec.nodes) > budget.max_nodes:
        raise DiagramValidationError(
            f"{spec.kind.value} supports at most {budget.max_nodes} nodes"
        )
    if len(spec.edges) > budget.max_edges:
        raise DiagramValidationError(
            f"{spec.kind.value} supports at most {budget.max_edges} edges"
        )

    ids = [node.node_id for node in spec.nodes]
    if len(ids) != len(set(ids)):
        raise DiagramValidationError("node IDs must be unique")
    if any(not _NODE_ID.fullmatch(node_id) for node_id in ids):
        raise DiagramValidationError("node IDs must be stable ASCII identifiers")

    focal_count = sum(1 for node in spec.nodes if node.focal)
    if focal_count > budget.max_focal_nodes:
        raise DiagramValidationError(
            f"at most {budget.max_focal_nodes} focal nodes are allowed"
        )

    known = set(ids)
    for node in spec.nodes:
        if not node.label.strip() or len(node.label) > 56:
            raise DiagramValidationError(
                f"node {node.node_id!r} label must contain 1-56 characters"
            )
        if len(node.subtitle) > 88:
            raise DiagramValidationError(
                f"node {node.node_id!r} subtitle must be at most 88 characters"
            )
        if len(node.kind) > 24 or len(node.details) > 6:
            raise DiagramValidationError(f"node {node.node_id!r} is over detail budget")
        if node.group is not None and len(node.group) > 48:
            raise DiagramValidationError(
                f"node {node.node_id!r} group must be at most 48 characters"
            )
        for value in (node.label, node.subtitle, node.kind, *(node.details)):
            if _has_control_characters(value):
                raise DiagramValidationError(
                    f"node {node.node_id!r} contains unsupported control characters"
                )
            if len(value) > 88:
                raise DiagramValidationError(
                    f"node {node.node_id!r} detail must be at most 88 characters"
                )

    for edge in spec.edges:
        if edge.source not in known or edge.target not in known:
            raise DiagramValidationError(
                f"edge {edge.source!r}->{edge.target!r} references an unknown node"
            )
        if len(edge.label) > 40:
            raise DiagramValidationError("edge labels must be at most 40 characters")
        if _has_control_characters(edge.label):
            raise DiagramValidationError("edge label contains control characters")

    for token in (
        spec.theme.background,
        spec.theme.surface,
        spec.theme.surface_alt,
        spec.theme.text,
        spec.theme.muted,
        spec.theme.accent,
        spec.theme.border,
        spec.theme.danger,
    ):
        if not _HEX.fullmatch(token):
            raise DiagramValidationError(f"invalid theme token: {token}")


def validate_svg(svg: str) -> tuple[str, ...]:
    """Validate the generated artifact without executing it."""

    lowered = svg.casefold()
    if not lowered.startswith("<svg"):
        raise DiagramValidationError("artifact is not a standalone SVG")
    for prohibited in _PROHIBITED_SVG:
        if prohibited in lowered:
            raise DiagramValidationError(
                f"generated SVG contains prohibited construct: {prohibited}"
            )
    if 'role="img"' not in svg or "aria-labelledby=" not in svg:
        raise DiagramValidationError("SVG accessibility metadata is missing")
    if "<title " not in svg or "<desc " not in svg:
        raise DiagramValidationError("SVG title/description metadata is missing")

    return (
        "standalone-svg",
        "accessible-title-desc",
        "no-script-or-foreign-object",
        "no-gradients-filters-or-external-assets",
        "ilaios-flat-vector-policy",
    )
