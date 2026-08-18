"""Canonical manifests for ILAIOS-native Video Factory prompting skills.

The existing cinematography skill already implements the director role, so this
module adds only the four missing governed skill identities. Implementations point
at canonical ILAIOS components rather than parallel engines.
"""

from __future__ import annotations

from .video_skills import SkillRisk, VideoSkillManifest


VIDEO_PROMPTING_SKILLS: tuple[VideoSkillManifest, ...] = (
    VideoSkillManifest(
        "ilaios.skill.video.prompt.compose",
        "1.0.0",
        "ilaios.capability.video-media-factory",
        "src.video_automation.prompt_compilation:ShotPromptCompiler",
        SkillRisk.READ_ONLY,
        ("manifest.read",),
    ),
    VideoSkillManifest(
        "ilaios.skill.video.reference-assets.inspect",
        "1.0.0",
        "ilaios.capability.video-media-factory",
        "services.reference_assets:ReferenceAssetRecord",
        SkillRisk.READ_ONLY,
        ("manifest.read",),
    ),
    VideoSkillManifest(
        "ilaios.skill.video.model-fit.analyze",
        "1.0.0",
        "ilaios.capability.video-media-factory",
        "services.routing_intelligence:RoutingIntelligenceEngine",
        SkillRisk.READ_ONLY,
        ("manifest.read",),
    ),
    VideoSkillManifest(
        "ilaios.skill.video.continuity.track",
        "1.0.0",
        "ilaios.capability.video-media-factory",
        "src.video_automation.continuity:ContinuityTracker",
        SkillRisk.READ_ONLY,
        ("manifest.read",),
    ),
)
