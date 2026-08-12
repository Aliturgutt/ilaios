from __future__ import annotations

import re
from pathlib import Path

REMOTE_ACTION = re.compile(r"^\s*-?\s*uses:\s*([^\s#]+)")
IMMUTABLE_GITHUB_REF = re.compile(r"^[^/\s]+/[^@\s]+@[0-9a-fA-F]{40}$")


def test_remote_github_actions_are_pinned_to_commit_sha() -> None:
    workflow_root = Path(".github/workflows")
    violations: list[str] = []

    for workflow in sorted(workflow_root.glob("*.y*ml")):
        for line_number, line in enumerate(
            workflow.read_text(encoding="utf-8").splitlines(), start=1
        ):
            match = REMOTE_ACTION.match(line)
            if match is None:
                continue
            reference = match.group(1)
            if reference.startswith("./") or reference.startswith("docker://"):
                continue
            if not IMMUTABLE_GITHUB_REF.fullmatch(reference):
                violations.append(f"{workflow}:{line_number}: {reference}")

    assert not violations, "mutable GitHub Action references:\n" + "\n".join(violations)
