"""Deterministic 8px-grid layout for graph-like ILAIOS diagrams."""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass

from .models import DiagramSpec, Direction


@dataclass(frozen=True, slots=True)
class NodeBox:
    x: int
    y: int
    width: int
    height: int

    @property
    def center_x(self) -> int:
        return self.x + self.width // 2

    @property
    def center_y(self) -> int:
        return self.y + self.height // 2


@dataclass(frozen=True, slots=True)
class GraphLayout:
    boxes: dict[str, NodeBox]
    ranks: dict[str, int]


def _snap(value: float) -> int:
    return max(0, int(round(value / 8.0)) * 8)


def _node_height(detail_count: int) -> int:
    return _snap(88 + detail_count * 16)


def _ranks(spec: DiagramSpec) -> dict[str, int]:
    ids = sorted(node.node_id for node in spec.nodes)
    outgoing: dict[str, list[str]] = {node_id: [] for node_id in ids}
    indegree: dict[str, int] = {node_id: 0 for node_id in ids}
    rank: dict[str, int] = {node_id: 0 for node_id in ids}

    for edge in spec.edges:
        outgoing[edge.source].append(edge.target)
        indegree[edge.target] += 1

    queue: deque[str] = deque(sorted(node_id for node_id in ids if indegree[node_id] == 0))
    visited: set[str] = set()
    while queue:
        source = queue.popleft()
        visited.add(source)
        for target in sorted(outgoing[source]):
            rank[target] = max(rank[target], rank[source] + 1)
            indegree[target] -= 1
            if indegree[target] == 0:
                queue.append(target)

    remaining = [node_id for node_id in ids if node_id not in visited]
    if remaining:
        base = max(rank.values(), default=0) + 1
        for index, node_id in enumerate(remaining):
            rank[node_id] = base + index // 4

    return rank


def build_graph_layout(spec: DiagramSpec) -> GraphLayout:
    """Place nodes deterministically; same spec means same coordinates."""

    ranks = _ranks(spec)
    by_rank: dict[int, list[str]] = defaultdict(list)
    by_id = {node.node_id: node for node in spec.nodes}
    for node_id, rank in ranks.items():
        by_rank[rank].append(node_id)
    for members in by_rank.values():
        members.sort()

    margin_x = 72
    margin_top = 112
    margin_bottom = 64
    max_rank = max(by_rank, default=0)
    rank_count = max_rank + 1
    preferred_gap = 56
    available_for_nodes = spec.width - margin_x * 2 - preferred_gap * max(rank_count - 1, 0)
    node_width = max(128, min(192, _snap(available_for_nodes / max(rank_count, 1))))

    boxes: dict[str, NodeBox] = {}
    if spec.direction is Direction.LEFT_TO_RIGHT:
        usable_w = spec.width - margin_x * 2 - node_width
        rank_gap = usable_w / max(max_rank, 1)
        usable_h = spec.height - margin_top - margin_bottom
        for rank, members in sorted(by_rank.items()):
            x = _snap(margin_x + rank * rank_gap)
            heights = [_node_height(len(by_id[node_id].details)) for node_id in members]
            total_h = sum(heights)
            gap = max(24, _snap((usable_h - total_h) / max(len(members) + 1, 1)))
            y = margin_top + gap
            for node_id, height in zip(members, heights, strict=True):
                boxes[node_id] = NodeBox(x=x, y=_snap(y), width=node_width, height=height)
                y += height + gap
    else:
        usable_h = spec.height - margin_top - margin_bottom - 80
        rank_gap = usable_h / max(max_rank, 1)
        usable_w = spec.width - margin_x * 2
        for rank, members in sorted(by_rank.items()):
            y = _snap(margin_top + rank * rank_gap)
            heights = [_node_height(len(by_id[node_id].details)) for node_id in members]
            box_h = max(heights, default=72)
            total_w = len(members) * node_width
            gap = max(24, _snap((usable_w - total_w) / max(len(members) + 1, 1)))
            x = margin_x + gap
            for node_id in members:
                boxes[node_id] = NodeBox(
                    x=_snap(x),
                    y=y,
                    width=node_width,
                    height=box_h,
                )
                x += node_width + gap

    return GraphLayout(boxes=boxes, ranks=ranks)


def attach_point(
    box: NodeBox,
    position: int,
    count: int,
    direction: Direction,
    *,
    source: bool,
) -> tuple[int, int]:
    """Fan connector attach points across the relevant node edge."""

    if direction is Direction.LEFT_TO_RIGHT:
        y = box.y + (box.height * position) // (count + 1)
        x = box.x + box.width if source else box.x
        return _snap(x), _snap(y)

    x = box.x + (box.width * position) // (count + 1)
    y = box.y + box.height if source else box.y
    return _snap(x), _snap(y)
