"""Additive single-runtime composition for the six canonical Web agents."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from services.agent_registry import CANONICAL_AGENT_REGISTRY
from services.named_agent_executor import NamedAgentExecutor
from services.runtime.ai_provider_adapter import GovernedAIProviderAdapter
from services.web_agent_execution import (
    WEB_GOVERNED_AI_CAPABILITIES,
    WebProviderBackedExecutor,
)
from services.web_agent_skill_catalog import (
    WEB_FIRST_PARTY_AGENT_SKILLS,
    ensure_web_agent_skills,
)
from services.web_factory_skills import WEB_FACTORY_BROWSER_SKILL_IDS


class WebAgentRuntimeCompositionError(RuntimeError):
    """Web composition would violate canonical identity/provider boundaries."""


@dataclass(frozen=True, slots=True)
class WebAgentRuntimeComposition:
    named_executor: NamedAgentExecutor
    ai_executor: WebProviderBackedExecutor | None
    target_agent_count: int
    provisioned_identity_count: int
    skill_count: int
    browser_tool_required: bool

    @property
    def ai_configured(self) -> bool:
        return self.ai_executor is not None


def compose_web_agent_runtime(
    named_executor: NamedAgentExecutor,
    repository_root: Path,
    *,
    ai_adapter: GovernedAIProviderAdapter | None = None,
    ai_provider_capabilities: Mapping[str, frozenset[str]] | None = None,
) -> WebAgentRuntimeComposition:
    """Compose Web identities/skills on the already-created canonical runtime.

    BrowserQA's tool itself is composed separately by ``compose_browser_runtime``
    because that boundary requires environment-specific egress enforcement. This
    function never substitutes an LLM for BrowserQA.
    """
    web = tuple(
        item for item in CANONICAL_AGENT_REGISTRY if item.manifest.team == "web"
    )
    if len(web) != 6:
        raise WebAgentRuntimeCompositionError(
            "canonical Web population must contain exactly six agents"
        )
    for item in web:
        named_executor.ensure_agent(item.manifest.agent_id)

    digests = ensure_web_agent_skills(named_executor, repository_root.resolve())
    expected_skill_ids = {
        item.skill_id for item in WEB_FIRST_PARTY_AGENT_SKILLS
    } | set(WEB_FACTORY_BROWSER_SKILL_IDS)
    if set(digests) != expected_skill_ids:
        missing = sorted(expected_skill_ids - set(digests))
        extra = sorted(set(digests) - expected_skill_ids)
        raise WebAgentRuntimeCompositionError(
            f"Web runtime skill coverage drifted missing={missing} extra={extra}"
        )

    capabilities = dict(ai_provider_capabilities or {})
    ai_executor: WebProviderBackedExecutor | None = None
    if ai_adapter is None:
        if capabilities:
            raise WebAgentRuntimeCompositionError(
                "Web AI provider capabilities require the canonical governed adapter"
            )
    else:
        if not capabilities:
            raise WebAgentRuntimeCompositionError(
                "Web governed AI adapter requires explicit provider capability contracts"
            )
        available = frozenset(
            capability
            for provider_capabilities in capabilities.values()
            for capability in provider_capabilities
        )
        if not WEB_GOVERNED_AI_CAPABILITIES.issubset(available):
            raise WebAgentRuntimeCompositionError(
                "configured providers do not cover all five Web proposal capabilities"
            )
        for provider_id, provider_capabilities in sorted(capabilities.items()):
            named_executor.ensure_provider(
                provider_id,
                provider_capabilities,
                adapter_kind=ai_adapter.adapter_kind(provider_id),
                deterministic=False,
            )
        ai_executor = WebProviderBackedExecutor(named_executor, ai_adapter)

    return WebAgentRuntimeComposition(
        named_executor=named_executor,
        ai_executor=ai_executor,
        target_agent_count=6,
        provisioned_identity_count=6,
        skill_count=len(digests),
        browser_tool_required=True,
    )
