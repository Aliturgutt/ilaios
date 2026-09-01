"""Deterministic, read-only graph construction for ILAIOS code intelligence.

The graph is derived exclusively from a ``RepositorySnapshot``. It performs no
repository I/O, network access, shell execution, persistence, or mutation.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum

from src.code_intelligence.models import (
    Certainty,
    FileKind,
    RepositorySnapshot,
    SymbolRecord,
    SymbolType,
)

_GRAPH_SCHEMA_VERSION = "ilaios-code-intelligence-graph-v1"
_CALLABLE_SYMBOL_TYPES = frozenset(
    {SymbolType.CLASS, SymbolType.FUNCTION, SymbolType.METHOD}
)


class GraphNodeKind(str, Enum):
    """Node classes exposed by the governed code-intelligence graph."""

    FILE = "file"
    SYMBOL = "symbol"
    EXTERNAL_DEPENDENCY = "external_dependency"


class GraphEdgeKind(str, Enum):
    """Typed, auditable relationships represented in the graph."""

    CONTAINS = "contains"
    PARENT = "parent"
    IMPORTS = "imports"
    DECLARES_DEPENDENCY = "declares_dependency"
    DEPENDS_ON = "depends_on"
    CALLS = "calls"


@dataclass(frozen=True, slots=True)
class GraphNode:
    """Immutable graph node with only deterministic source-derived fields."""

    node_id: str
    kind: GraphNodeKind
    label: str
    path: str | None
    qualified_name: str | None
    symbol_type: SymbolType | None
    line: int | None
    public: bool | None
    certainty: Certainty


@dataclass(frozen=True, slots=True)
class GraphEdge:
    """Immutable relationship with evidence strength inherited from analysis."""

    edge_id: str
    source_id: str
    target_id: str
    kind: GraphEdgeKind
    certainty: Certainty
    evidence: str


@dataclass(frozen=True, slots=True)
class IndexCoverage:
    """Explicit coverage facts; never imply unsupported semantic coverage."""

    total_files: int
    analyzable_source_files: int
    semantic_files: int
    structural_files: int
    generated_files: int
    unknown_facts: int

    @property
    def semantic_ratio(self) -> float:
        """Return semantic coverage over analyzable source/test files."""

        if self.analyzable_source_files == 0:
            return 1.0
        return self.semantic_files / self.analyzable_source_files


@dataclass(frozen=True, slots=True)
class CodeIntelligenceIndex:
    """Immutable graph generation bound to one repository snapshot revision."""

    repository_root: str
    revision: str
    schema_version: str
    generation_id: str
    nodes: tuple[GraphNode, ...]
    edges: tuple[GraphEdge, ...]
    coverage: IndexCoverage
    unknowns: tuple[str, ...]


class CodeIntelligenceGraphBuilder:
    """Build an in-memory graph without widening repository trust boundaries."""

    def build(self, snapshot: RepositorySnapshot) -> CodeIntelligenceIndex:
        """Create a deterministic graph from a previously governed snapshot."""

        nodes: dict[str, GraphNode] = {}
        edges: dict[str, GraphEdge] = {}
        unknowns = set(snapshot.unknowns)
        file_node_ids: dict[str, str] = {}
        symbol_node_ids: dict[str, str] = {}

        for file_record in snapshot.files:
            node_id = _stable_id("file", file_record.path)
            file_node_ids[file_record.path] = node_id
            nodes[node_id] = GraphNode(
                node_id=node_id,
                kind=GraphNodeKind.FILE,
                label=file_record.path,
                path=file_record.path,
                qualified_name=None,
                symbol_type=None,
                line=None,
                public=None,
                certainty=file_record.certainty,
            )

        for symbol in snapshot.symbols:
            node_id = _stable_id("symbol", symbol.symbol_id)
            symbol_node_ids[symbol.symbol_id] = node_id
            nodes[node_id] = GraphNode(
                node_id=node_id,
                kind=GraphNodeKind.SYMBOL,
                label=symbol.name,
                path=symbol.location.path,
                qualified_name=symbol.qualified_name,
                symbol_type=symbol.symbol_type,
                line=symbol.location.line,
                public=symbol.public,
                certainty=symbol.certainty,
            )
            file_node_id = file_node_ids.get(symbol.location.path)
            if file_node_id is None:
                unknowns.add(
                    f"symbol source file is absent from snapshot: {symbol.symbol_id}"
                )
            else:
                _add_edge(
                    edges,
                    file_node_id,
                    node_id,
                    GraphEdgeKind.CONTAINS,
                    symbol.certainty,
                    f"symbol:{symbol.symbol_id}",
                )

        for symbol in snapshot.symbols:
            if symbol.parent_symbol_id is None:
                continue
            source_id = symbol_node_ids.get(symbol.parent_symbol_id)
            target_id = symbol_node_ids.get(symbol.symbol_id)
            if source_id is None or target_id is None:
                unknowns.add(
                    f"symbol parent could not be resolved: {symbol.symbol_id}"
                )
                continue
            _add_edge(
                edges,
                source_id,
                target_id,
                GraphEdgeKind.PARENT,
                symbol.certainty,
                f"parent:{symbol.parent_symbol_id}",
            )

        for dependency in snapshot.dependencies:
            source_id = file_node_ids.get(dependency.source)
            if source_id is None:
                unknowns.add(
                    f"dependency source file is absent from snapshot: {dependency.source}"
                )
                continue
            target_id = file_node_ids.get(dependency.target)
            if target_id is None:
                target_id = _external_dependency_node_id(dependency.target)
                nodes.setdefault(
                    target_id,
                    GraphNode(
                        node_id=target_id,
                        kind=GraphNodeKind.EXTERNAL_DEPENDENCY,
                        label=dependency.target,
                        path=None,
                        qualified_name=None,
                        symbol_type=None,
                        line=None,
                        public=None,
                        certainty=dependency.certainty,
                    ),
                )
            _add_edge(
                edges,
                source_id,
                target_id,
                _dependency_edge_kind(dependency.relationship),
                dependency.certainty,
                (
                    f"dependency:{dependency.source}:"
                    f"{dependency.relationship}:{dependency.target}"
                ),
            )

        self._add_call_edges(snapshot.symbols, symbol_node_ids, edges, unknowns)
        coverage = _coverage(snapshot, len(unknowns))
        ordered_nodes = tuple(sorted(nodes.values(), key=lambda item: item.node_id))
        ordered_edges = tuple(sorted(edges.values(), key=lambda item: item.edge_id))
        ordered_unknowns = tuple(sorted(unknowns))
        generation_id = _generation_id(
            snapshot.revision,
            ordered_nodes,
            ordered_edges,
            ordered_unknowns,
        )
        return CodeIntelligenceIndex(
            repository_root=snapshot.root,
            revision=snapshot.revision,
            schema_version=_GRAPH_SCHEMA_VERSION,
            generation_id=generation_id,
            nodes=ordered_nodes,
            edges=ordered_edges,
            coverage=coverage,
            unknowns=ordered_unknowns,
        )

    def _add_call_edges(
        self,
        symbols: tuple[SymbolRecord, ...],
        symbol_node_ids: dict[str, str],
        edges: dict[str, GraphEdge],
        unknowns: set[str],
    ) -> None:
        callable_symbols = tuple(
            symbol
            for symbol in symbols
            if symbol.symbol_type in _CALLABLE_SYMBOL_TYPES
        )
        by_name: dict[str, list[SymbolRecord]] = {}
        by_qualified_name: dict[str, list[SymbolRecord]] = {}
        for symbol in callable_symbols:
            by_name.setdefault(symbol.name, []).append(symbol)
            by_qualified_name.setdefault(symbol.qualified_name, []).append(symbol)

        for caller in callable_symbols:
            source_id = symbol_node_ids.get(caller.symbol_id)
            if source_id is None:
                continue
            for reference in caller.references:
                if reference == "<dynamic>":
                    unknowns.add(
                        f"dynamic call cannot be resolved: {caller.symbol_id}"
                    )
                    continue
                target, ambiguous = _resolve_call_reference(
                    caller,
                    reference,
                    by_name,
                    by_qualified_name,
                )
                if ambiguous:
                    unknowns.add(
                        f"ambiguous call reference: {caller.symbol_id} -> {reference}"
                    )
                    continue
                if target is None:
                    continue
                target_id = symbol_node_ids.get(target.symbol_id)
                if target_id is None:
                    continue
                certainty = _minimum_certainty(caller.certainty, target.certainty)
                _add_edge(
                    edges,
                    source_id,
                    target_id,
                    GraphEdgeKind.CALLS,
                    certainty,
                    f"call:{caller.symbol_id}:{reference}",
                )


def _resolve_call_reference(
    caller: SymbolRecord,
    reference: str,
    by_name: dict[str, list[SymbolRecord]],
    by_qualified_name: dict[str, list[SymbolRecord]],
) -> tuple[SymbolRecord | None, bool]:
    exact_qualified = by_qualified_name.get(reference, [])
    if len(exact_qualified) == 1:
        return exact_qualified[0], False
    if len(exact_qualified) > 1:
        return None, True

    if "." in reference:
        suffix_matches = [
            symbol
            for qualified_name, symbols in by_qualified_name.items()
            if qualified_name.endswith(f".{reference}")
            for symbol in symbols
        ]
        if len(suffix_matches) == 1:
            return suffix_matches[0], False
        if len(suffix_matches) > 1:
            return None, True
        return None, False

    named = by_name.get(reference, [])
    same_file = [
        symbol
        for symbol in named
        if symbol.location.path == caller.location.path
    ]
    if len(same_file) == 1:
        return same_file[0], False
    if len(same_file) > 1:
        return None, True
    if len(named) == 1:
        return named[0], False
    if len(named) > 1:
        return None, True
    return None, False


def _coverage(snapshot: RepositorySnapshot, unknown_count: int) -> IndexCoverage:
    analyzable = [
        file_record
        for file_record in snapshot.files
        if file_record.kind in {FileKind.SOURCE, FileKind.TEST}
        and not file_record.generated
        and file_record.language is not None
    ]
    semantic = [
        file_record
        for file_record in analyzable
        if file_record.language is not None
        and file_record.language.value == "python"
    ]
    structural = [
        file_record
        for file_record in analyzable
        if file_record.language is not None
        and file_record.language.value != "python"
    ]
    return IndexCoverage(
        total_files=len(snapshot.files),
        analyzable_source_files=len(analyzable),
        semantic_files=len(semantic),
        structural_files=len(structural),
        generated_files=sum(file_record.generated for file_record in snapshot.files),
        unknown_facts=unknown_count,
    )


def _dependency_edge_kind(relationship: str) -> GraphEdgeKind:
    normalized = relationship.casefold()
    if normalized == "imports":
        return GraphEdgeKind.IMPORTS
    if normalized == "declares_dependency":
        return GraphEdgeKind.DECLARES_DEPENDENCY
    return GraphEdgeKind.DEPENDS_ON


def _external_dependency_node_id(target: str) -> str:
    return _stable_id("external", target)


def _add_edge(
    edges: dict[str, GraphEdge],
    source_id: str,
    target_id: str,
    kind: GraphEdgeKind,
    certainty: Certainty,
    evidence: str,
) -> None:
    edge_id = _stable_id("edge", source_id, target_id, kind.value, evidence)
    edges[edge_id] = GraphEdge(
        edge_id=edge_id,
        source_id=source_id,
        target_id=target_id,
        kind=kind,
        certainty=certainty,
        evidence=evidence,
    )


def _minimum_certainty(left: Certainty, right: Certainty) -> Certainty:
    rank = {
        Certainty.UNKNOWN: 0,
        Certainty.INFERRED: 1,
        Certainty.KNOWN: 2,
    }
    return left if rank[left] <= rank[right] else right


def _stable_id(prefix: str, *parts: str) -> str:
    payload = "\x1f".join((prefix, *parts)).encode("utf-8")
    return f"{prefix}:{hashlib.sha256(payload).hexdigest()[:24]}"


def _generation_id(
    revision: str,
    nodes: tuple[GraphNode, ...],
    edges: tuple[GraphEdge, ...],
    unknowns: tuple[str, ...],
) -> str:
    payload = {
        "schema_version": _GRAPH_SCHEMA_VERSION,
        "revision": revision,
        "nodes": [
            {
                "id": node.node_id,
                "kind": node.kind.value,
                "label": node.label,
                "path": node.path,
                "qualified_name": node.qualified_name,
                "symbol_type": (
                    None if node.symbol_type is None else node.symbol_type.value
                ),
                "line": node.line,
                "public": node.public,
                "certainty": node.certainty.value,
            }
            for node in nodes
        ],
        "edges": [
            {
                "id": edge.edge_id,
                "source": edge.source_id,
                "target": edge.target_id,
                "kind": edge.kind.value,
                "certainty": edge.certainty.value,
                "evidence": edge.evidence,
            }
            for edge in edges
        ],
        "unknowns": list(unknowns),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(encoded).hexdigest()
