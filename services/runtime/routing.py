"""Fail-closed runtime routing and supply-chain validation."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass


class RuntimeError(ValueError):
    """Raised when governed runtime selection cannot be proven safe."""


@dataclass(frozen=True, slots=True)
class AgentProfile:
    agent_id: str
    authorities: frozenset[str]


@dataclass(frozen=True, slots=True)
class ProviderProfile:
    provider_id: str
    capabilities: frozenset[str]
    deterministic: bool
    enabled: bool = True


@dataclass(frozen=True, slots=True)
class SkillArtifact:
    skill_id: str
    content: bytes
    requested_authorities: frozenset[str]

    @property
    def digest(self) -> str:
        return hashlib.sha256(self.content).hexdigest()


@dataclass(frozen=True, slots=True)
class RouteDecision:
    agent_id: str
    skill_id: str
    provider_id: str
    capability: str
    deterministic_first: bool
    evidence: tuple[str, ...]


class SkillRegistry:
    """Allow-list of immutable skill digests and bounded authorities."""

    def __init__(self) -> None:
        self._approved: dict[str, tuple[str, frozenset[str]]] = {}

    def approve(
        self, skill_id: str, digest: str, authorities: frozenset[str]
    ) -> None:
        if len(digest) != 64:
            raise RuntimeError("skill digest must be a SHA-256 hex digest")
        self._approved[skill_id] = (digest, authorities)

    def validate(self, artifact: SkillArtifact, agent: AgentProfile) -> None:
        approved = self._approved.get(artifact.skill_id)
        if approved is None:
            raise RuntimeError("skill is not approved")
        digest, authorities = approved
        if artifact.digest != digest:
            raise RuntimeError("skill digest does not match approval")
        if not artifact.requested_authorities <= authorities:
            raise RuntimeError("skill requests authority outside approval")
        if not artifact.requested_authorities <= agent.authorities:
            raise RuntimeError("skill would expand agent authority")


def route_provider(
    agent: AgentProfile,
    artifact: SkillArtifact,
    registry: SkillRegistry,
    providers: tuple[ProviderProfile, ...],
    *,
    capability: str,
) -> RouteDecision:
    """Choose a deterministic capable provider without expanding authority."""
    registry.validate(artifact, agent)
    candidates = sorted(
        (
            provider
            for provider in providers
            if provider.enabled and capability in provider.capabilities
        ),
        key=lambda provider: (not provider.deterministic, provider.provider_id),
    )
    if not candidates:
        raise RuntimeError("no enabled provider has the required capability")
    selected = candidates[0]
    return RouteDecision(
        agent_id=agent.agent_id,
        skill_id=artifact.skill_id,
        provider_id=selected.provider_id,
        capability=capability,
        deterministic_first=selected.deterministic,
        evidence=(
            f"skill_digest={artifact.digest}",
            f"authority_count={len(artifact.requested_authorities)}",
            f"provider={selected.provider_id}",
        ),
    )
