from dataclasses import replace

import pytest

from services.integrations.video_skill_governance import (
    ALL_VIDEO_SKILLS,
    REQUIRED_VIDEO_SKILL_FAMILIES,
    approve_video_skills,
    runtime_artifact_for_video_skill,
    validate_video_skill,
)
from services.runtime.routing import AgentProfile, RuntimeError, SkillRegistry


def _video_agent() -> AgentProfile:
    authorities = frozenset(
        permission for skill in ALL_VIDEO_SKILLS for permission in skill.permissions
    )
    return AgentProfile("video-worker", authorities)


def test_all_video_skill_families_share_one_canonical_registry() -> None:
    registry = SkillRegistry()
    artifacts = approve_video_skills(registry)
    agent = _video_agent()

    families = {
        artifact.skill_id.removeprefix("ilaios.skill.video.").split(".", 1)[0]
        for artifact in artifacts
    }
    assert REQUIRED_VIDEO_SKILL_FAMILIES <= families
    assert {artifact.skill_id for artifact in artifacts} == {
        skill.skill_id for skill in ALL_VIDEO_SKILLS
    }
    for manifest in ALL_VIDEO_SKILLS:
        artifact = validate_video_skill(registry, agent, manifest)
        assert artifact.digest == manifest.digest
        assert artifact.owner == "ILAIOS"
        assert artifact.license_id == "LicenseRef-ILAIOS-Proprietary"
        assert artifact.source_provenance == "ILAIOS-native"


def test_video_prompting_skills_reuse_canonical_implementations() -> None:
    expected = {
        "ilaios.skill.video.direction.cinematography": (
            "src.video_automation.video_skills:CreativeDirection"
        ),
        "ilaios.skill.video.prompt.compose": (
            "src.video_automation.prompt_compilation:ShotPromptCompiler"
        ),
        "ilaios.skill.video.reference-assets.inspect": (
            "services.reference_assets:ReferenceAssetRecord"
        ),
        "ilaios.skill.video.model-fit.analyze": (
            "services.routing_intelligence:RoutingIntelligenceEngine"
        ),
        "ilaios.skill.video.continuity.track": (
            "src.video_automation.continuity:ContinuityTracker"
        ),
    }
    manifests = {
        skill.skill_id: skill
        for skill in ALL_VIDEO_SKILLS
        if skill.skill_id in expected
    }
    assert set(manifests) == set(expected)
    for skill_id, implementation in expected.items():
        manifest = manifests[skill_id]
        assert manifest.implementation == implementation
        assert manifest.risk.value == "read_only"
        assert manifest.permissions == ("manifest.read",)
        assert "video_prompting_skills" not in manifest.implementation


def test_video_runtime_gate_rejects_digest_authority_and_supply_chain_tampering(
) -> None:
    registry = SkillRegistry()
    approve_video_skills(registry)
    agent = _video_agent()
    manifest = ALL_VIDEO_SKILLS[0]
    artifact = runtime_artifact_for_video_skill(manifest)

    with pytest.raises(RuntimeError, match="digest"):
        registry.validate(
            replace(artifact, content=artifact.content + b"tampered"), agent
        )
    with pytest.raises(RuntimeError, match="outside approval"):
        registry.validate(
            replace(
                artifact,
                requested_authorities=artifact.requested_authorities
                | frozenset({"system.admin"}),
            ),
            AgentProfile("elevated", agent.authorities | frozenset({"system.admin"})),
        )
    with pytest.raises(RuntimeError, match="owner"):
        registry.validate(replace(artifact, owner="Other"), agent)
    with pytest.raises(RuntimeError, match="license"):
        registry.validate(replace(artifact, license_id="MIT"), agent)
    with pytest.raises(RuntimeError, match="provenance"):
        registry.validate(replace(artifact, source_provenance="third-party"), agent)


def test_supply_chain_approval_is_complete_or_rejected() -> None:
    registry = SkillRegistry()
    artifact = runtime_artifact_for_video_skill(ALL_VIDEO_SKILLS[0])

    with pytest.raises(RuntimeError, match="metadata must be complete"):
        registry.approve(
            artifact.skill_id,
            artifact.digest,
            artifact.requested_authorities,
            owner="ILAIOS",
        )


def test_video_namespace_cannot_bypass_proprietary_supply_chain_identity() -> None:
    registry = SkillRegistry()
    artifact = runtime_artifact_for_video_skill(ALL_VIDEO_SKILLS[0])

    with pytest.raises(RuntimeError, match="proprietary supply-chain identity"):
        registry.approve(
            artifact.skill_id, artifact.digest, artifact.requested_authorities
        )
    with pytest.raises(RuntimeError, match="proprietary supply-chain identity"):
        registry.approve(
            artifact.skill_id,
            artifact.digest,
            artifact.requested_authorities,
            owner="ILAIOS",
            license_id="MIT",
            source_provenance="ILAIOS-native",
        )
