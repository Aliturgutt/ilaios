"""Canonical M23 platform profiles independent of publisher adapters."""

from __future__ import annotations

from dataclasses import dataclass


class PlatformProfileError(ValueError):
    """Raised when a platform profile is invalid or unavailable."""


@dataclass(frozen=True, slots=True)
class PlatformProfile:
    platform: str
    profile_name: str
    width: int
    height: int
    min_duration_seconds: float
    max_duration_seconds: float
    requires_captions: bool
    requires_thumbnail: bool
    metadata_fields: tuple[str, ...]

    def __post_init__(self) -> None:
        for name in ("platform", "profile_name"):
            value = getattr(self, name)
            if not value or value != value.strip():
                raise PlatformProfileError(f"{name} must be non-blank and trimmed")
        if self.width <= 0 or self.height <= 0:
            raise PlatformProfileError("resolution dimensions must be positive")
        if self.min_duration_seconds <= 0:
            raise PlatformProfileError("min_duration_seconds must be positive")
        if self.max_duration_seconds < self.min_duration_seconds:
            raise PlatformProfileError("max_duration_seconds must be >= minimum")
        if len(set(self.metadata_fields)) != len(self.metadata_fields):
            raise PlatformProfileError("metadata_fields must be unique")


class PlatformProfileRegistry:
    """Deterministic lookup of output requirements without upload logic."""

    def __init__(self, profiles: tuple[PlatformProfile, ...]) -> None:
        if not profiles:
            raise PlatformProfileError("at least one platform profile is required")
        keys = [(profile.platform, profile.profile_name) for profile in profiles]
        if len(keys) != len(set(keys)):
            raise PlatformProfileError("platform/profile keys must be unique")
        self._profiles = {key: profile for key, profile in zip(keys, profiles)}

    def get(self, platform: str, profile_name: str) -> PlatformProfile:
        try:
            return self._profiles[(platform, profile_name)]
        except KeyError as exc:
            raise PlatformProfileError("unknown platform profile") from exc

    def list(self) -> tuple[PlatformProfile, ...]:
        return tuple(self._profiles[key] for key in sorted(self._profiles))

    @classmethod
    def default(cls) -> PlatformProfileRegistry:
        vertical_metadata = ("title", "description", "hashtags")
        return cls(
            (
                PlatformProfile("youtube", "long_form", 1920, 1080, 1.0, 43200.0, False, True, ("title", "description", "tags")),
                PlatformProfile("youtube", "shorts", 1080, 1920, 1.0, 180.0, True, False, vertical_metadata),
                PlatformProfile("tiktok", "vertical", 1080, 1920, 1.0, 600.0, True, False, vertical_metadata),
                PlatformProfile("instagram", "reels", 1080, 1920, 1.0, 180.0, True, False, vertical_metadata),
                PlatformProfile("facebook", "reels", 1080, 1920, 1.0, 90.0, True, False, vertical_metadata),
            )
        )
