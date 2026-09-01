"""Tests for BootstrapValidator Git validation functionality."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.core.bootstrap_validator import BootstrapValidator, ContextError


class TestBootstrapValidator:
    """Test suite for BootstrapValidator."""

    def test_validate_git_identity_all_checks_pass(self) -> None:
        """Test successful Git identity validation with all checks passing."""
        validator = BootstrapValidator()

        with patch("src.core.bootstrap_validator.subprocess.run") as mock_run:
            # Mock all four git commands to return valid responses
            mock_run.side_effect = [
                MagicMock(stdout="/fake/path/to/repo\n", stderr="", returncode=0),
                MagicMock(stdout="main\n", stderr="", returncode=0),
                MagicMock(stdout="a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8g9h0\n", stderr="", returncode=0),
                MagicMock(stdout="https://github.com/user/repo.git\n", stderr="", returncode=0),
            ]

            result = validator.validate_git_identity()

            # Verify the result is a Path object pointing to the repo root
            assert isinstance(result, Path)
            # Normalize path for cross-platform comparison
            assert str(result).replace("\\", "/") == "/fake/path/to/repo"

            # Verify all four git commands were called
            assert mock_run.call_count == 4

    def test_validate_git_identity_repo_root_check_fails(self) -> None:
        """Test that validation fails when repo root check fails."""
        validator = BootstrapValidator()

        with patch("src.core.bootstrap_validator.subprocess.run") as mock_run:
            # Mock first command to fail with CalledProcessError
            error = subprocess.CalledProcessError(128, "git rev-parse --show-toplevel")
            error.stderr = "fatal: not a git repository"
            mock_run.side_effect = error

            with pytest.raises(ContextError):
                validator.validate_git_identity()

    def test_validate_git_identity_branch_check_fails(self) -> None:
        """Test that validation fails when branch check fails."""
        validator = BootstrapValidator()

        with patch("src.core.bootstrap_validator.subprocess.run") as mock_run:
            # Mock first command to succeed, second to fail
            mock_run.side_effect = [
                MagicMock(stdout="/fake/path/to/repo\n", stderr="", returncode=0),
                subprocess.CalledProcessError(128, "git branch --show-current"),
            ]

            with pytest.raises(ContextError):
                validator.validate_git_identity()

    def test_validate_git_identity_head_check_fails(self) -> None:
        """Test that validation fails when HEAD check fails."""
        validator = BootstrapValidator()

        with patch("src.core.bootstrap_validator.subprocess.run") as mock_run:
            # Mock first two commands to succeed, third to fail
            mock_run.side_effect = [
                MagicMock(stdout="/fake/path/to/repo\n", stderr="", returncode=0),
                MagicMock(stdout="main\n", stderr="", returncode=0),
                subprocess.CalledProcessError(128, "git rev-parse HEAD"),
            ]

            with pytest.raises(ContextError):
                validator.validate_git_identity()

    def test_validate_git_identity_origin_check_fails(self) -> None:
        """Test that validation fails when origin check fails."""
        validator = BootstrapValidator()

        with patch("src.core.bootstrap_validator.subprocess.run") as mock_run:
            # Mock first three commands to succeed, fourth to fail
            mock_run.side_effect = [
                MagicMock(stdout="/fake/path/to/repo\n", stderr="", returncode=0),
                MagicMock(stdout="main\n", stderr="", returncode=0),
                MagicMock(stdout="a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8g9h0\n", stderr="", returncode=0),
                subprocess.CalledProcessError(128, "git remote get-url origin"),
            ]

            with pytest.raises(ContextError):
                validator.validate_git_identity()

    def test_validate_git_identity_repo_root_empty(self) -> None:
        """Test that validation fails when repo root is empty."""
        validator = BootstrapValidator()

        with patch("src.core.bootstrap_validator.subprocess.run") as mock_run:
            # Mock first command to return empty output
            mock_run.side_effect = [
                MagicMock(stdout="\n", stderr="", returncode=0),
            ]

            with pytest.raises(ContextError, match="Git command returned empty output: git rev-parse --show-toplevel"):
                validator.validate_git_identity()

    def test_validate_git_identity_branch_empty(self) -> None:
        """Test that validation fails when branch name is empty."""
        validator = BootstrapValidator()

        with patch("src.core.bootstrap_validator.subprocess.run") as mock_run:
            # Mock first command succeeds, second returns empty
            mock_run.side_effect = [
                MagicMock(stdout="/fake/path/to/repo\n", stderr="", returncode=0),
                MagicMock(stdout="\n", stderr="", returncode=0),
            ]

            with pytest.raises(ContextError, match="Git command returned empty output: git branch --show-current"):
                validator.validate_git_identity()

    def test_validate_git_identity_head_empty(self) -> None:
        """Test that validation fails when HEAD commit is empty."""
        validator = BootstrapValidator()

        with patch("src.core.bootstrap_validator.subprocess.run") as mock_run:
            # Mock first two commands succeed, third returns empty
            mock_run.side_effect = [
                MagicMock(stdout="/fake/path/to/repo\n", stderr="", returncode=0),
                MagicMock(stdout="main\n", stderr="", returncode=0),
                MagicMock(stdout="\n", stderr="", returncode=0),
            ]

            with pytest.raises(ContextError, match="Git command returned empty output: git rev-parse HEAD"):
                validator.validate_git_identity()

    def test_validate_git_identity_origin_empty(self) -> None:
        """Test that validation fails when origin URL is empty."""
        validator = BootstrapValidator()

        with patch("src.core.bootstrap_validator.subprocess.run") as mock_run:
            # Mock first three commands succeed, fourth returns empty
            mock_run.side_effect = [
                MagicMock(stdout="/fake/path/to/repo\n", stderr="", returncode=0),
                MagicMock(stdout="main\n", stderr="", returncode=0),
                MagicMock(stdout="a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8g9h0\n", stderr="", returncode=0),
                MagicMock(stdout="\n", stderr="", returncode=0),
            ]

            with pytest.raises(ContextError, match="Git command returned empty output: git remote get-url origin"):
                validator.validate_git_identity()

    def test_execute_git_command_timeout(self) -> None:
        """Test that Git command timeout raises ContextError."""
        validator = BootstrapValidator()

        with patch("src.core.bootstrap_validator.subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired("git rev-parse --show-toplevel", 30)

            with pytest.raises(ContextError):
                validator.validate_git_identity()

    def test_execute_git_command_file_not_found(self) -> None:
        """Test that Git not found raises ContextError."""
        validator = BootstrapValidator()

        with patch("src.core.bootstrap_validator.subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("No such file or directory")

            with pytest.raises(ContextError):
                validator.validate_git_identity()
