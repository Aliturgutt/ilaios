"""Regression contract for exact-master Software Factory status publication."""

from __future__ import annotations

from pathlib import Path


WORKFLOW_PATH = (
    Path(__file__).resolve().parents[1]
    / ".github"
    / "workflows"
    / "software-factory-final-evidence-status.yml"
)


def _workflow_text() -> str:
    return WORKFLOW_PATH.read_text(encoding="utf-8")


def test_status_is_derived_only_from_master_push_completion() -> None:
    text = _workflow_text()
    assert "- Software Factory Final Evidence" in text
    assert "- completed" in text
    assert "github.event.workflow_run.event == 'push'" in text
    assert "github.event.workflow_run.head_branch == 'master'" in text
    assert "HEAD_SHA: ${{ github.event.workflow_run.head_sha }}" in text
    assert "RUN_CONCLUSION: ${{ github.event.workflow_run.conclusion }}" in text


def test_status_permissions_are_minimal() -> None:
    text = _workflow_text()
    assert "contents: read" in text
    assert "statuses: write" in text
    assert "contents: write" not in text
    assert "actions: write" not in text
    assert "pull-requests: write" not in text


def test_status_fails_closed_and_validates_sha() -> None:
    text = _workflow_text()
    assert "len(sha) != 40" in text
    assert "workflow_run head SHA is malformed" in text
    assert "state = 'success' if conclusion == 'success' else 'failure'" in text
    assert "'context': 'ilaios/software-factory-exact-master'" in text
    assert "'target_url': os.environ['TARGET_URL']" in text
    assert "assert response.status == 201" in text
