"""Bind ILAIOS-native Video skills to the canonical governed SkillRegistry.

This module is an adapter only. It does not define a second registry, policy engine,
evidence authority, provider selector, or runtime.
"""

from __future__ import annotations

from collections.abc import Sequence

from services.runtime.routing import AgentProfile, SkillArtifact, SkillRegistry
from src.video_automation.video_lifecycle_skill_manifests import VIDEO_LIFECYCLE_SKILLS
from src.video_automation.video_prompting_skill_manifests import VIDEO_PROMPTING_SKILLS
from src.video_automation.video_skills import (
    VIDEO_SKILLS,
    VideoSkillError,
    VideoSkillManifest,
    validate_video_skills,
)

ALL_VIDEO_SKILLS: tuple[VideoSkillManifest, ...] = (
    *VIDEO_SKILLS,
    *VIDEO_PROMPTING_SKILLS,
    *VIDEO_LIFECYCLE_SKILLS,
)

REQUIRED_VIDEO_SKILL_FAMILIES = frozenset(
    {
        "edit",
        "direction",
        "qa",
        "repair",
        "thumbnail",
        "publish",
        "prompt",
        "reference-assets",
        "model-fit",
        "continuity",
        "generation",
        "captions",
        "composition",
        "render",
    }
)


def _canonical_manifest_content(manifest: VideoSkillManifest) -> bytes:
    material = "|".join(
        (
            manifest.skill_id,
            manifest.version,
            manifest.capability_id,
            manifest.implementation,
            manifest.risk.value,
            *manifest.permissions,
            manifest.owner,
            manifest.license_id,
            manifest.source_provenance,
        )
    )
    return material.encode()


def _video_skill_family(skill_id: str) -> str:
    prefix = "ilaios.skill.video."
    if not skill_id.startswith(prefix):
        raise VideoSkillError("video skill is outside the canonical namespace")
    return skill_id.removeprefix(prefix).split(".", 1)[0]


def _require_governed_families(skills: Sequence[VideoSkillManifest]) -> None:
    present = {_video_skill_family(skill.skill_id) for skill in skills}
    missing = REQUIRED_VIDEO_SKILL_FAMILIES - present
    if missing:
        raise VideoSkillError(
            "video governance is missing required skill families: "
            + ", ".join(sorted(missing))
        )


def runtime_artifact_for_video_skill(
    manifest: VideoSkillManifest,
    *,
    requested_authorities: frozenset[str] | None = None,
) -> SkillArtifact:
    """Build the immutable runtime artifact represented by one canonical manifest."""
    artifact = SkillArtifact(
        manifest.skill_id,
        _canonical_manifest_content(manifest),
        frozenset(manifest.permissions)
        if requested_authorities is None
        else requested_authorities,
        owner=manifest.owner,
        license_id=manifest.license_id,
        source_provenance=manifest.source_provenance,
    )
    if artifact.digest != manifest.digest:
        raise VideoSkillError("video manifest digest diverges from runtime artifact")
    return artifact


def approve_video_skills(
    registry: SkillRegistry,
    skills: Sequence[VideoSkillManifest] = ALL_VIDEO_SKILLS,
) -> tuple[SkillArtifact, ...]:
    """Approve every canonical Video skill in the existing governed registry."""
    validate_video_skills(skills)
    _require_governed_families(skills)
    artifacts: list[SkillArtifact] = []
    for manifest in skills:
        artifact = runtime_artifact_for_video_skill(manifest)
        registry.approve(
            artifact.skill_id,
            artifact.digest,
            frozenset(manifest.permissions),
            owner=manifest.owner,
            license_id=manifest.license_id,
            source_provenance=manifest.source_provenance,
        )
        artifacts.append(artifact)
    return tuple(artifacts)


def validate_video_skill(
    registry: SkillRegistry,
    agent: AgentProfile,
    manifest: VideoSkillManifest,
    *,
    requested_authorities: frozenset[str] | None = None,
) -> SkillArtifact:
    """Fail closed unless one Video skill passes canonical registry governance."""
    artifact = runtime_artifact_for_video_skill(
        manifest, requested_authorities=requested_authorities
    )
    registry.validate(artifact, agent)
    return artifact
