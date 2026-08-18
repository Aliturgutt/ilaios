from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
VERCEL_CONFIG = REPO_ROOT / "apps" / "website" / "vercel.json"


def test_vercel_git_auto_deployments_are_disabled_on_hobby() -> None:
    config = json.loads(VERCEL_CONFIG.read_text(encoding="utf-8"))

    git_config = config.get("git")
    assert isinstance(git_config, dict)
    assert git_config.get("deploymentEnabled") is False


def test_vercel_config_has_no_ignored_build_fallback() -> None:
    config = json.loads(VERCEL_CONFIG.read_text(encoding="utf-8"))

    # Ignored Build Step runs after a deployment has already been created and
    # canceled builds still consume Hobby deployment quota. With Git auto-deploy
    # disabled, production releases must be deliberate single deployments.
    assert "ignoreCommand" not in config
