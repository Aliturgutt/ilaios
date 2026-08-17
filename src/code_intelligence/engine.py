"""Bounded, typed queries over an ILAIOS code-intelligence graph."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Literal

from src.code_intelligence.graph import (
    CodeIntelligenceIndex,
    GraphEdge,
    GraphEdgeKind,
    GraphNode,
    GraphNodeKind,
    IndexCoverage,
)
from src.code_intelligence.models import Certainty, SymbolType

_CALLABLE_SYMBOL_TYPES = frozenset(
    {SymbolType.CLASS, SymbolType.FUNCTION, SymbolType.METHOD}
)
_DEPENDENCY_EDGE_KINDS = frozenset(
    {
        GraphEdgeKind.IMPORTS,
        GraphEdgeKind.DECLARES_DEPENDENCY,
        GraphEdgeKind.DEPENDS_ON,
    }
)


class CodeIntelligenceQueryError(ValueError):
    """A query is invalid, ambiguous, or outside the bounded contract."""


@dataclass(frozen=True, slots=True)
class QueryLimits:
    """Hard limits preventing unbounded graph expansion."""

    max_results: int = 100
    max_depth: int = 8
    max_visited_nodes: int = 5_000

    def __post_init__(self) -> None:
        if self.max_results < 1:
            raise ValueError("max_results must be positive")
        if self.max_depth < 1:
            raise ValueError("max_depth must be positive")
        if self.max_visited_nodes < 1:
            raise ValueError("max_visited_nodes must be positive")


@dataclass(frozen=True, slots=True)
class SymbolSearchHit:
    node_id: str
    name: str
    qualified_name: str
    path: str
    line: int
    symbol_type: SymbolType
    certainty: Certainty
    score: int


@dataclass(frozen=True, slots=True)
class GraphTraversal:
    origin_node_id: str
    direction: str
    node_ids: tuple[str, ...]
    edge_ids: tuple[str, ...]
    truncated: bool


@dataclass(frozen=True, slots=True)
class ArchitectureComponent:
    name: str
    files: tuple[str, ...]
    symbol_count: int


@dataclass(frozen=True, slots=True)
class ArchitectureDependency:
    source_component: str
    target_component: str
    edge_count: int


@dataclass(frozen=True, slots=True)
class ArchitectureMap:
    components: tuple[ArchitectureComponent, ...]
    dependencies: tuple[ArchitectureDependency, ...]


@dataclass(frozen=True, slots=True)
class RouteAnalysis:
    query: str
    route_node_ids: tuple[str, ...]
    handler_node_ids: tuple[str, ...]
    certainty: Certainty
    unknowns: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class DeadCodeCandidate:
    node_id: str
    qualified_name: str
    path: str
    line: int
    certainty: Certainty
    rationale: str


class CodeIntelligenceEngine:
    """Execute explicit read-only operations against one immutable index."""

    def __init__(
        self,
        index: CodeIntelligenceIndex,
        *,
        limits: QueryLimits | None = None,
    ) -> None:
        self._index = index
        self._limits = limits or QueryLimits()
        self._nodes = {node.node_id: node for node in index.nodes}
        self._edges = {edge.edge_id: edge for edge in index.edges}
        self._outgoing: dict[str, tuple[GraphEdge, ...]] = {}
        self._incoming: dict[str, tuple[GraphEdge, ...]] = {}
        outgoing_lists: dict[str, list[GraphEdge]] = {}
        incoming_lists: dict[str, list[GraphEdge]] = {}
        for edge in index.edges:
            outgoing_lists.setdefault(edge.source_id, []).append(edge)
            incoming_lists.setdefault(edge.target_id, []).append(edge)
        self._outgoing = {
            node_id: tuple(sorted(edges, key=lambda edge: edge.edge_id))
            for node_id, edges in outgoing_lists.items()
        }
        self._incoming = {
            node_id: tuple(sorted(edges, key=lambda edge: edge.edge_id))
            for node_id, edges in incoming_lists.items()
        }

    @property
    def index(self) -> CodeIntelligenceIndex:
        return self._index

    def coverage(self) -> IndexCoverage:
        """Return explicit semantic/structural coverage without inference."""

        return self._index.coverage

    def search_symbols(
        self,
        query: str,
        *,
        limit: int = 20,
    ) -> tuple[SymbolSearchHit, ...]:
        """Search symbols deterministically; no embeddings or fuzzy LLM matching."""

        normalized = query.strip().casefold()
        if not normalized:
            raise CodeIntelligenceQueryError("symbol query must not be empty")
        bounded_limit = self._bounded_limit(limit)
        hits: list[SymbolSearchHit] = []
        for node in self._index.nodes:
            if node.kind is not GraphNodeKind.SYMBOL:
                continue
            if (
                node.qualified_name is None
                or node.path is None
                or node.line is None
                or node.symbol_type is None
            ):
                continue
            score = _symbol_score(node, normalized)
            if score == 0:
                continue
            hits.append(
                SymbolSearchHit(
                    node_id=node.node_id,
                    name=node.label,
                    qualified_name=node.qualified_name,
                    path=node.path,
                    line=node.line,
                    symbol_type=node.symbol_type,
                    certainty=node.certainty,
                    score=score,
                )
            )
        hits.sort(
            key=lambda hit: (
                -hit.score,
                hit.qualified_name.casefold(),
                hit.path,
                hit.line,
                hit.node_id,
            )
        )
        return tuple(hits[:bounded_limit])

    def trace_call_graph(
        self,
        symbol: str,
        *,
        direction: Literal["callers", "callees"] = "callees",
        max_depth: int = 4,
    ) -> GraphTraversal:
        """Traverse only statically resolved CALLS edges under hard limits."""

        origin = self._resolve_symbol(symbol)
        return self._traverse(
            origin.node_id,
            direction,
            frozenset({GraphEdgeKind.CALLS}),
            max_depth,
        )

    def dependency_analysis(
        self,
        path: str,
        *,
        reverse: bool = False,
        max_depth: int = 4,
    ) -> GraphTraversal:
        """Trace file/package dependencies or reverse dependents."""

        origin = self._resolve_file(path)
        direction = "incoming" if reverse else "outgoing"
        return self._traverse(
            origin.node_id,
            direction,
            _DEPENDENCY_EDGE_KINDS,
            max_depth,
        )

    def architecture_map(self) -> ArchitectureMap:
        """Summarize top-level repository components and cross-component edges."""

        files_by_component: dict[str, list[str]] = {}
        symbol_count: dict[str, int] = {}
        component_by_node: dict[str, str] = {}
        component_by_path: dict[str, str] = {}
        for node in self._index.nodes:
            if node.kind is not GraphNodeKind.FILE or node.path is None:
                continue
            component = _component(node.path)
            files_by_component.setdefault(component, []).append(node.path)
            component_by_node[node.node_id] = component
            component_by_path[node.path] = component

        for node in self._index.nodes:
            if node.kind is not GraphNodeKind.SYMBOL or node.path is None:
                continue
            symbol_component = component_by_path.get(node.path)
            if symbol_component is not None:
                symbol_count[symbol_component] = symbol_count.get(symbol_component, 0) + 1

        components = tuple(
            ArchitectureComponent(
                name=name,
                files=tuple(sorted(paths)),
                symbol_count=symbol_count.get(name, 0),
            )
            for name, paths in sorted(files_by_component.items())
        )

        cross_counts: dict[tuple[str, str], int] = {}
        for edge in self._index.edges:
            if edge.kind not in _DEPENDENCY_EDGE_KINDS:
                continue
            source_component = component_by_node.get(edge.source_id)
            target_component = component_by_node.get(edge.target_id)
            if (
                source_component is None
                or target_component is None
                or source_component == target_component
            ):
                continue
            key = (source_component, target_component)
            cross_counts[key] = cross_counts.get(key, 0) + 1

        dependencies = tuple(
            ArchitectureDependency(source, target, count)
            for (source, target), count in sorted(cross_counts.items())
        )
        return ArchitectureMap(components, dependencies)

    def route_analysis(self, route: str) -> RouteAnalysis:
        """Correlate known route symbols with same-location handler symbols."""

        normalized = route.strip().casefold()
        if not normalized:
            raise CodeIntelligenceQueryError("route query must not be empty")
        route_nodes = tuple(
            node
            for node in self._index.nodes
            if node.kind is GraphNodeKind.SYMBOL
            and node.symbol_type is SymbolType.API_ROUTE
            and normalized in node.label.casefold()
        )
        handler_ids: set[str] = set()
        for route_node in route_nodes:
            for node in self._index.nodes:
                if (
                    node.kind is GraphNodeKind.SYMBOL
                    and node.symbol_type in {SymbolType.FUNCTION, SymbolType.METHOD}
                    and node.path == route_node.path
                    and node.line == route_node.line
                ):
                    handler_ids.add(node.node_id)

        unknowns: list[str] = []
        if not route_nodes:
            unknowns.append(f"route is absent from index: {route}")
        elif not handler_ids:
            unknowns.append(f"route handler could not be correlated: {route}")

        certainty = _combined_certainty(tuple(node.certainty for node in route_nodes))
        if unknowns:
            certainty = Certainty.UNKNOWN
        return RouteAnalysis(
            query=route,
            route_node_ids=tuple(sorted(node.node_id for node in route_nodes)),
            handler_node_ids=tuple(sorted(handler_ids)),
            certainty=certainty,
            unknowns=tuple(unknowns),
        )

    def dead_code_candidates(
        self,
        *,
        limit: int = 100,
    ) -> tuple[DeadCodeCandidate, ...]:
        """Return conservative candidates, never deletion-safe assertions."""

        bounded_limit = self._bounded_limit(limit)
        incoming_call_targets = {
            edge.target_id
            for edge in self._index.edges
            if edge.kind is GraphEdgeKind.CALLS
        }
        route_locations = {
            (node.path, node.line)
            for node in self._index.nodes
            if node.kind is GraphNodeKind.SYMBOL
            and node.symbol_type is SymbolType.API_ROUTE
        }
        candidates: list[DeadCodeCandidate] = []
        for node in self._index.nodes:
            if (
                node.kind is not GraphNodeKind.SYMBOL
                or node.symbol_type not in _CALLABLE_SYMBOL_TYPES
                or node.public is not False
                or node.node_id in incoming_call_targets
                or node.path is None
                or node.line is None
                or node.qualified_name is None
                or node.label.startswith("__")
                or (node.path, node.line) in route_locations
            ):
                continue
            candidates.append(
                DeadCodeCandidate(
                    node_id=node.node_id,
                    qualified_name=node.qualified_name,
                    path=node.path,
                    line=node.line,
                    certainty=Certainty.INFERRED,
                    rationale=(
                        "no statically resolved incoming call; dynamic, reflection, "
                        "framework, or external entry points may still exist"
                    ),
                )
            )
        candidates.sort(
            key=lambda candidate: (
                candidate.path,
                candidate.line,
                candidate.qualified_name,
                candidate.node_id,
            )
        )
        return tuple(candidates[:bounded_limit])

    def _resolve_symbol(self, query: str) -> GraphNode:
        normalized = query.strip()
        if not normalized:
            raise CodeIntelligenceQueryError("symbol must not be empty")
        exact = [
            node
            for node in self._index.nodes
            if node.kind is GraphNodeKind.SYMBOL
            and (node.node_id == normalized or node.qualified_name == normalized)
        ]
        if len(exact) == 1:
            return exact[0]
        if len(exact) > 1:
            raise CodeIntelligenceQueryError(f"symbol is ambiguous: {query}")
        named = [
            node
            for node in self._index.nodes
            if node.kind is GraphNodeKind.SYMBOL and node.label == normalized
        ]
        if len(named) == 1:
            return named[0]
        if not named:
            raise CodeIntelligenceQueryError(f"symbol is absent from index: {query}")
        raise CodeIntelligenceQueryError(f"symbol is ambiguous: {query}")

    def _resolve_file(self, path: str) -> GraphNode:
        normalized = path.strip().replace("\\", "/")
        if not normalized:
            raise CodeIntelligenceQueryError("path must not be empty")
        matches = [
            node
            for node in self._index.nodes
            if node.kind is GraphNodeKind.FILE and node.path == normalized
        ]
        if len(matches) != 1:
            raise CodeIntelligenceQueryError(f"file is absent from index: {path}")
        return matches[0]

    def _traverse(
        self,
        origin_id: str,
        direction: str,
        edge_kinds: frozenset[GraphEdgeKind],
        max_depth: int,
    ) -> GraphTraversal:
        if max_depth < 1 or max_depth > self._limits.max_depth:
            raise CodeIntelligenceQueryError(
                f"max_depth must be between 1 and {self._limits.max_depth}"
            )
        if direction not in {"callers", "callees", "incoming", "outgoing"}:
            raise CodeIntelligenceQueryError(
                f"unsupported traversal direction: {direction}"
            )

        reverse = direction in {"callers", "incoming"}
        queue: deque[tuple[str, int]] = deque([(origin_id, 0)])
        visited_nodes = {origin_id}
        visited_edges: set[str] = set()
        truncated = False

        while queue:
            node_id, depth = queue.popleft()
            if depth >= max_depth:
                continue
            adjacent = (
                self._incoming.get(node_id, ())
                if reverse
                else self._outgoing.get(node_id, ())
            )
            for edge in adjacent:
                if edge.kind not in edge_kinds:
                    continue
                next_id = edge.source_id if reverse else edge.target_id
                visited_edges.add(edge.edge_id)
                if next_id in visited_nodes:
                    continue
                if len(visited_nodes) >= self._limits.max_visited_nodes:
                    truncated = True
                    queue.clear()
                    break
                visited_nodes.add(next_id)
                queue.append((next_id, depth + 1))

        return GraphTraversal(
            origin_node_id=origin_id,
            direction=direction,
            node_ids=tuple(sorted(visited_nodes)),
            edge_ids=tuple(sorted(visited_edges)),
            truncated=truncated,
        )

    def _bounded_limit(self, requested: int) -> int:
        if requested < 1:
            raise CodeIntelligenceQueryError("limit must be positive")
        return min(requested, self._limits.max_results)


def _symbol_score(node: GraphNode, normalized_query: str) -> int:
    name = node.label.casefold()
    qualified = (node.qualified_name or "").casefold()
    if qualified == normalized_query:
        return 120
    if name == normalized_query:
        return 110
    if name.startswith(normalized_query):
        return 90
    if qualified.startswith(normalized_query):
        return 80
    if normalized_query in name:
        return 60
    if normalized_query in qualified:
        return 50
    return 0


def _component(path: str) -> str:
    if "/" not in path:
        return "<root>"
    return path.split("/", 1)[0]


def _combined_certainty(values: tuple[Certainty, ...]) -> Certainty:
    if not values:
        return Certainty.UNKNOWN
    if Certainty.UNKNOWN in values:
        return Certainty.UNKNOWN
    if Certainty.INFERRED in values:
        return Certainty.INFERRED
    return Certainty.KNOWN
