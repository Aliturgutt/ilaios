"""Additive single-runtime composition for Media and Intelligence agents."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from services.agent_registry import CANONICAL_AGENT_REGISTRY
from services.media_intelligence_agent_execution import (
    MEDIA_INTELLIGENCE_GOVERNED_AI_CAPABILITIES,
    MediaIntelligenceProviderBackedExecutor,
)
from services.media_intelligence_agent_skill_catalog import (
    MEDIA_INTELLIGENCE_FIRST_PARTY_SKILLS,
    ensure_media_intelligence_agent_skills,
)
from services.named_agent_executor import NamedAgentExecutor
from services.research_factory_skills import RESEARCH_FACTORY_SKILL_IDS
from services.runtime.ai_provider_adapter import GovernedAIProviderAdapter


class MediaIntelligenceAgentRuntimeCompositionError(RuntimeError):
    """Media/Intelligence composition violated canonical runtime boundaries."""


@dataclass(frozen=True, slots=True)
class MediaIntelligenceAgentRuntimeComposition:
    named_executor: NamedAgentExecutor
    ai_executor: MediaIntelligenceProviderBackedExecutor | None
    target_agent_count: int
    provisioned_identity_count: int
    skill_count: int
    direct_network_authority: bool = False
    direct_media_side_effect_authority: bool = False
    direct_publish_authority: bool = False

    @property
    def ai_configured(self) -> bool:
        return self.ai_executor is not None


def compose_media_intelligence_agent_runtime(
    named_executor: NamedAgentExecutor,
    repository_root: Path,
    *,
    ai_adapter: GovernedAIProviderAdapter | None = None,
    ai_provider_capabilities: Mapping[str, frozenset[str]] | None = None,
) -> MediaIntelligenceAgentRuntimeComposition:
    """Compose 8 Media + 4 Intelligence identities on the existing runtime."""
    registrations = tuple(
        item
        for item in CANONICAL_AGENT_REGISTRY
        if item.manifest.team in {"media", "intelligence"}
    )
    media_count = sum(item.manifest.team == "media" for item in registrations)
    intelligence_count = sum(
        item.manifest.team == "intelligence" for item in registrations
    )
    if len(registrations) != 12 or media_count != 8 or intelligence_count != 4:
        raise MediaIntelligenceAgentRuntimeCompositionError(
            "canonical Media/Intelligence population must be 8+4"
        )
    for item in registrations:
        named_executor.ensure_agent(item.manifest.agent_id)

    digests = ensure_media_intelligence_agent_skills(
        named_executor,
        repository_root.resolve(),
    )
    expected_skill_ids = {
        item.skill_id for item in MEDIA_INTELLIGENCE_FIRST_PARTY_SKILLS
    } | set(RESEARCH_FACTORY_SKILL_IDS)
    if set(digests) != expected_skill_ids:
        missing = sorted(expected_skill_ids - set(digests))
        extra = sorted(set(digests) - expected_skill_ids)
        raise MediaIntelligenceAgentRuntimeCompositionError(
            f"Media/Intelligence runtime skill coverage drifted missing={missing} extra={extra}"
        )

    capabilities = dict(ai_provider_capabilities or {})
    ai_executor: MediaIntelligenceProviderBackedExecutor | None = None
    if ai_adapter is None:
        if capabilities:
            raise MediaIntelligenceAgentRuntimeCompositionError(
                "Media/Intelligence AI capabilities require the canonical governed adapter"
            )
    else:
        if not capabilities:
            raise MediaIntelligenceAgentRuntimeCompositionError(
                "Media/Intelligence governed AI adapter requires provider contracts"
            )
        available = frozenset(
            capability
            for provider_capabilities in capabilities.values()
            for capability in provider_capabilities
        )
        if not MEDIA_INTELLIGENCE_GOVERNED_AI_CAPABILITIES.issubset(available):
            raise MediaIntelligenceAgentRuntimeCompositionError(
                "configured providers do not cover all Media/Intelligence proposal capabilities"
            )
        for provider_id, provider_capabilities in sorted(capabilities.items()):
            named_executor.ensure_provider(
                provider_id,
                provider_capabilities,
                adapter_kind=ai_adapter.adapter_kind(provider_id),
                deterministic=False,
            )
        ai_executor = MediaIntelligenceProviderBackedExecutor(
            named_executor,
            ai_adapter,
        )

    return MediaIntelligenceAgentRuntimeComposition(
        named_executor=named_executor,
        ai_executor=ai_executor,
        target_agent_count=12,
        provisioned_identity_count=12,
        skill_count=len(digests),
    )


__all__ = [
    "MediaIntelligenceAgentRuntimeComposition",
    "MediaIntelligenceAgentRuntimeCompositionError",
    "compose_media_intelligence_agent_runtime",
]
