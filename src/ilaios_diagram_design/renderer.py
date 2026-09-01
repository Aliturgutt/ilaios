"""Self-contained SVG renderer for the ILAIOS diagram-design skill."""

from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from dataclasses import asdict, dataclass
from html import escape

from .layout import GraphLayout, NodeBox, attach_point, build_graph_layout
from .models import DiagramEdge, DiagramNode, DiagramSpec, Direction, EdgeKind
from .quality import validate_spec, validate_svg


@dataclass(frozen=True, slots=True)
class RenderArtifact:
    """Rendered diagram plus reproducible evidence hashes."""

    svg: str
    spec_sha256: str
    artifact_sha256: str
    checks: tuple[str, ...]


def _canonical_spec(spec: DiagramSpec) -> str:
    payload = {
        "title": spec.title,
        "description": spec.description,
        "kind": spec.kind.value,
        "nodes": [
            {
                "node_id": node.node_id,
                "label": node.label,
                "subtitle": node.subtitle,
                "kind": node.kind,
                "group": node.group,
                "focal": node.focal,
                "details": list(node.details),
            }
            for node in spec.nodes
        ],
        "edges": [
            {
                "source": edge.source,
                "target": edge.target,
                "label": edge.label,
                "kind": edge.kind.value,
            }
            for edge in spec.edges
        ],
        "width": spec.width,
        "height": spec.height,
        "direction": spec.direction.value,
        "dark_mode": spec.dark_mode,
        "theme": asdict(spec.theme),
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _marker_id(prefix: str, edge_kind: EdgeKind) -> str:
    if edge_kind is EdgeKind.ACCENT:
        return f"{prefix}-arrow-accent"
    if edge_kind is EdgeKind.FORBIDDEN:
        return f"{prefix}-arrow-danger"
    return f"{prefix}-arrow"


def _edge_stroke(spec: DiagramSpec, edge_kind: EdgeKind) -> tuple[str, str]:
    if edge_kind is EdgeKind.ACCENT:
        return spec.theme.accent, ""
    if edge_kind is EdgeKind.FORBIDDEN:
        return spec.theme.danger, "6 4"
    if edge_kind is EdgeKind.ASYNC:
        return spec.theme.muted, "6 4"
    return spec.theme.muted, ""


def _rounded_path_lr(
    start: tuple[int, int],
    end: tuple[int, int],
    *,
    lane: int,
) -> str:
    sx, sy = start
    tx, ty = end
    if sy == ty and tx > sx:
        return f"M {sx} {sy} H {tx}"

    if tx > sx + 32:
        mid_x = int(round(((sx + tx) / 2) / 8.0)) * 8
        radius = min(8, max(4, abs(ty - sy) // 2))
        vertical_sign = 1 if ty > sy else -1
        return (
            f"M {sx} {sy} "
            f"H {mid_x - radius} "
            f"Q {mid_x} {sy} {mid_x} {sy + vertical_sign * radius} "
            f"V {ty - vertical_sign * radius} "
            f"Q {mid_x} {ty} {mid_x + radius} {ty} "
            f"H {tx}"
        )

    lane_y = max(sy, ty) + 48 + lane * 16
    out_x = sx + 24 + lane * 8
    in_x = tx - 24 - lane * 8
    return (
        f"M {sx} {sy} H {out_x} "
        f"Q {out_x + 8} {sy} {out_x + 8} {sy + 8} "
        f"V {lane_y - 8} Q {out_x + 8} {lane_y} {out_x} {lane_y} "
        f"H {in_x} Q {in_x - 8} {lane_y} {in_x - 8} {lane_y - 8} "
        f"V {ty + 8} Q {in_x - 8} {ty} {in_x} {ty} H {tx}"
    )


def _rounded_path_tb(
    start: tuple[int, int],
    end: tuple[int, int],
    *,
    lane: int,
) -> str:
    sx, sy = start
    tx, ty = end
    if sx == tx and ty > sy:
        return f"M {sx} {sy} V {ty}"

    if ty > sy + 32:
        mid_y = int(round(((sy + ty) / 2) / 8.0)) * 8
        radius = min(8, max(4, abs(tx - sx) // 2))
        horizontal_sign = 1 if tx > sx else -1
        return (
            f"M {sx} {sy} "
            f"V {mid_y - radius} "
            f"Q {sx} {mid_y} {sx + horizontal_sign * radius} {mid_y} "
            f"H {tx - horizontal_sign * radius} "
            f"Q {tx} {mid_y} {tx} {mid_y + radius} "
            f"V {ty}"
        )

    lane_x = max(sx, tx) + 48 + lane * 16
    out_y = sy + 24 + lane * 8
    in_y = ty - 24 - lane * 8
    return (
        f"M {sx} {sy} V {out_y} "
        f"Q {sx} {out_y + 8} {sx + 8} {out_y + 8} "
        f"H {lane_x - 8} Q {lane_x} {out_y + 8} {lane_x} {out_y} "
        f"V {in_y} Q {lane_x} {in_y - 8} {lane_x - 8} {in_y - 8} "
        f"H {tx + 8} Q {tx} {in_y - 8} {tx} {in_y} V {ty}"
    )


def _edge_label(
    edge: DiagramEdge,
    start: tuple[int, int],
    end: tuple[int, int],
    spec: DiagramSpec,
    source_box: NodeBox,
    target_box: NodeBox,
) -> str:
    if not edge.label:
        return ""

    sx, sy = start
    tx, ty = end
    text = escape(edge.label)
    mask_width = max(40, min(176, len(edge.label) * 7 + 16))
    if spec.direction is Direction.LEFT_TO_RIGHT:
        x = int(round(((sx + tx) / 2) / 8.0)) * 8
        horizontal_gap = target_box.x - (source_box.x + source_box.width)
        if horizontal_gap < mask_width + 12:
            y = min(source_box.y, target_box.y) - 12
        else:
            y = min(sy, ty) - 14
    else:
        y = int(round(((sy + ty) / 2) / 8.0)) * 8
        vertical_gap = target_box.y - (source_box.y + source_box.height)
        if vertical_gap < 30:
            x = max(source_box.x + source_box.width, target_box.x + target_box.width) + mask_width // 2 + 12
        else:
            x = max(sx, tx) + 12

    return (
        f'<rect x="{x - mask_width // 2}" y="{y - 13}" width="{mask_width}" '
        f'height="18" rx="2" fill="{spec.theme.background}"/>'
        f'<text x="{x}" y="{y}" text-anchor="middle" '
        f'font-family="Sora, Segoe UI, Arial, sans-serif" font-size="10" '
        f'font-weight="600" fill="{spec.theme.muted}">{text}</text>'
    )


def _wrap_label(label: str, width: int) -> tuple[str, ...]:
    """Wrap a human-readable node label to at most two deterministic lines."""

    max_chars = max(12, min(24, (width - 24) // 8))
    if len(label) <= max_chars:
        return (label,)
    words = label.split()
    if len(words) <= 1:
        camel_words = re.split(r"(?<=[a-z0-9])(?=[A-Z])", label)
        if len(camel_words) > 1:
            words = camel_words
        else:
            return (label[:max_chars], label[max_chars:max_chars * 2])
    first: list[str] = []
    second: list[str] = []
    target = first
    for word in words:
        candidate = " ".join((*target, word))
        if target is first and len(candidate) > max_chars and first:
            target = second
            candidate = " ".join((*target, word))
        if target is second and len(candidate) > max_chars and second:
            second[-1] = (second[-1][: max(1, max_chars - 1)] + "…")
            break
        target.append(word)
    first_line = " ".join(first)
    second_line = " ".join(second)
    return (first_line,) if not second_line else (first_line, second_line)


def _node_svg(node: DiagramNode, box: NodeBox, spec: DiagramSpec) -> str:
    stroke = spec.theme.accent if node.focal else spec.theme.border
    fill = spec.theme.surface_alt if node.focal else spec.theme.surface
    label_fill = spec.theme.accent if node.focal else spec.theme.text
    tag = escape(node.kind.upper())
    label_lines = tuple(escape(line) for line in _wrap_label(node.label, box.width))
    subtitle = escape(node.subtitle)

    lines = [
        f'<g data-node-id="{escape(node.node_id)}">',
        f'<rect x="{box.x}" y="{box.y}" width="{box.width}" height="{box.height}" '
        f'rx="8" fill="{fill}" stroke="{stroke}" stroke-width="1.2"/>',
        f'<text x="{box.x + 14}" y="{box.y + 20}" '
        f'font-family="Sora, Segoe UI, Arial, sans-serif" font-size="8" '
        f'font-weight="700" letter-spacing="1.0" fill="{spec.theme.muted}">{tag}</text>',
    ]
    label_y = box.y + 42
    for line in label_lines:
        lines.append(
            f'<text x="{box.x + 14}" y="{label_y}" '
            f'font-family="Sora, Segoe UI, Arial, sans-serif" font-size="13" '
            f'font-weight="650" fill="{label_fill}">{line}</text>'
        )
        label_y += 16
    if subtitle:
        lines.append(
            f'<text x="{box.x + 14}" y="{label_y + 3}" '
            f'font-family="Sora, Segoe UI, Arial, sans-serif" font-size="9" '
            f'fill="{spec.theme.muted}">{subtitle}</text>'
        )
        label_y += 16
    detail_y = label_y + 5
    for detail in node.details:
        lines.append(
            f'<text x="{box.x + 16}" y="{detail_y}" '
            f'font-family="ui-monospace, SFMono-Regular, Consolas, monospace" '
            f'font-size="9" fill="{spec.theme.muted}">{escape(detail)}</text>'
        )
        detail_y += 16
    lines.append("</g>")
    return "".join(lines)


def _group_svg(layout: GraphLayout, spec: DiagramSpec) -> str:
    groups: dict[str, list[NodeBox]] = defaultdict(list)
    by_id = {node.node_id: node for node in spec.nodes}
    for node_id, box in layout.boxes.items():
        group = by_id[node_id].group
        if group:
            groups[group].append(box)

    result: list[str] = []
    for group_name, boxes in sorted(groups.items()):
        min_x = min(box.x for box in boxes) - 24
        min_y = min(box.y for box in boxes) - 32
        max_x = max(box.x + box.width for box in boxes) + 24
        max_y = max(box.y + box.height for box in boxes) + 24
        result.append(
            f'<g data-group="{escape(group_name)}">'
            f'<rect x="{min_x}" y="{min_y}" width="{max_x - min_x}" '
            f'height="{max_y - min_y}" rx="8" fill="none" '
            f'stroke="{spec.theme.accent}" stroke-width="1" stroke-dasharray="5 5"/>'
            f'<text x="{min_x + 12}" y="{min_y + 18}" '
            f'font-family="Sora, Segoe UI, Arial, sans-serif" font-size="10" '
            f'font-weight="700" fill="{spec.theme.accent}">{escape(group_name)}</text>'
            "</g>"
        )
    return "".join(result)


def _graph_svg(spec: DiagramSpec, prefix: str) -> str:
    layout = build_graph_layout(spec)
    source_indices: dict[str, list[int]] = defaultdict(list)
    target_indices: dict[str, list[int]] = defaultdict(list)
    for index, edge in enumerate(spec.edges):
        source_indices[edge.source].append(index)
        target_indices[edge.target].append(index)

    edge_parts: list[str] = []
    for index, edge in enumerate(spec.edges):
        source_box = layout.boxes[edge.source]
        target_box = layout.boxes[edge.target]
        source_list = source_indices[edge.source]
        target_list = target_indices[edge.target]
        source_position = source_list.index(index) + 1
        target_position = target_list.index(index) + 1
        start = attach_point(
            source_box,
            source_position,
            len(source_list),
            spec.direction,
            source=True,
        )
        end = attach_point(
            target_box,
            target_position,
            len(target_list),
            spec.direction,
            source=False,
        )
        path = (
            _rounded_path_lr(start, end, lane=index)
            if spec.direction is Direction.LEFT_TO_RIGHT
            else _rounded_path_tb(start, end, lane=index)
        )
        stroke, dash = _edge_stroke(spec, edge.kind)
        dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
        marker = _marker_id(prefix, edge.kind)
        edge_parts.append(
            f'<path d="{path}" fill="none" stroke="{stroke}" stroke-width="1.4"'
            f'{dash_attr} marker-end="url(#{marker})"/>'
        )
        edge_parts.append(_edge_label(edge, start, end, spec, source_box, target_box))

    node_parts = [
        _node_svg(node, layout.boxes[node.node_id], spec)
        for node in sorted(spec.nodes, key=lambda item: item.node_id)
    ]
    return _group_svg(layout, spec) + "".join(edge_parts) + "".join(node_parts)


def _sequence_svg(spec: DiagramSpec, prefix: str) -> str:
    nodes = sorted(spec.nodes, key=lambda item: item.node_id)
    margin_x = 80
    usable = spec.width - margin_x * 2
    actor_gap = usable / max(len(nodes), 1)
    actor_width = 160
    top_y = 120
    bottom_y = spec.height - 72
    centers: dict[str, int] = {}
    parts: list[str] = []

    for index, node in enumerate(nodes):
        center_x = int(round((margin_x + actor_gap * (index + 0.5)) / 8.0)) * 8
        centers[node.node_id] = center_x
        x = center_x - actor_width // 2
        parts.append(
            f'<line x1="{center_x}" y1="{top_y + 56}" x2="{center_x}" y2="{bottom_y}" '
            f'stroke="{spec.theme.border}" stroke-width="1" stroke-dasharray="4 5"/>'
        )
        parts.append(
            f'<rect x="{x}" y="{top_y}" width="{actor_width}" height="56" rx="8" '
            f'fill="{spec.theme.surface}" stroke="{spec.theme.border}" stroke-width="1.2"/>'
            f'<text x="{center_x}" y="{top_y + 24}" text-anchor="middle" '
            f'font-family="Sora, Segoe UI, Arial, sans-serif" font-size="13" '
            f'font-weight="650" fill="{spec.theme.text}">{escape(node.label)}</text>'
            f'<text x="{center_x}" y="{top_y + 42}" text-anchor="middle" '
            f'font-family="ui-monospace, SFMono-Regular, Consolas, monospace" '
            f'font-size="9" fill="{spec.theme.muted}">{escape(node.subtitle)}</text>'
        )

    message_y = top_y + 96
    for index, edge in enumerate(spec.edges):
        source_x = centers[edge.source]
        target_x = centers[edge.target]
        y = message_y + index * 40
        stroke, dash = _edge_stroke(spec, edge.kind)
        dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
        marker = _marker_id(prefix, edge.kind)
        parts.append(
            f'<line x1="{source_x}" y1="{y}" x2="{target_x}" y2="{y}" '
            f'stroke="{stroke}" stroke-width="1.4"{dash_attr} '
            f'marker-end="url(#{marker})"/>'
        )
        if edge.label:
            label_x = (source_x + target_x) // 2
            parts.append(
                f'<rect x="{label_x - 74}" y="{y - 22}" width="148" height="16" '
                f'rx="2" fill="{spec.theme.background}"/>'
                f'<text x="{label_x}" y="{y - 10}" text-anchor="middle" '
                f'font-family="Sora, Segoe UI, Arial, sans-serif" font-size="10" '
                f'font-weight="600" fill="{spec.theme.muted}">{escape(edge.label)}</text>'
            )
    return "".join(parts)


def _definitions(spec: DiagramSpec, prefix: str) -> str:
    return (
        "<defs>"
        f'<marker id="{prefix}-arrow" markerWidth="8" markerHeight="6" '
        'refX="7" refY="3" orient="auto">'
        f'<polygon points="0 0, 8 3, 0 6" fill="{spec.theme.muted}"/></marker>'
        f'<marker id="{prefix}-arrow-accent" markerWidth="8" markerHeight="6" '
        'refX="7" refY="3" orient="auto">'
        f'<polygon points="0 0, 8 3, 0 6" fill="{spec.theme.accent}"/></marker>'
        f'<marker id="{prefix}-arrow-danger" markerWidth="8" markerHeight="6" '
        'refX="7" refY="3" orient="auto">'
        f'<polygon points="0 0, 8 3, 0 6" fill="{spec.theme.danger}"/></marker>'
        "</defs>"
    )


def render_diagram(spec: DiagramSpec) -> RenderArtifact:
    """Validate, render, validate again, and emit evidence hashes."""

    validate_spec(spec)
    canonical = _canonical_spec(spec)
    spec_sha = _sha256_text(canonical)
    prefix = f"ilaios-{spec_sha[:10]}"
    title_id = f"{prefix}-title"
    desc_id = f"{prefix}-desc"

    body = (
        _sequence_svg(spec, prefix)
        if spec.kind.value == "sequence"
        else _graph_svg(spec, prefix)
    )
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{spec.width}" '
        f'height="{spec.height}" viewBox="0 0 {spec.width} {spec.height}" '
        f'role="img" aria-labelledby="{title_id} {desc_id}">'
        f'<title id="{title_id}">{escape(spec.title)}</title>'
        f'<desc id="{desc_id}">{escape(spec.description or spec.title)}</desc>'
        f'{_definitions(spec, prefix)}'
        f'<rect width="{spec.width}" height="{spec.height}" fill="{spec.theme.background}"/>'
        f'<text x="48" y="50" font-family="Sora, Segoe UI, Arial, sans-serif" '
        f'font-size="24" font-weight="700" fill="{spec.theme.text}">{escape(spec.title)}</text>'
        f'<text x="48" y="74" font-family="Sora, Segoe UI, Arial, sans-serif" '
        f'font-size="11" fill="{spec.theme.muted}">{escape(spec.description)}</text>'
        f"{body}</svg>"
    )
    checks = validate_svg(svg)
    artifact_sha = _sha256_text(svg)
    return RenderArtifact(
        svg=svg,
        spec_sha256=spec_sha,
        artifact_sha256=artifact_sha,
        checks=checks,
    )


def wrap_html(artifact: RenderArtifact, *, page_title: str) -> str:
    """Wrap a validated SVG in dependency-free HTML."""

    title = escape(page_title)
    return (
        "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>{title}</title>"
        "<style>"
        "html,body{margin:0;padding:0;background:#fff}"
        "main{display:grid;min-height:100vh;place-items:center;padding:24px;box-sizing:border-box}"
        "svg{max-width:100%;height:auto}"
        "</style></head><body><main>"
        f"{artifact.svg}"
        "</main></body></html>"
    )
