"""Regression guards for secret-bearing files at the repository boundary."""

from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _is_ignored(path: str) -> bool:
    result = subprocess.run(
        ["git", "check-ignore", "--no-index", "--quiet", path],
        cwd=ROOT,
        check=False,
    )
    return result.returncode == 0


def test_secret_bearing_file_families_are_ignored() -> None:
    blocked = (
        ".env",
        ".env.local",
        "apps/website/.env.production",
        "private.key",
        "signing.p12",
        "signing.pfx",
        "android.jks",
        "credentials.json",
        "service-account-prod.json",
        "provider_credentials.json",
        "runtime.secret",
        "secrets/provider-token.txt",
    )
    assert all(_is_ignored(path) for path in blocked)


def test_documented_env_templates_remain_trackable() -> None:
    allowed = (
        ".env.example",
        ".env.sample",
        "apps/website/.env.example",
        "apps/desktop/.env.sample",
    )
    assert all(not _is_ignored(path) for path in allowed)
