from __future__ import annotations

import pytest

from src.code_intelligence import (
    Certainty,
    CodeIntelligenceEngine,
    CodeIntelligenceGraphBuilder,
    CodeIntelligenceQueryError,
    DependencyEdge,
    FileKind,
    GraphEdgeKind,
    GraphNodeKind,
    Language,
    QueryLimits,
    RepositorySnapshot,
    SourceFileRecord,
    SourceLocation,
    SymbolRecord,
    SymbolType,
)


def _snapshot() -> RepositorySnapshot:
    files = (
        SourceFileRecord(
            "pyproject.toml",
            None,
            FileKind.MANIFEST,
            None,
            None,
            False,
            Certainty.KNOWN,
        ),
        SourceFileRecord(
            "src/a.py",
            Language.PYTHON,
            FileKind.SOURCE,
            "src.a",
            "src",
            False,
            Certainty.KNOWN,
        ),
        SourceFileRecord(
            "src/b.py",
            Language.PYTHON,
            FileKind.SOURCE,
            "src.b",
            "src",
            False,
            Certainty.KNOWN,
        ),
        SourceFileRecord(
            "tests/test_a.py",
            Language.PYTHON,
            FileKind.TEST,
            "tests.test_a",
            "tests",
            False,
            Certainty.KNOWN,
        ),
        SourceFileRecord(
            "web/app.ts",
            Language.TYPESCRIPT,
            FileKind.SOURCE,
            None,
            "web",
            False,
            Certainty.KNOWN,
        ),
    )
    symbols = (
        SymbolRecord(
            "function:src/a.py:src.a.caller",
            "caller",
            "src.a.caller",
            SymbolType.FUNCTION,
            SourceLocation("src/a.py", 3),
            Language.PYTHON,
            True,
            references=("target",),
        ),
        SymbolRecord(
            "api_route:src/a.py:GET /health",
            "GET /health",
            "src.a.GET /health",
            SymbolType.API_ROUTE,
            SourceLocation("src/a.py", 10),
            Language.PYTHON,
            True,
            certainty=Certainty.INFERRED,
        ),
        SymbolRecord(
            "function:src/a.py:src.a.health",
            "health",
            "src.a.health",
            SymbolType.FUNCTION,
            SourceLocation("src/a.py", 10),
            Language.PYTHON,
            True,
        ),
        SymbolRecord(
            "function:src/a.py:src.a._orphan",
            "_orphan",
            "src.a._orphan",
            SymbolType.FUNCTION,
            SourceLocation("src/a.py", 20),
            Language.PYTHON,
            False,
        ),
        SymbolRecord(
            "function:src/b.py:src.b.target",
            "target",
            "src.b.target",
            SymbolType.FUNCTION,
            SourceLocation("src/b.py", 4),
            Language.PYTHON,
            True,
        ),
    )
    dependencies = (
        DependencyEdge("src/a.py", "src/b.py", "imports", Certainty.KNOWN),
        DependencyEdge(
            "tests/test_a.py",
            "src/a.py",
            "imports",
            Certainty.KNOWN,
        ),
        DependencyEdge(
            "pyproject.toml",
            "package:requests",
            "declares_dependency",
            Certainty.KNOWN,
        ),
    )
    return RepositorySnapshot(
        root="/repo",
        revision="abc123",
        files=files,
        symbols=symbols,
        dependencies=dependencies,
        test_mappings=(),
        api_routes=("GET /health",),
        schema_entities=(),
        manifests=("pyproject.toml",),
        configurations=(),
        unknowns=("semantic certainty limited for web/app.ts",),
    )


def _engine() -> CodeIntelligenceEngine:
    return CodeIntelligenceEngine(CodeIntelligenceGraphBuilder().build(_snapshot()))


def test_graph_generation_is_deterministic() -> None:
    builder = CodeIntelligenceGraphBuilder()

    first = builder.build(_snapshot())
    second = builder.build(_snapshot())

    assert first == second
    assert first.generation_id == second.generation_id
    assert first.schema_version == "ilaios-code-intelligence-graph-v1"


def test_graph_contains_typed_dependency_and_call_edges() -> None:
    index = CodeIntelligenceGraphBuilder().build(_snapshot())

    kinds = {edge.kind for edge in index.edges}
    node_kinds = {node.kind for node in index.nodes}

    assert GraphEdgeKind.CONTAINS in kinds
    assert GraphEdgeKind.IMPORTS in kinds
    assert GraphEdgeKind.DECLARES_DEPENDENCY in kinds
    assert GraphEdgeKind.CALLS in kinds
    assert GraphNodeKind.EXTERNAL_DEPENDENCY in node_kinds


def test_call_resolution_prefers_unique_repository_symbol() -> None:
    engine = _engine()

    trace = engine.trace_call_graph("src.a.caller")
    target = engine.search_symbols("src.b.target")[0]

    assert target.node_id in trace.node_ids
    assert len(trace.edge_ids) == 1


def test_ambiguous_call_is_not_materialized_as_fact() -> None:
    snapshot = _snapshot()
    duplicate = SymbolRecord(
        "function:src/a.py:src.a.target",
        "target",
        "src.a.target",
        SymbolType.FUNCTION,
        SourceLocation("src/a.py", 30),
        Language.PYTHON,
        True,
    )
    ambiguous_caller = SymbolRecord(
        "function:web/app.ts:web.caller",
        "webCaller",
        "web.caller",
        SymbolType.FUNCTION,
        SourceLocation("web/app.ts", 2),
        Language.TYPESCRIPT,
        True,
        references=("target",),
        certainty=Certainty.INFERRED,
    )
    replaced = RepositorySnapshot(
        root=snapshot.root,
        revision=snapshot.revision,
        files=snapshot.files,
        symbols=(*snapshot.symbols, duplicate, ambiguous_caller),
        dependencies=snapshot.dependencies,
        test_mappings=snapshot.test_mappings,
        api_routes=snapshot.api_routes,
        schema_entities=snapshot.schema_entities,
        manifests=snapshot.manifests,
        configurations=snapshot.configurations,
        unknowns=snapshot.unknowns,
    )

    index = CodeIntelligenceGraphBuilder().build(replaced)
    caller = next(
        node
        for node in index.nodes
        if node.qualified_name == "web.caller"
    )
    caller_edges = [
        edge
        for edge in index.edges
        if edge.source_id == caller.node_id and edge.kind is GraphEdgeKind.CALLS
    ]

    assert caller_edges == []
    assert any("ambiguous call reference" in item for item in index.unknowns)


def test_symbol_search_is_ranked_and_bounded() -> None:
    engine = _engine()

    hits = engine.search_symbols("target", limit=1)

    assert len(hits) == 1
    assert hits[0].qualified_name == "src.b.target"
    assert hits[0].score == 110


def test_dependency_analysis_supports_reverse_blast_radius() -> None:
    engine = _engine()

    trace = engine.dependency_analysis("src/a.py", reverse=True)
    test_node = next(
        node
        for node in engine.index.nodes
        if node.path == "tests/test_a.py" and node.kind is GraphNodeKind.FILE
    )

    assert test_node.node_id in trace.node_ids
    assert trace.direction == "incoming"


def test_route_analysis_correlates_same_location_handler() -> None:
    result = _engine().route_analysis("/health")

    assert len(result.route_node_ids) == 1
    assert len(result.handler_node_ids) == 1
    assert result.certainty is Certainty.INFERRED
    assert result.unknowns == ()


def test_dead_code_is_advisory_and_conservative() -> None:
    candidates = _engine().dead_code_candidates()

    assert [candidate.qualified_name for candidate in candidates] == [
        "src.a._orphan"
    ]
    assert candidates[0].certainty is Certainty.INFERRED
    assert "may still exist" in candidates[0].rationale


def test_coverage_separates_semantic_and_structural_analysis() -> None:
    coverage = _engine().coverage()

    assert coverage.total_files == 5
    assert coverage.analyzable_source_files == 4
    assert coverage.semantic_files == 3
    assert coverage.structural_files == 1
    assert coverage.semantic_ratio == pytest.approx(0.75)
    assert coverage.unknown_facts == 1


def test_architecture_map_reports_cross_component_dependencies() -> None:
    result = _engine().architecture_map()

    component_names = {component.name for component in result.components}
    cross = {
        (dependency.source_component, dependency.target_component)
        for dependency in result.dependencies
    }

    assert {"<root>", "src", "tests", "web"} <= component_names
    assert ("tests", "src") in cross


def test_query_limits_reject_unbounded_depth() -> None:
    engine = CodeIntelligenceEngine(
        CodeIntelligenceGraphBuilder().build(_snapshot()),
        limits=QueryLimits(max_depth=2),
    )

    with pytest.raises(CodeIntelligenceQueryError, match="max_depth"):
        engine.trace_call_graph("src.a.caller", max_depth=3)


def test_missing_or_ambiguous_symbols_fail_closed() -> None:
    engine = _engine()

    with pytest.raises(CodeIntelligenceQueryError, match="absent"):
        engine.trace_call_graph("does_not_exist")
