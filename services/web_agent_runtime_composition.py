"""Single-runtime composition for the six canonical Web agents."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from services.agent_governance import GrantAuthorizer
from services.agent_registry import INDEPENDENT_VERIFIER_ID, registration_for
from services.browser_runtime_composition import ensure_web_factory_browser_skills
from services.independent_verifier_execution import (
    INDEPENDENT_VERIFIER_ADAPTER_KIND,
    INDEPENDENT_VERIFIER_PROVIDER_ID,
)
from services.named_agent_executor import NamedAgentExecutor
from services.runtime import GovernedRuntime
from services.runtime.ai_provider_adapter import GovernedAIProviderAdapter
from services.runtime.browser_evidence_adapter import (
    BROWSER_EVIDENCE_ADAPTER_KIND,
    BROWSER_EVIDENCE_CAPABILITY,
    BROWSER_EVIDENCE_PROVIDER_ID,
    BrowserEvidenceRuntimeAdapter,
)
from services.web_agent_execution import (
    WEB_AGENT_BINDINGS,
    WebBrowserEvidenceExecutor,
    WebProviderBackedExecutor,
)
from services.web_agent_skill_catalog import ensure_web_agent_proposal_skills


class WebAgentRuntimeCompositionError(RuntimeError):
    """Web composition would violate canonical runtime/provider boundaries."""


@dataclass(frozen=True, slots=True)
class WebAgentRuntimeComposition:
    named_executor: NamedAgentExecutor
    ai_executor: WebProviderBackedExecutor
    browser_evidence_executor: WebBrowserEvidenceExecutor
    target_agent_count: int
    skill_count: int
    ai_provider_count: int
    local_provider_count: int


def compose_web_agent_runtime(
    runtime: GovernedRuntime,
    grants: GrantAuthorizer,
    *,
    repository_root: Path,
    browser_evidence_adapter: BrowserEvidenceRuntimeAdapter,
    ai_adapter: GovernedAIProviderAdapter,
    ai_provider_capabilities: Mapping[str, frozenset[str]],
) -> WebAgentRuntimeComposition:
    web_registrations = tuple(
        registration_for(binding.agent_id) for binding in WEB_AGENT_BINDINGS
    )
    if len(web_registrations) != 6:
        raise WebAgentRuntimeCompositionError("canonical Web population must contain six agents")
    named = NamedAgentExecutor(runtime, grants)
    for registration in web_registrations:
        named.ensure_agent(registration.manifest.agent_id)
    named.ensure_agent(INDEPENDENT_VERIFIER_ID)

    proposal_skills = ensure_web_agent_proposal_skills(named)
    browser_skills = ensure_web_factory_browser_skills(named, repository_root.resolve())
    if len(proposal_skills) != 5 or len(browser_skills) != 4:
        raise WebAgentRuntimeCompositionError("Web skill coverage drifted")

    named.ensure_provider(
        INDEPENDENT_VERIFIER_PROVIDER_ID,
        frozenset({"evidence.verify"}),
        adapter_kind=INDEPENDENT_VERIFIER_ADAPTER_KIND,
        deterministic=True,
    )

    expected_ai_capabilities = frozenset(
        binding.capability
        for binding in WEB_AGENT_BINDINGS
        if binding.execution_mode == "governed-ai"
    )
    if not ai_provider_capabilities:
        raise WebAgentRuntimeCompositionError("Web AI provider capabilities are required")
    for provider_id, capabilities in sorted(ai_provider_capabilities.items()):
        if not capabilities or not capabilities.issubset(expected_ai_capabilities):
            raise WebAgentRuntimeCompositionError(
                "Web AI provider capability contract exceeds canonical Web proposal roles"
            )
        named.ensure_provider(
            provider_id,
            capabilities,
            adapter_kind=ai_adapter.adapter_kind(provider_id),
            deterministic=False,
        )

    browser_adapters = browser_evidence_adapter.runtime_adapters()
    if set(browser_adapters) != {BROWSER_EVIDENCE_ADAPTER_KIND}:
        raise WebAgentRuntimeCompositionError("BrowserQA evidence adapter contract drifted")
    named.ensure_provider(
        BROWSER_EVIDENCE_PROVIDER_ID,
        frozenset({BROWSER_EVIDENCE_CAPABILITY}),
        adapter_kind=BROWSER_EVIDENCE_ADAPTER_KIND,
        deterministic=True,
    )

    return WebAgentRuntimeComposition(
        named_executor=named,
        ai_executor=WebProviderBackedExecutor(named, ai_adapter),
        browser_evidence_executor=WebBrowserEvidenceExecutor(
            named, BROWSER_EVIDENCE_PROVIDER_ID
        ),
        target_agent_count=6,
        skill_count=len(set(proposal_skills) | set(browser_skills)),
        ai_provider_count=len(ai_provider_capabilities),
        local_provider_count=2,
    )
