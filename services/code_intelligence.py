"""Governed Software Factory adapter for first-party ILAIOS code intelligence."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from src.code_intelligence.engine import CodeIntelligenceEngine
from src.code_intelligence.graph import CodeIntelligenceGraphBuilder
from src.code_intelligence.models import RepositorySnapshot
from src.code_intelligence.repository_analyzer import RepositoryAnalyzer


class CodeIntelligenceAdmissionError(ValueError):
    """Repository intelligence cannot safely bind to the requested revision."""


@dataclass(frozen=True, slots=True)
class CodeIntelligenceSession:
    """Immutable snapshot/index/query bundle for one admitted repository revision."""

    snapshot: RepositorySnapshot
    engine: CodeIntelligenceEngine


class ILAIOSRepositoryIntelligence:
    """First-party implementation of the SF-7 RepositoryIntelligencePort.

    The adapter is deliberately read-only. It verifies the repository revision,
    builds a deterministic in-memory graph, and returns bounded evidence. More
    specific queries use ``session`` and the typed ``CodeIntelligenceEngine``.
    """

    def session(self, repository: Path, base_sha: str) -> CodeIntelligenceSession:
        """Create a revision-bound read-only intelligence session."""

        root = repository.resolve()
        if not root.is_dir() or root.is_symlink():
            raise CodeIntelligenceAdmissionError(
                "repository must be a regular directory"
            )
        if len(base_sha) != 40 or any(character not in "0123456789abcdef" for character in base_sha):
            raise CodeIntelligenceAdmissionError(
                "base_sha must be a lowercase 40-character SHA-1"
            )
        snapshot = RepositoryAnalyzer(root).snapshot()
        if snapshot.revision != base_sha:
            raise CodeIntelligenceAdmissionError(
                "repository revision does not match requested base_sha"
            )
        index = CodeIntelligenceGraphBuilder().build(snapshot)
        return CodeIntelligenceSession(
            snapshot=snapshot,
            engine=CodeIntelligenceEngine(index),
        )

    def inspect(self, repository: Path, base_sha: str) -> Mapping[str, object]:
        """Return stable evidence compatible with the canonical SF-7 port."""

        session = self.session(repository, base_sha)
        index = session.engine.index
        coverage = index.coverage
        architecture = session.engine.architecture_map()
        return {
            "schema_version": "ilaios-code-intelligence-evidence-v1",
            "repository_revision": index.revision,
            "generation_id": index.generation_id,
            "graph_schema_version": index.schema_version,
            "node_count": len(index.nodes),
            "edge_count": len(index.edges),
            "coverage": {
                "total_files": coverage.total_files,
                "analyzable_source_files": coverage.analyzable_source_files,
                "semantic_files": coverage.semantic_files,
                "structural_files": coverage.structural_files,
                "generated_files": coverage.generated_files,
                "unknown_facts": coverage.unknown_facts,
                "semantic_ratio": coverage.semantic_ratio,
            },
            "architecture": {
                "components": [
                    {
                        "name": component.name,
                        "files": list(component.files),
                        "symbol_count": component.symbol_count,
                    }
                    for component in architecture.components
                ],
                "dependencies": [
                    {
                        "source_component": dependency.source_component,
                        "target_component": dependency.target_component,
                        "edge_count": dependency.edge_count,
                    }
                    for dependency in architecture.dependencies
                ],
            },
            "unknowns": list(index.unknowns),
        }
