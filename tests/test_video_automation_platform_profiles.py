from __future__ import annotations

import pytest

from src.video_automation.platform_profiles import (
    PlatformProfile,
    PlatformProfileError,
    PlatformProfileRegistry,
)


def test_default_profiles_cover_required_platform_families() -> None:
    registry = PlatformProfileRegistry.default()
    keys = {(profile.platform, profile.profile_name) for profile in registry.list()}
    assert ("youtube", "long_form") in keys
    assert ("youtube", "shorts") in keys
    assert ("tiktok", "vertical") in keys
    assert ("instagram", "reels") in keys
    assert ("facebook", "reels") in keys


def test_profiles_define_format_and_publishing_requirements() -> None:
    profile = PlatformProfileRegistry.default().get("youtube", "shorts")
    assert (profile.width, profile.height) == (1080, 1920)
    assert profile.max_duration_seconds == 180.0
    assert profile.requires_captions is True
    assert "title" in profile.metadata_fields


def test_registry_rejects_duplicate_profile_keys() -> None:
    profile = PlatformProfile("x", "p", 1, 1, 1.0, 2.0, False, False, ())
    with pytest.raises(PlatformProfileError, match="unique"):
        PlatformProfileRegistry((profile, profile))


def test_unknown_profile_fails_closed() -> None:
    with pytest.raises(PlatformProfileError, match="unknown"):
        PlatformProfileRegistry.default().get("youtube", "missing")
