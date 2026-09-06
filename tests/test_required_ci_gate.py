"""Regression coverage for fail-closed Required CI aggregation."""

from __future__ import annotations

import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_dependency_vulnerability_failure_blocks_required_ci_gate() -> None:
    workflow = (REPO_ROOT / ".github/workflows/required-ci-gate.yml").read_text(
        encoding="utf-8"
    )

    assert "dependency-vulnerability-scan" in workflow
    assert "DEPENDENCY_VULNERABILITY_RESULT" in workflow
    assert "needs.dependency-vulnerability-scan.result" in workflow
    assert '[[ "$DEPENDENCY_VULNERABILITY_RESULT" != "success" ]]' in workflow
    assert "Dependency vulnerability scanning failed:" in workflow


def test_s2_platform_validation_uses_a_distinct_concurrency_scope() -> None:
    platform_workflow = (REPO_ROOT / ".github/workflows/platform-ci.yml").read_text(
        encoding="utf-8"
    )
    required_workflow = (REPO_ROOT / ".github/workflows/required-ci-gate.yml").read_text(
        encoding="utf-8"
    )

    assert "concurrency_scope:" in platform_workflow
    assert "default: default" in platform_workflow
    assert "inputs.concurrency_scope || 'default'" in platform_workflow
    normal_job = re.search(
        r"^  platform:\n.*?(?=^  [a-z][a-z-]+:|\Z)",
        required_workflow,
        flags=re.MULTILINE | re.DOTALL,
    )
    s2_job = re.search(
        r"^  release-candidate-platform:\n.*?(?=^  [a-z][a-z-]+:|\Z)",
        required_workflow,
        flags=re.MULTILINE | re.DOTALL,
    )

    assert normal_job is not None
    assert s2_job is not None
    normal_scope = re.search(r"concurrency_scope: ([^\n]+)", normal_job.group(0))
    s2_scope = re.search(r"concurrency_scope: ([^\n]+)", s2_job.group(0))
    assert normal_scope is not None
    assert s2_scope is not None
    assert normal_scope.group(1) != s2_scope.group(1)
