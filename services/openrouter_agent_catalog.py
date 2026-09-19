"""Fail-closed OpenRouter free-model discovery for canonical text agents.

When user-visible model metadata exposes an exact zero price, the most capable
eligible direct free models are preferred. If the user-filtered catalog contains
no such direct model, the documented ``openrouter/free`` virtual router is used
as the only automatic fallback. Paid routing remains an explicit policy/budget
decision and is never selected by this bootstrap.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from services.agent_provider_capabilities import AGENT_GOVERNED_AI_CAPABILITIES
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
from services.p0_ai_provider_config import P0AIProviderConfiguration
from services.runtime.ai_provider_adapter import (
    AIProviderTransportError,
    GovernedAIProviderAdapter,
    OpenAICompatibleTransport,
    ProviderEndpoint,
    ProviderTransportResult,
)


class OpenRouterAgentCatalogError(RuntimeError):
    """OpenRouter catalog evidence is missing, malformed, or unsafe."""


_OPENROUTER_PROVIDER_ID = "openrouter"
_OPENROUTER_STRICT_WIRE_PROVIDER_ID = "openrouter-strict-wire"
_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
_OPENROUTER_MODELS_URL = f"{_OPENROUTER_BASE_URL}/models/user"
_OPENROUTER_FREE_ROUTER_ID = "openrouter/free"
_MAX_AUTO_MODELS = 12
_FREE_ROUTER_CONTEXT_WINDOW = 32_768
_FREE_ROUTER_MAX_OUTPUT_TOKENS = 2_048


class _StrictOpenRouterTransport(OpenAICompatibleTransport):
    """Require downstream support for the bounded, provider-filterable controls."""

    def complete(
        self,
        endpoint: ProviderEndpoint,
        *,
        api_key: str,
        model_id: str,
        system_instructions: str,
        prompt: str,
        max_output_tokens: int,
        response_format: dict[str, Any] | None = None,
        require_parameters: bool = False,
    ) -> ProviderTransportResult:
        if endpoint.provider_id != _OPENROUTER_PROVIDER_ID:
            raise OpenRouterAgentCatalogError(
                "strict OpenRouter transport received a non-OpenRouter endpoint"
            )

        # OpenRouter publishes provider support for the normalized ``max_tokens``
        # parameter. Dynamic routers such as ``openrouter/free`` do not guarantee
        # reasoning controls, and provider support metadata does not expose
        # ``modalities`` as a filterable request parameter. Serialize the strict
        # request through the generic OpenAI-compatible branch so the wire body
        # contains only parameters that ``require_parameters`` can enforce.
        wire_endpoint = ProviderEndpoint(
            _OPENROUTER_STRICT_WIRE_PROVIDER_ID,
            endpoint.base_url,
            endpoint.api_key_env,
            timeout_seconds=endpoint.timeout_seconds,
            max_retries=endpoint.max_retries,
            requires_api_key=endpoint.requires_api_key,
        )
        result = super().complete(
            wire_endpoint,
            api_key=api_key,
            model_id=model_id,
            system_instructions=system_instructions,
            prompt=prompt,
            max_output_tokens=max_output_tokens,
            response_format=response_format,
            require_parameters=True,
        )
        if result.output_tokens > max_output_tokens:
            raise AIProviderTransportError(
                "OpenRouter downstream exceeded the required output-token ceiling",
                retryable=True,
            )
        return result


class _TenantTemplateUsageGovernor(UsageGovernor):
    """Apply one conservative zero-cost template per actual tenant scope."""

    def __init__(
        self,
        registry: ModelProviderRegistry,
        tenant_limit: UsageLimits,
    ) -> None:
        super().__init__(registry, {})
        self._tenant_limit = tenant_limit

    def admit(self, request: UsageRequest, now: datetime) -> UsageEvidence:
        for scope in request.scopes:
            if scope.kind is not ScopeKind.TENANT:
                raise OpenRouterAgentCatalogError(
                    "automatic zero-cost routing accepts tenant scope only"
                )
            if scope not in self._limits:
                self._limits[scope] = self._tenant_limit
        return super().admit(request, now)


def discover_free_openrouter_agent_configuration(
    *,
    api_key: str | None = None,
    timeout_seconds: float = 10.0,
) -> P0AIProviderConfiguration | None:
    """Build a zero-cost agent configuration from live OpenRouter evidence.

    Direct exact-zero user-visible text models are preferred. If none are
    exposed, ``openrouter/free`` is admitted as a conservative virtual model.
    That router is never mixed with paid model IDs by this bootstrap.
    """
    secret = api_key if api_key is not None else os.environ.get("OPENROUTER_API_KEY", "")
    if not secret or not secret.strip():
        return None
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")
    request = urllib.request.Request(
        _OPENROUTER_MODELS_URL,
        headers={
            "Authorization": f"Bearer {secret.strip()}",
            "Accept": "application/json",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            document = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise OpenRouterAgentCatalogError(
            f"OpenRouter model catalog rejected the configured credential: HTTP {exc.code}"
        ) from exc
    except (urllib.error.URLError, TimeoutError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise OpenRouterAgentCatalogError("OpenRouter model catalog observation failed") from exc

    raw_models = document.get("data") if isinstance(document, dict) else None
    if not isinstance(raw_models, list):
        raise OpenRouterAgentCatalogError("OpenRouter model catalog contract is malformed")

    capabilities = _agent_capabilities()
    models = [
        model
        for raw in raw_models
        if (model := _eligible_free_text_model(raw, capabilities)) is not None
    ]
    models.sort(key=lambda item: (-item.context_window, item.model_id))
    models = models[:_MAX_AUTO_MODELS]
    if not models:
        models = [_free_router_model(capabilities)]

    return _configuration(models, capabilities)


def _configuration(
    models: list[ModelRecord],
    capabilities: frozenset[str],
) -> P0AIProviderConfiguration:
    if not models:
        raise OpenRouterAgentCatalogError("zero-cost model set cannot be empty")
    if any(
        model.provider_id != _OPENROUTER_PROVIDER_ID
        or model.input_cost_per_million != 0
        or model.output_cost_per_million != 0
        for model in models
    ):
        raise OpenRouterAgentCatalogError(
            "automatic OpenRouter configuration contains non-zero-cost routing"
        )

    registry = ModelProviderRegistry()
    registry.register_provider(ProviderRecord(_OPENROUTER_PROVIDER_ID, "openai-compatible"))
    for model in models:
        registry.register_model(model)
    fallback_order = tuple(model.model_id for model in models)
    policy = RoutingPolicy(
        allowed_models=frozenset(fallback_order),
        allowed_providers=frozenset({_OPENROUTER_PROVIDER_ID}),
        fallback_order=fallback_order,
    )
    conservative = UsageLimits(
        max_input_tokens=32_768,
        max_output_tokens=4_096,
        max_requests_daily=200,
        max_concurrency=4,
        daily_cost=Decimal(0),
        monthly_cost=Decimal(0),
        gpu_seconds_daily=Decimal(0),
        runtime_seconds_daily=Decimal("14400"),
        warning_fraction=Decimal("0.8"),
        max_retries=1,
        max_retry_cost=Decimal(0),
    )
    governor = _TenantTemplateUsageGovernor(registry, conservative)
    endpoint = ProviderEndpoint(
        _OPENROUTER_PROVIDER_ID,
        _OPENROUTER_BASE_URL,
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
        provider_capabilities={_OPENROUTER_PROVIDER_ID: capabilities},
        configured_scopes=(),
    )


def _agent_capabilities() -> frozenset[str]:
    return AGENT_GOVERNED_AI_CAPABILITIES


def _free_router_model(capabilities: frozenset[str]) -> ModelRecord:
    """Represent the documented free router with conservative local ceilings.

    The context/output values are ILAIOS admission ceilings, not a claim about
    the dynamically selected downstream model. The router itself remains the
    persisted requested model identity while provider response evidence can
    identify the downstream model when exposed by OpenRouter.
    """
    return ModelRecord(
        _OPENROUTER_FREE_ROUTER_ID,
        _OPENROUTER_PROVIDER_ID,
        capabilities,
        context_window=_FREE_ROUTER_CONTEXT_WINDOW,
        max_output_tokens=_FREE_ROUTER_MAX_OUTPUT_TOKENS,
        input_cost_per_million=Decimal(0),
        output_cost_per_million=Decimal(0),
    )


def _eligible_free_text_model(
    value: object,
    capabilities: frozenset[str],
) -> ModelRecord | None:
    if not isinstance(value, dict):
        return None
    model_id = value.get("id")
    context_length = value.get("context_length")
    pricing = value.get("pricing")
    architecture = value.get("architecture")
    supported = value.get("supported_parameters")
    top_provider = value.get("top_provider")
    if not isinstance(model_id, str) or not model_id.strip():
        return None
    if model_id.strip() == _OPENROUTER_FREE_ROUTER_ID:
        return None
    if not isinstance(context_length, int) or isinstance(context_length, bool) or context_length <= 0:
        return None
    if not isinstance(pricing, dict) or not isinstance(architecture, dict):
        return None
    if not isinstance(supported, list) or "max_tokens" not in supported:
        return None
    inputs = architecture.get("input_modalities")
    outputs = architecture.get("output_modalities")
    if not isinstance(inputs, list) or "text" not in inputs:
        return None
    if not isinstance(outputs, list) or "text" not in outputs:
        return None
    if not all(_zero_price(pricing.get(field)) for field in ("prompt", "completion", "request")):
        return None
    max_output = None
    if isinstance(top_provider, dict):
        candidate = top_provider.get("max_completion_tokens")
        if isinstance(candidate, int) and not isinstance(candidate, bool) and candidate > 0:
            max_output = candidate
    if max_output is None:
        max_output = min(4096, context_length)
    max_output = min(max_output, context_length)
    return ModelRecord(
        model_id.strip(),
        _OPENROUTER_PROVIDER_ID,
        capabilities,
        context_window=context_length,
        max_output_tokens=max_output,
        input_cost_per_million=Decimal(0),
        output_cost_per_million=Decimal(0),
    )


def _zero_price(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parsed = Decimal(value)
    except InvalidOperation:
        return False
    return parsed.is_finite() and parsed == 0
