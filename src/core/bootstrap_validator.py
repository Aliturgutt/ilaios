"""Bootstrap Validator: Git Validation Foundation.

Implements the first atomic part of Bootstrap Validator that validates
Git repository identity through four core checks.
"""

import subprocess
from pathlib import Path


class ContextError(Exception):
    """Raised when repository context cannot be established."""


class BootstrapValidator:
    """Validates Git repository identity and establishes context."""

    def __init__(self, repo_path: Path | None = None) -> None:
        """Initialize validator with optional repository path.

        Args:
            repo_path: Path to Git repository. Defaults to current working directory.
        """
        self.repo_path = repo_path or Path.cwd()

    def validate_git_identity(self) -> Path:
        """Validate Git repository identity through four core checks.

        Executes these checks:
        1. git rev-parse --show-toplevel
        2. git branch --show-current
        3. git rev-parse HEAD
        4. git remote get-url origin

        Returns:
            Path: Verified Git repository root path

        Raises:
            ContextError: If any check fails, required output is empty,
                         or repository identity cannot be established.
        """
        # Check 1: Verify repository root
        repo_root = self._execute_git_command(["rev-parse", "--show-toplevel"])
        if not repo_root:
            raise ContextError("Git repository root path is empty")

        repo_root_path = Path(repo_root.strip())

        # Check 2: Verify current branch
        current_branch = self._execute_git_command(["branch", "--show-current"])
        if not current_branch:
            raise ContextError("Current Git branch name is empty")

        # Check 3: Verify HEAD commit
        head_commit = self._execute_git_command(["rev-parse", "HEAD"])
        if not head_commit:
            raise ContextError("Current Git HEAD commit is empty")

        # Check 4: Verify origin remote URL
        origin_url = self._execute_git_command(["remote", "get-url", "origin"])
        if not origin_url:
            raise ContextError("Git origin remote URL is empty")

        return repo_root_path

    def _execute_git_command(self, args: list[str]) -> str:
        """Execute a Git command and return its output.

        Args:
            args: Git command arguments

        Returns:
            str: Command output

        Raises:
            ContextError: If command fails or returns empty output
        """
        try:
            result = subprocess.run(
                ["git"] + args,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True,
                timeout=30
            )
            output = result.stdout.strip()
            if not output:
                raise ContextError(f"Git command returned empty output: git {' '.join(args)}")
            return output
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.strip() if e.stderr else "Unknown error"
            raise ContextError(
                f"Git command failed: git {' '.join(args)}\n"
                f"Exit code: {e.returncode}\n"
                f"Error: {error_msg}"
            ) from e
        except subprocess.TimeoutExpired as e:
            raise ContextError(
                f"Git command timed out: git {' '.join(args)}"
            ) from e
        except FileNotFoundError as e:
            raise ContextError(
                "Git is not installed or not found in PATH"
            ) from e
