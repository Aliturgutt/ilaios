"""Fail-closed OpenRouter free-model discovery for canonical text agents.

This bootstrap is used only when an OpenRouter secret exists and no explicit
``ILAIOS_AGENT_AI_CONFIG_JSON`` contract was supplied. It never guesses prices:
only user-visible models whose prompt/completion/request prices are all exactly
zero are eligible. Paid routing remains an explicit policy/budget decision.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

from services.ai_governance import (
    ModelProviderRegistry,
    ModelRecord,
    ProviderRecord,
    RoutingPolicy,
    ScopeKind,
    UsageGovernor,
    UsageLimits,
)
from services.p0_agent_execution import P0_AGENT_BINDINGS
from services.p0_ai_provider_config import P0AIProviderConfiguration
from services.runtime.ai_provider_adapter import GovernedAIProviderAdapter, ProviderEndpoint


class OpenRouterAgentCatalogError(RuntimeError):
    """OpenRouter catalog evidence is missing, malformed, or unsafe."""


_OPENROUTER_PROVIDER_ID = "openrouter"
_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
_OPENROUTER_MODELS_URL = f"{_OPENROUTER_BASE_URL}/models/user"
_MAX_AUTO_MODELS = 12


def discover_free_openrouter_agent_configuration(
    *,
    api_key: str | None = None,
    timeout_seconds: float = 10.0,
) -> P0AIProviderConfiguration | None:
    """Build a zero-cost agent configuration from live user-filtered catalog evidence.

    Returns ``None`` when no secret exists. Any configured-secret/network/catalog
    failure raises so the caller can disable AI execution without fabricating
    readiness.
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

    capabilities = frozenset(
        {binding.capability for binding in P0_AGENT_BINDINGS if binding.execution_mode == "governed-ai"}
        | {"evidence.verify"}
    )
    models: list[ModelRecord] = []
    for raw in raw_models:
        model = _eligible_free_text_model(raw, capabilities)
        if model is not None:
            models.append(model)
    models.sort(key=lambda item: (-item.context_window, item.model_id))
    models = models[:_MAX_AUTO_MODELS]
    if not models:
        raise OpenRouterAgentCatalogError(
            "no user-eligible zero-cost OpenRouter text model satisfies the agent contract"
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
    governor = UsageGovernor(
        registry,
        {},
        default_limits={ScopeKind.TENANT: conservative},
    )
    endpoint = ProviderEndpoint(
        _OPENROUTER_PROVIDER_ID,
        _OPENROUTER_BASE_URL,
        "OPENROUTER_API_KEY",
        timeout_seconds=45.0,
        max_retries=1,
    )
    return P0AIProviderConfiguration(
        adapter=GovernedAIProviderAdapter(registry, policy, governor, (endpoint,)),
        provider_capabilities={_OPENROUTER_PROVIDER_ID: capabilities},
        configured_scopes=(),
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
