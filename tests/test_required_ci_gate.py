"""Regression coverage for fail-closed Required CI aggregation."""

from __future__ import annotations

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
