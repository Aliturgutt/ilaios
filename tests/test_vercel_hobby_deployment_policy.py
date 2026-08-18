from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
VERCEL_CONFIG = REPO_ROOT / "apps" / "website" / "vercel.json"


def test_vercel_git_deployments_are_opt_in_except_master() -> None:
    config = json.loads(VERCEL_CONFIG.read_text(encoding="utf-8"))

    git_config = config.get("git")
    assert isinstance(git_config, dict)
    deployment_enabled = git_config.get("deploymentEnabled")
    assert isinstance(deployment_enabled, dict)

    assert deployment_enabled.get("*") is False
    assert deployment_enabled.get("master") is True
    assert deployment_enabled.get("vercel-preview-*") is True


def test_vercel_ignored_build_step_uses_last_successful_deployment() -> None:
    config = json.loads(VERCEL_CONFIG.read_text(encoding="utf-8"))

    ignore_command = config.get("ignoreCommand")
    assert isinstance(ignore_command, str)
    assert "VERCEL_GIT_PREVIOUS_SHA" in ignore_command
    assert "git diff --quiet" in ignore_command
    assert "HEAD^ HEAD" in ignore_command
    assert "-- ./" in ignore_command
