"""ILAIOS-native Knowledge/RAG skill manifests."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass


_OWNER = "ILAIOS"
_LICENSE = "LicenseRef-ILAIOS-Proprietary"
_PROVENANCE = "ILAIOS-native"


@dataclass(frozen=True, slots=True)
class KnowledgeSkillManifest:
    skill_id: str
    version: str
    authorities: frozenset[str]
    description: str
    owner: str = _OWNER
    license_id: str = _LICENSE
    source_provenance: str = _PROVENANCE

    @property
    def content(self) -> bytes:
        material = "\n".join(
            (
                self.skill_id,
                self.version,
                ",".join(sorted(self.authorities)),
                self.description,
                self.owner,
                self.license_id,
                self.source_provenance,
            )
        )
        return material.encode("utf-8")

    @property
    def digest(self) -> str:
        return hashlib.sha256(self.content).hexdigest()


KNOWLEDGE_SKILLS: tuple[KnowledgeSkillManifest, ...] = (
    KnowledgeSkillManifest(
        skill_id="ilaios.skill.knowledge.retrieve.authorized",
        version="1.0.0",
        authorities=frozenset({"knowledge:retrieve"}),
        description=(
            "Retrieve bounded project context only after tenant, principal, purpose, "
            "classification, residency, retention, source-revocation and provenance checks."
        ),
    ),
    KnowledgeSkillManifest(
        skill_id="ilaios.skill.knowledge.context.provenance",
        version="1.0.0",
        authorities=frozenset({"knowledge:provenance"}),
        description=(
            "Bind authorized retrieved context to deterministic source and content evidence."
        ),
    ),
)


def knowledge_skill(skill_id: str) -> KnowledgeSkillManifest:
    for manifest in KNOWLEDGE_SKILLS:
        if manifest.skill_id == skill_id:
            return manifest
    raise ValueError(f"unknown Knowledge/RAG skill: {skill_id}")
