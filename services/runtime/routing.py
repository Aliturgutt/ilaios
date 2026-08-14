"""Fail-closed runtime routing and supply-chain validation."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass


_VIDEO_SKILL_PREFIX = "ilaios.skill.video."
_VIDEO_SKILL_SUPPLY_CHAIN = (
    "ILAIOS",
    "LicenseRef-ILAIOS-Proprietary",
    "ILAIOS-native",
)


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
    owner: str | None = None
    license_id: str | None = None
    source_provenance: str | None = None

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


@dataclass(frozen=True, slots=True)
class _SkillApproval:
    digest: str
    authorities: frozenset[str]
    owner: str | None
    license_id: str | None
    source_provenance: str | None


class SkillRegistry:
    """Allow-list of immutable skill digests, authorities, and supply-chain identity."""

    def __init__(self) -> None:
        self._approved: dict[str, _SkillApproval] = {}

    def approve(
        self,
        skill_id: str,
        digest: str,
        authorities: frozenset[str],
        *,
        owner: str | None = None,
        license_id: str | None = None,
        source_provenance: str | None = None,
    ) -> None:
        if len(digest) != 64 or any(
            character not in "0123456789abcdef" for character in digest
        ):
            raise RuntimeError("skill digest must be a lowercase SHA-256 hex digest")
        metadata = (owner, license_id, source_provenance)
        if any(value is not None for value in metadata):
            if any(value is None for value in metadata):
                raise RuntimeError("skill supply-chain metadata must be complete")
            if any(not value or value != value.strip() for value in metadata if value):
                raise RuntimeError("skill supply-chain metadata must be trimmed")
        if (
            skill_id.startswith(_VIDEO_SKILL_PREFIX)
            and metadata != _VIDEO_SKILL_SUPPLY_CHAIN
        ):
            raise RuntimeError(
                "video skills require ILAIOS proprietary supply-chain identity"
            )
        self._approved[skill_id] = _SkillApproval(
            digest,
            authorities,
            owner,
            license_id,
            source_provenance,
        )

    def validate(self, artifact: SkillArtifact, agent: AgentProfile) -> None:
        approved = self._approved.get(artifact.skill_id)
        if approved is None:
            raise RuntimeError("skill is not approved")
        if artifact.digest != approved.digest:
            raise RuntimeError("skill digest does not match approval")
        if not artifact.requested_authorities <= approved.authorities:
            raise RuntimeError("skill requests authority outside approval")
        if not artifact.requested_authorities <= agent.authorities:
            raise RuntimeError("skill would expand agent authority")
        if approved.owner is not None and artifact.owner != approved.owner:
            raise RuntimeError("skill owner does not match approval")
        if (
            approved.license_id is not None
            and artifact.license_id != approved.license_id
        ):
            raise RuntimeError("skill license does not match approval")
        if (
            approved.source_provenance is not None
            and artifact.source_provenance != approved.source_provenance
        ):
            raise RuntimeError("skill provenance does not match approval")


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
    supply_chain_evidence = tuple(
        item
        for item in (
            f"skill_owner={artifact.owner}" if artifact.owner is not None else None,
            f"skill_license={artifact.license_id}"
            if artifact.license_id is not None
            else None,
            f"skill_provenance={artifact.source_provenance}"
            if artifact.source_provenance is not None
            else None,
        )
        if item is not None
    )
    return RouteDecision(
        agent_id=agent.agent_id,
        skill_id=artifact.skill_id,
        provider_id=selected.provider_id,
        capability=capability,
        deterministic_first=selected.deterministic,
        evidence=(
            f"skill_digest={artifact.digest}",
            f"authority_count={len(artifact.requested_authorities)}",
            *supply_chain_evidence,
            f"provider={selected.provider_id}",
        ),
    )
