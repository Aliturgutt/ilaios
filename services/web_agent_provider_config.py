"""Zero-cost provider configuration for canonical Web proposal agents.

This module does not introduce a provider engine. It builds another capability
contract around the existing GovernedAIProviderAdapter and the same OpenRouter
free-router transport used by P0.
"""

from __future__ import annotations

from decimal import Decimal

from services.ai_governance import (
    ModelProviderRegistry,
    ModelRecord,
    ProviderRecord,
    RoutingPolicy,
    ScopeKind,
    UsageEvidence,
    UsageGovernor,
    UsageLimits,
    UsageRequest,
)
from services.openrouter_agent_catalog import _StrictOpenRouterTransport
from services.p0_ai_provider_config import P0AIProviderConfiguration
from services.runtime.ai_provider_adapter import GovernedAIProviderAdapter, ProviderEndpoint

WEB_GOVERNED_AI_CAPABILITIES = frozenset(
    {"web.ux", "web.visual", "web.asset", "web.content", "web.seo"}
)


class WebAgentProviderConfigError(RuntimeError):
    """Web provider configuration violated zero-cost or capability boundaries."""


class _TenantTemplateUsageGovernor(UsageGovernor):
    def __init__(self, registry: ModelProviderRegistry, tenant_limit: UsageLimits) -> None:
        super().__init__(registry, {})
        self._tenant_limit = tenant_limit

    def admit(self, request: UsageRequest, now) -> UsageEvidence:  # type: ignore[no-untyped-def]
        for scope in request.scopes:
            if scope.kind is not ScopeKind.TENANT:
                raise WebAgentProviderConfigError(
                    "automatic Web zero-cost routing accepts tenant scope only"
                )
            if scope not in self._limits:
                self._limits[scope] = self._tenant_limit
        return super().admit(request, now)


def build_zero_cost_web_openrouter_configuration() -> P0AIProviderConfiguration:
    """Use only the documented OpenRouter free router for five Web proposal roles."""
    registry = ModelProviderRegistry()
    registry.register_provider(ProviderRecord("openrouter", "openai-compatible"))
    registry.register_model(
        ModelRecord(
            "openrouter/free",
            "openrouter",
            WEB_GOVERNED_AI_CAPABILITIES,
            context_window=32_768,
            max_output_tokens=2_048,
            input_cost_per_million=Decimal(0),
            output_cost_per_million=Decimal(0),
        )
    )
    policy = RoutingPolicy(
        allowed_models=frozenset({"openrouter/free"}),
        allowed_providers=frozenset({"openrouter"}),
        fallback_order=("openrouter/free",),
    )
    governor = _TenantTemplateUsageGovernor(
        registry,
        UsageLimits(
            max_input_tokens=32_768,
            max_output_tokens=4_096,
            max_requests_daily=100,
            max_concurrency=4,
            daily_cost=Decimal(0),
            monthly_cost=Decimal(0),
            gpu_seconds_daily=Decimal(0),
            runtime_seconds_daily=Decimal("7200"),
            warning_fraction=Decimal("0.8"),
            max_retries=1,
            max_retry_cost=Decimal(0),
        ),
    )
    endpoint = ProviderEndpoint(
        "openrouter",
        "https://openrouter.ai/api/v1",
        "OPENROUTER_API_KEY",
        timeout_seconds=45.0,
        max_retries=1,
    )
    return P0AIProviderConfiguration(
        adapter=GovernedAIProviderAdapter(
            registry,
            policy,
            governor,
            (endpoint,),
            transport=_StrictOpenRouterTransport(),
        ),
        provider_capabilities={"openrouter": WEB_GOVERNED_AI_CAPABILITIES},
        configured_scopes=(),
    )
