"""Tests for ExecutionContext immutable foundation."""
import tempfile
from pathlib import Path

import pytest

from src.core.bootstrap_validator import ContextError
from src.core.immutable_context import ExecutionContext


def test_construction() -> None:
    """Test ExecutionContext construction with required fields."""
    git_root = Path("/tmp/test_repo")
    branch = "main"
    head_sha = "abc123"
    origin_url = "https://example.com/repo.git"

    ctx = ExecutionContext(git_root, branch, head_sha, origin_url)

    assert ctx.git_root == git_root
    assert ctx.branch == branch
    assert ctx.head_sha == head_sha
    assert ctx.origin_url == origin_url


def test_field_immutability() -> None:
    """Test that fields cannot be modified after construction."""
    ctx = ExecutionContext(Path("/tmp"), "main", "abc123", "https://example.com/repo.git")

    with pytest.raises(AttributeError):
        ctx.git_root = Path("/other")  # type: ignore[misc]
    with pytest.raises(AttributeError):
        ctx.branch = "dev"  # type: ignore[misc]
    with pytest.raises(AttributeError):
        ctx.head_sha = "def456"  # type: ignore[misc]
    with pytest.raises(AttributeError):
        ctx.origin_url = "https://example.com/other.git"  # type: ignore[misc]


def test_resolve_path_valid_internal() -> None:
    """Test resolve_path with paths inside git_root."""
    with tempfile.TemporaryDirectory() as tmpdir:
        git_root = Path(tmpdir)
        ctx = ExecutionContext(git_root, "main", "abc123", "https://example.com/repo.git")

        # Relative path
        internal = ctx.resolve_path("src/file.txt")
        assert internal == git_root / "src/file.txt"

        # Absolute path inside
        abs_internal = git_root / "subdir" / "file.txt"
        assert ctx.resolve_path(abs_internal) == abs_internal

        # Path with . and ..
        internal2 = ctx.resolve_path("subdir/../src/file.txt")
        assert internal2 == git_root / "src/file.txt"


def test_resolve_path_escape_rejection() -> None:
    """Test resolve_path rejects paths escaping git_root."""
    with tempfile.TemporaryDirectory() as tmpdir:
        git_root = Path(tmpdir)
        ctx = ExecutionContext(git_root, "main", "abc123", "https://example.com/repo.git")

        # Absolute path outside
        outside = Path("/etc/passwd")
        with pytest.raises(ContextError, match="escapes repository root"):
            ctx.resolve_path(outside)

        # Parent traversal from relative
        with pytest.raises(ContextError, match="escapes repository root"):
            ctx.resolve_path("../../../etc/passwd")

        # Symlink-based escape (if supported)
        try:
            link_path = git_root / "link.outside"
            target = Path("/tmp")
            link_path.symlink_to(target)
            with pytest.raises(ContextError, match="escapes repository root"):
                ctx.resolve_path(link_path)
        except (OSError, NotImplementedError):
            # Symlinks not supported or permission denied; skip
            pass


def test_resolve_path_symlink_escape() -> None:
    """Test symlink escape rejection where symlinks are supported."""
    with tempfile.TemporaryDirectory() as tmpdir:
        git_root = Path(tmpdir)
        ctx = ExecutionContext(git_root, "main", "abc123", "https://example.com/repo.git")

        # Create a symlink pointing outside the repo
        link = git_root / "escape_link"
        try:
            link.symlink_to("/tmp")
            # Attempt to resolve the symlink should fail
            with pytest.raises(ContextError, match="escapes repository root"):
                ctx.resolve_path(link)
        except (OSError, NotImplementedError):
            # If symlinks aren't supported, we skip the test
            pytest.skip("Symlinks not supported or permission denied")
