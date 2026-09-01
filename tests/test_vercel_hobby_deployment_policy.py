from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
VERCEL_CONFIG = REPO_ROOT / "apps" / "website" / "vercel.json"


def test_vercel_git_deployments_are_master_only() -> None:
    config = json.loads(VERCEL_CONFIG.read_text(encoding="utf-8"))

    git_config = config.get("git")
    assert isinstance(git_config, dict)
    assert git_config.get("deploymentEnabled") == {"*": False, "master": True}


def test_vercel_git_freeze_has_no_ignored_build_escape_hatch() -> None:
    config = json.loads(VERCEL_CONFIG.read_text(encoding="utf-8"))

    assert "ignoreCommand" not in config
