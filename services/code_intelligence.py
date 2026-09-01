"""Governed Software Factory adapter for first-party ILAIOS code intelligence."""

from __future__ import annotations

import subprocess
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from src.code_intelligence.engine import CodeIntelligenceEngine
from src.code_intelligence.graph import CodeIntelligenceGraphBuilder
from src.code_intelligence.models import RepositorySnapshot
from src.code_intelligence.repository_analyzer import RepositoryAnalyzer

_GIT_TIMEOUT_SECONDS = 10.0


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
    requires snapshot inputs to be clean tracked files, builds a deterministic
    in-memory graph, and returns bounded evidence. More specific queries use
    ``session`` and the typed ``CodeIntelligenceEngine``.
    """

    def session(self, repository: Path, base_sha: str) -> CodeIntelligenceSession:
        """Create a revision-bound read-only intelligence session."""

        if repository.is_symlink():
            raise CodeIntelligenceAdmissionError(
                "repository must not be a symbolic link"
            )
        root = repository.resolve()
        if not root.is_dir():
            raise CodeIntelligenceAdmissionError(
                "repository must be a regular directory"
            )
        if len(base_sha) != 40 or any(
            character not in "0123456789abcdef" for character in base_sha
        ):
            raise CodeIntelligenceAdmissionError(
                "base_sha must be a lowercase 40-character SHA-1"
            )

        repository_root = _git_text(root, "rev-parse", "--show-toplevel")
        if Path(repository_root).resolve() != root:
            raise CodeIntelligenceAdmissionError(
                "repository must be the Git worktree root"
            )
        head_sha = _git_text(root, "rev-parse", "HEAD")
        if head_sha != base_sha:
            raise CodeIntelligenceAdmissionError(
                "repository revision does not match requested base_sha"
            )
        _require_clean_worktree(root)
        tracked_files = _tracked_files(root)

        snapshot = RepositoryAnalyzer(root).snapshot()

        if snapshot.revision != base_sha:
            raise CodeIntelligenceAdmissionError(
                "repository revision changed during analysis"
            )
        untracked_snapshot_files = sorted(
            file_record.path
            for file_record in snapshot.files
            if file_record.path not in tracked_files
        )
        if untracked_snapshot_files:
            raise CodeIntelligenceAdmissionError(
                "snapshot contains files not tracked by requested revision: "
                + ", ".join(untracked_snapshot_files[:10])
            )
        _require_clean_worktree(root)
        if _git_text(root, "rev-parse", "HEAD") != base_sha:
            raise CodeIntelligenceAdmissionError(
                "repository revision changed during analysis"
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


def _git_output(root: Path, *arguments: str, strip: bool) -> str:
    try:
        completed = subprocess.run(
            (
                "git",
                "-c",
                "core.fsmonitor=false",
                "-c",
                "core.untrackedCache=false",
                *arguments,
            ),
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
            timeout=_GIT_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise CodeIntelligenceAdmissionError(
            "repository Git verification failed"
        ) from exc
    if completed.returncode != 0:
        raise CodeIntelligenceAdmissionError(
            "repository Git verification failed"
        )
    return completed.stdout.strip() if strip else completed.stdout


def _git_text(root: Path, *arguments: str) -> str:
    return _git_output(root, *arguments, strip=True)


def _tracked_files(root: Path) -> frozenset[str]:
    output = _git_output(root, "ls-files", "-z", strip=False)
    return frozenset(path for path in output.split("\0") if path)


def _require_clean_worktree(root: Path) -> None:
    status = _git_text(
        root,
        "status",
        "--porcelain=v1",
        "--untracked-files=all",
        "--ignore-submodules=all",
    )
    if status:
        raise CodeIntelligenceAdmissionError(
            "repository worktree must be clean for revision-bound analysis"
        )
