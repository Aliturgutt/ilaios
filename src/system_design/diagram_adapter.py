"""Schema bridge from ILAIOS system-design artifacts to diagram-design specs."""

from __future__ import annotations

from typing import Any

from src.ilaios_diagram_design import (
    DiagramEdge,
    DiagramKind,
    DiagramNode,
    DiagramSpec,
    Direction,
    EdgeKind,
    RenderArtifact,
    render_diagram,
    validate_spec,
)

_NODE_LABELS = {
    "edge-gateway": "Edge Gateway",
    "rate-limiter": "Rate Limiter",
    "application": "Application",
    "primary-database": "Primary Database",
    "database-replica": "Database Replica",
    "observability": "Observability",
    "cache": "Cache",
    "work-queue": "Work Queue",
    "async-worker": "Async Worker",
}
_EDGE_KINDS = {
    "control_flow": EdgeKind.DEFAULT,
    "data_flow": EdgeKind.DEFAULT,
    "telemetry": EdgeKind.ASYNC,
    "replication": EdgeKind.ACCENT,
}


def architecture_to_diagram_spec(
    architecture: dict[str, Any], *, dark_mode: bool = False
) -> DiagramSpec:
    """Convert the renderer-neutral architecture schema to a validated spec."""
    if architecture.get("schema_version") != "1.0":
        raise ValueError("unsupported system-design architecture schema version")
    system_id = architecture.get("system_id")
    raw_nodes = architecture.get("nodes")
    raw_edges = architecture.get("edges")
    if not isinstance(system_id, str) or not system_id.strip():
        raise ValueError("architecture requires a system_id")
    if not isinstance(raw_nodes, list) or not isinstance(raw_edges, list):
        raise ValueError("architecture nodes and edges must be arrays")
    spec = DiagramSpec(
        title=f"{system_id} — System Architecture",
        description=(
            "ILAIOS system-design output. Capacity decisions remain estimates until "
            "representative load and failure evidence exists."
        ),
        kind=DiagramKind.ARCHITECTURE,
        nodes=tuple(_convert_node(node) for node in raw_nodes),
        edges=tuple(_convert_edge(edge) for edge in raw_edges),
        width=1200,
        height=720,
        direction=Direction.LEFT_TO_RIGHT,
        dark_mode=dark_mode,
    )
    validate_spec(spec)
    return spec


def render_architecture_diagram(
    architecture: dict[str, Any], *, dark_mode: bool = False
) -> RenderArtifact:
    """Render a system-design artifact through existing diagram-design."""
    return render_diagram(
        architecture_to_diagram_spec(architecture, dark_mode=dark_mode)
    )


def _convert_node(raw: Any) -> DiagramNode:
    if not isinstance(raw, dict):
        raise ValueError("architecture node must be an object")
    node_id = raw.get("id")
    kind = raw.get("kind")
    layer = raw.get("layer")
    failure_domain = raw.get("failure_domain")
    values = (node_id, kind, layer, failure_domain)
    if not all(isinstance(value, str) and value.strip() for value in values):
        raise ValueError("architecture node fields must be non-empty strings")
    assert isinstance(node_id, str)
    assert isinstance(kind, str)
    assert isinstance(layer, str)
    assert isinstance(failure_domain, str)
    label = _NODE_LABELS.get(node_id, node_id.replace("-", " ").title())
    return DiagramNode(
        node_id=node_id,
        label=label,
        subtitle=f"{layer} · failure domain: {failure_domain}",
        kind=kind[:24],
        group=layer,
        focal=node_id == "application",
        details=(f"stateful={bool(raw.get('stateful'))}",),
    )


def _convert_edge(raw: Any) -> DiagramEdge:
    if not isinstance(raw, dict):
        raise ValueError("architecture edge must be an object")
    source = raw.get("from")
    target = raw.get("to")
    kind = raw.get("kind")
    values = (source, target, kind)
    if not all(isinstance(value, str) and value.strip() for value in values):
        raise ValueError("architecture edge fields must be non-empty strings")
    assert isinstance(source, str)
    assert isinstance(target, str)
    assert isinstance(kind, str)
    return DiagramEdge(
        source=source,
        target=target,
        label=kind.replace("_", " "),
        kind=_EDGE_KINDS.get(kind, EdgeKind.DEFAULT),
    )
