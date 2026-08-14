"""Canonical SkillRegistry adapter for ILAIOS-native Knowledge/RAG skills."""

from __future__ import annotations

from services.runtime.routing import AgentProfile, SkillArtifact, SkillRegistry
from src.knowledge_rag.skills import KNOWLEDGE_SKILLS, KnowledgeSkillManifest, knowledge_skill


def approve_knowledge_skills(registry: SkillRegistry) -> None:
    """Approve exact immutable Knowledge/RAG manifests in the canonical registry."""
    for manifest in KNOWLEDGE_SKILLS:
        registry.approve(
            manifest.skill_id,
            manifest.digest,
            manifest.authorities,
            owner=manifest.owner,
            license_id=manifest.license_id,
            source_provenance=manifest.source_provenance,
        )


def validate_knowledge_skill(
    registry: SkillRegistry,
    agent: AgentProfile,
    skill_id: str,
) -> KnowledgeSkillManifest:
    """Validate a native Knowledge/RAG skill without creating a second registry."""
    manifest = knowledge_skill(skill_id)
    artifact = SkillArtifact(
        skill_id=manifest.skill_id,
        content=manifest.content,
        requested_authorities=manifest.authorities,
        owner=manifest.owner,
        license_id=manifest.license_id,
        source_provenance=manifest.source_provenance,
    )
    registry.validate(artifact, agent)
    return manifest
