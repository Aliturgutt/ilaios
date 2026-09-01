"""Resolve request CaptionMode against an optional platform profile."""

from __future__ import annotations

from dataclasses import dataclass

from .platform_profiles import PlatformProfile
from .request_manifest import CaptionMode, EpisodeRequestManifest


@dataclass(frozen=True, slots=True)
class CaptionPolicyDecision:
    requested_mode: CaptionMode
    effective_enabled: bool
    reason: str


def resolve_caption_policy(
    *,
    manifest: EpisodeRequestManifest,
    platform_profile: PlatformProfile | None,
) -> CaptionPolicyDecision:
    mode = manifest.caption_mode
    if mode is CaptionMode.OFF:
        return CaptionPolicyDecision(mode, False, "user_or_default_off")
    if mode is CaptionMode.ON:
        return CaptionPolicyDecision(mode, True, "user_requested_on")
    if platform_profile is None:
        return CaptionPolicyDecision(mode, False, "auto_without_platform_requirement")
    return CaptionPolicyDecision(
        mode,
        platform_profile.requires_captions,
        "auto_platform_requires_captions"
        if platform_profile.requires_captions
        else "auto_platform_does_not_require_captions",
    )
