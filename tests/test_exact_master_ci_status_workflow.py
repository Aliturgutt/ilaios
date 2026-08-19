"""Regression contract for exact-master Required CI evidence publication."""

from __future__ import annotations

from pathlib import Path


WORKFLOW_PATH = (
    Path(__file__).resolve().parents[1]
    / ".github"
    / "workflows"
    / "exact-master-ci-status.yml"
)


def _workflow_text() -> str:
    return WORKFLOW_PATH.read_text(encoding="utf-8")


def test_exact_master_status_is_derived_only_from_required_ci_completion() -> None:
    text = _workflow_text()
    assert 'workflows: ["Required CI Gate"]' in text
    assert "types: [completed]" in text
    assert "github.event.workflow_run.event == 'push'" in text
    assert "github.event.workflow_run.head_branch == 'master'" in text
    assert "HEAD_SHA: ${{ github.event.workflow_run.head_sha }}" in text


def test_exact_master_status_permissions_are_minimal() -> None:
    text = _workflow_text()
    assert "contents: read" in text
    assert "statuses: write" in text
    assert "contents: write" not in text
    assert "actions: write" not in text
    assert "pull-requests: write" not in text


def test_exact_master_status_fails_closed_and_is_auditable() -> None:
    text = _workflow_text()
    assert 'context": "ILAIOS Exact Master CI"' in text
    assert 'description="Required CI Gate PASS on exact master"' in text
    assert "failure|timed_out|cancelled|action_required)" in text
    assert 'state="failure"' in text
    assert 'state="error"' in text
    assert '"target_url": os.environ["RUN_URL"]' in text
