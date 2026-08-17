from __future__ import annotations

from src.code_intelligence import (
    Certainty,
    CodeIntelligenceGraphBuilder,
    FileKind,
    GraphEdgeKind,
    Language,
    RepositorySnapshot,
    SourceFileRecord,
    SourceLocation,
    SymbolRecord,
    SymbolType,
)


def _snapshot(reference: str) -> RepositorySnapshot:
    files = (
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
    )
    symbols = (
        SymbolRecord(
            "function:src/a.py:src.a.caller",
            "caller",
            "src.a.caller",
            SymbolType.FUNCTION,
            SourceLocation("src/a.py", 1),
            Language.PYTHON,
            True,
            references=(reference,),
        ),
        SymbolRecord(
            "function:src/a.py:src.a.target",
            "target",
            "src.a.target",
            SymbolType.FUNCTION,
            SourceLocation("src/a.py", 5),
            Language.PYTHON,
            True,
        ),
        SymbolRecord(
            "function:src/b.py:src.b.service.target",
            "target",
            "src.b.service.target",
            SymbolType.FUNCTION,
            SourceLocation("src/b.py", 5),
            Language.PYTHON,
            True,
        ),
    )
    return RepositorySnapshot(
        root="/repo",
        revision="abc123",
        files=files,
        symbols=symbols,
        dependencies=(),
        test_mappings=(),
        api_routes=(),
        schema_entities=(),
        manifests=(),
        configurations=(),
        unknowns=(),
    )


def _call_target_qualified_names(reference: str) -> set[str]:
    index = CodeIntelligenceGraphBuilder().build(_snapshot(reference))
    caller = next(
        node for node in index.nodes if node.qualified_name == "src.a.caller"
    )
    target_ids = {
        edge.target_id
        for edge in index.edges
        if edge.source_id == caller.node_id and edge.kind is GraphEdgeKind.CALLS
    }
    return {
        node.qualified_name
        for node in index.nodes
        if node.node_id in target_ids and node.qualified_name is not None
    }


def test_qualified_reference_resolves_only_unique_qualified_suffix() -> None:
    assert _call_target_qualified_names("service.target") == {
        "src.b.service.target"
    }


def test_unresolved_qualified_reference_does_not_fall_back_to_leaf_name() -> None:
    assert _call_target_qualified_names("foreign.target") == set()
