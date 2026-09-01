"""Canonical manifests for existing Video Factory lifecycle implementations.

These manifests expose already-implemented M16/M19/M20 and governed provider
execution through the existing Video skill registry. They create no second
renderer, provider router, policy authority, or acceptance authority.
"""

from __future__ import annotations

from .video_skills import SkillRisk, VideoSkillManifest


VIDEO_LIFECYCLE_SKILLS: tuple[VideoSkillManifest, ...] = (
    VideoSkillManifest(
        "ilaios.skill.video.generation.execute",
        "1.0.0",
        "ilaios.capability.video-media-factory",
        "services.integrations.provider_video_runtime:ProviderBackedDesktopVideoRuntime",
        SkillRisk.EXTERNAL_SIDE_EFFECT,
        ("manifest.read", "provider.request", "media.write"),
    ),
    VideoSkillManifest(
        "ilaios.skill.video.captions.export",
        "1.0.0",
        "ilaios.capability.video-media-factory",
        "src.video_automation.caption_subtitle:CaptionSubtitleEngine",
        SkillRisk.MEDIA_MUTATION,
        ("media.read", "media.write"),
    ),
    VideoSkillManifest(
        "ilaios.skill.video.composition.prepare",
        "1.0.0",
        "ilaios.capability.video-media-factory",
        "src.video_automation.remotion_composition:RemotionCompositionAdapter",
        SkillRisk.MEDIA_MUTATION,
        ("media.read", "media.write"),
    ),
    VideoSkillManifest(
        "ilaios.skill.video.render.execute",
        "1.0.0",
        "ilaios.capability.video-media-factory",
        "src.video_automation.render_engine:RenderEngine",
        SkillRisk.MEDIA_MUTATION,
        ("media.read", "media.write"),
    ),
)


__all__ = ["VIDEO_LIFECYCLE_SKILLS"]
