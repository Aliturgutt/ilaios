"""Regression contract for canonical exact-master Required CI status publication."""

from __future__ import annotations

from pathlib import Path


WORKFLOW_PATH = (
    Path(__file__).resolve().parents[1]
    / ".github"
    / "workflows"
    / "required-ci-status.yml"
)


def _workflow_text() -> str:
    return WORKFLOW_PATH.read_text(encoding="utf-8")


def test_exact_master_status_is_derived_from_required_ci_completion() -> None:
    text = _workflow_text()
    assert "- Required CI Gate" in text
    assert "- completed" in text
    assert "github.event.workflow_run.head_branch == 'master'" in text
    assert "HEAD_SHA: ${{ github.event.workflow_run.head_sha }}" in text
    assert "RUN_CONCLUSION: ${{ github.event.workflow_run.conclusion }}" in text


def test_exact_master_status_permissions_are_minimal() -> None:
    text = _workflow_text()
    assert "contents: read" in text
    assert "statuses: write" in text
    assert "contents: write" not in text
    assert "actions: write" not in text
    assert "pull-requests: write" not in text


def test_exact_master_status_fails_closed_and_validates_sha() -> None:
    text = _workflow_text()
    assert "len(sha) != 40" in text
    assert "workflow_run head SHA is malformed" in text
    assert "state = 'success' if conclusion == 'success' else 'failure'" in text
    assert "'context': 'ilaios/required-ci-exact-master'" in text
    assert "'target_url': os.environ['TARGET_URL']" in text
    assert "assert response.status == 201" in text
