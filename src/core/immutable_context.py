"""Immutable Context for Core Initialization.

Implements ExecutionContext with immutable fields and path resolution.

"""
from pathlib import Path

from .bootstrap_validator import ContextError


class ExecutionContext:
    """Immutable execution context for core initialization."""

    def __init__(
        self,
        git_root: Path,
        branch: str,
        head_sha: str,
        origin_url: str,
    ) -> None:
        self._git_root = git_root
        self._branch = branch
        self._head_sha = head_sha
        self._origin_url = origin_url

    @property
    def git_root(self) -> Path:
        return self._git_root

    @property
    def branch(self) -> str:
        return self._branch

    @property
    def head_sha(self) -> str:
        return self._head_sha

    @property
    def origin_url(self) -> str:
        return self._origin_url

    def resolve_path(self, path: str | Path) -> Path:
        """Resolve path and ensure it stays within git_root."""
        target = (self._git_root / path).resolve()
        if not target.is_relative_to(self._git_root):
            raise ContextError("Path escapes repository root")
        return target
