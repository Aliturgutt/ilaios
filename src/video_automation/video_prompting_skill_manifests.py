"""Canonical manifests for ILAIOS-native Video Factory prompting skills."""

from __future__ import annotations

from .video_skills import SkillRisk, VideoSkillManifest


VIDEO_PROMPTING_SKILLS: tuple[VideoSkillManifest, ...] = (
    VideoSkillManifest(
        "ilaios.skill.video.director.plan",
        "1.0.0",
        "ilaios.capability.video-media-factory",
        "src.video_automation.video_prompting_skills:VideoDirector",
        SkillRisk.READ_ONLY,
        ("manifest.read",),
    ),
    VideoSkillManifest(
        "ilaios.skill.video.prompt.compose",
        "1.0.0",
        "ilaios.capability.video-media-factory",
        "src.video_automation.video_prompting_skills:VideoPromptComposer",
        SkillRisk.READ_ONLY,
        ("manifest.read",),
    ),
    VideoSkillManifest(
        "ilaios.skill.video.reference-assets.plan",
        "1.0.0",
        "ilaios.capability.video-media-factory",
        "src.video_automation.video_prompting_skills:ReferenceAssetPlanner",
        SkillRisk.READ_ONLY,
        ("manifest.read",),
    ),
    VideoSkillManifest(
        "ilaios.skill.video.routing.model",
        "1.0.0",
        "ilaios.capability.video-media-factory",
        "src.video_automation.video_prompting_skills:ModelRoutingAdvisor",
        SkillRisk.READ_ONLY,
        ("manifest.read",),
    ),
    VideoSkillManifest(
        "ilaios.skill.video.continuity.plan",
        "1.0.0",
        "ilaios.capability.video-media-factory",
        "src.video_automation.video_prompting_skills:ContinuityPlanner",
        SkillRisk.READ_ONLY,
        ("manifest.read",),
    ),
)
