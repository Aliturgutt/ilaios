"""Strict external configuration loader for governed AI providers."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

from services.agent_provider_capabilities import ALLOWED_AGENT_AI_CAPABILITIES
from services.ai_governance import (
    ModelProviderRegistry,
    ModelRecord,
    ProviderRecord,
    RoutingPolicy,
    Scope,
    ScopeKind,
    UsageGovernor,
    UsageLimits,
)
from services.runtime.ai_provider_adapter import GovernedAIProviderAdapter, ProviderEndpoint


class P0AIProviderConfigError(ValueError):
    """External AI provider/model/cost/limit configuration is unsafe or incomplete."""


@dataclass(frozen=True, slots=True)
class P0AIProviderConfiguration:
    adapter: GovernedAIProviderAdapter
    provider_capabilities: dict[str, frozenset[str]]
    configured_scopes: tuple[Scope, ...]


_ALLOWED_CAPABILITIES = ALLOWED_AGENT_AI_CAPABILITIES


def load_p0_ai_provider_configuration(
    raw: str | None = None,
) -> P0AIProviderConfiguration | None:
    text = raw if raw is not None else os.environ.get("ILAIOS_AGENT_AI_CONFIG_JSON", "")
    if not text or not text.strip():
        return None
    try:
        document = json.loads(text)
    except json.JSONDecodeError as exc:
        raise P0AIProviderConfigError("P0 AI configuration is not valid JSON") from exc
    if not isinstance(document, dict):
        raise P0AIProviderConfigError("P0 AI configuration must be an object")
    if set(document) != {"providers", "models", "routing", "limits"}:
        raise P0AIProviderConfigError("P0 AI configuration has unknown or missing top-level fields")

    providers_raw = document.get("providers")
    models_raw = document.get("models")
    routing_raw = document.get("routing")
    limits_raw = document.get("limits")
    if not isinstance(providers_raw, list) or not providers_raw:
        raise P0AIProviderConfigError("at least one AI provider is required")
    if not isinstance(models_raw, list) or not models_raw:
        raise P0AIProviderConfigError("at least one AI model is required")
    if not isinstance(routing_raw, dict):
        raise P0AIProviderConfigError("routing configuration must be an object")
    if not isinstance(limits_raw, list) or not limits_raw:
        raise P0AIProviderConfigError("at least one exact usage limit scope is required")

    registry = ModelProviderRegistry()
    endpoints: list[ProviderEndpoint] = []
    provider_ids: set[str] = set()
    for raw_provider in providers_raw:
        provider = _object(raw_provider, "provider")
        _exact_fields(
            provider,
            {"provider_id", "base_url", "api_key_env", "timeout_seconds", "max_retries"},
            "provider",
        )
        provider_id = _text(provider, "provider_id")
        if provider_id in provider_ids:
            raise P0AIProviderConfigError("provider IDs must be unique")
        provider_ids.add(provider_id)
        api_key_env = _text(provider, "api_key_env")
        if api_key_env.startswith(("sk-", "Bearer ")):
            raise P0AIProviderConfigError("api_key_env must name a secret variable, not contain a secret")
        timeout = _positive_number(provider.get("timeout_seconds"), "timeout_seconds")
        retries = _nonnegative_int(provider.get("max_retries"), "max_retries")
        registry.register_provider(ProviderRecord(provider_id, "openai-compatible"))
        endpoints.append(
            ProviderEndpoint(
                provider_id,
                _text(provider, "base_url"),
                api_key_env,
                timeout_seconds=timeout,
                max_retries=retries,
            )
        )

    provider_capabilities: dict[str, set[str]] = {provider_id: set() for provider_id in provider_ids}
    model_ids: set[str] = set()
    for raw_model in models_raw:
        model = _object(raw_model, "model")
        _exact_fields(
            model,
            {
                "model_id", "provider_id", "capabilities", "context_window",
                "max_output_tokens", "input_cost_per_million_usd",
                "output_cost_per_million_usd",
            },
            "model",
        )
        model_id = _text(model, "model_id")
        provider_id = _text(model, "provider_id")
        if model_id in model_ids:
            raise P0AIProviderConfigError("model IDs must be unique")
        if provider_id not in provider_ids:
            raise P0AIProviderConfigError("model references unknown provider")
        model_ids.add(model_id)
        capabilities = _string_set(model.get("capabilities"), "model capabilities")
        if not capabilities or not capabilities.issubset(_ALLOWED_CAPABILITIES):
            raise P0AIProviderConfigError("model capability exceeds P0 governed AI boundary")
        provider_capabilities[provider_id].update(capabilities)
        registry.register_model(
            ModelRecord(
                model_id,
                provider_id,
                capabilities,
                context_window=_positive_int(model.get("context_window"), "context_window"),
                max_output_tokens=_positive_int(model.get("max_output_tokens"), "max_output_tokens"),
                input_cost_per_million=_decimal(model.get("input_cost_per_million_usd"), "input_cost_per_million_usd"),
                output_cost_per_million=_decimal(model.get("output_cost_per_million_usd"), "output_cost_per_million_usd"),
            )
        )
    if any(not capabilities for capabilities in provider_capabilities.values()):
        raise P0AIProviderConfigError("every configured provider must back at least one model capability")

    _exact_fields(
        routing_raw,
        {"allowed_models", "denied_models", "allowed_providers", "denied_providers", "fallback_order"},
        "routing",
    )
    allowed_models = _string_set(routing_raw.get("allowed_models"), "allowed_models", allow_empty=True)
    denied_models = _string_set(routing_raw.get("denied_models"), "denied_models", allow_empty=True)
    allowed_providers = _string_set(routing_raw.get("allowed_providers"), "allowed_providers", allow_empty=True)
    denied_providers = _string_set(routing_raw.get("denied_providers"), "denied_providers", allow_empty=True)
    fallback_order = _string_tuple(routing_raw.get("fallback_order"), "fallback_order")
    if (allowed_models | denied_models | set(fallback_order)) - model_ids:
        raise P0AIProviderConfigError("routing references unknown model")
    if (allowed_providers | denied_providers) - provider_ids:
        raise P0AIProviderConfigError("routing references unknown provider")
    if len(fallback_order) != len(set(fallback_order)):
        raise P0AIProviderConfigError("fallback_order cannot contain duplicates")
    policy = RoutingPolicy(
        allowed_models=allowed_models,
        denied_models=denied_models,
        allowed_providers=allowed_providers,
        denied_providers=denied_providers,
        fallback_order=fallback_order,
    )

    limits: dict[Scope, UsageLimits] = {}
    for raw_limit in limits_raw:
        limit = _object(raw_limit, "limit")
        _exact_fields(
            limit,
            {
                "scope_kind", "scope_id", "max_input_tokens", "max_output_tokens",
                "max_requests_daily", "max_concurrency", "daily_cost_usd",
                "monthly_cost_usd", "gpu_seconds_daily", "runtime_seconds_daily",
                "warning_fraction", "max_retries", "max_retry_cost_usd",
            },
            "limit",
        )
        try:
            kind = ScopeKind(_text(limit, "scope_kind"))
        except ValueError as exc:
            raise P0AIProviderConfigError("usage limit scope_kind is invalid") from exc
        scope = Scope(kind, _text(limit, "scope_id"))
        if scope in limits:
            raise P0AIProviderConfigError("usage limit scopes must be unique")
        limits[scope] = UsageLimits(
            max_input_tokens=_positive_int(limit.get("max_input_tokens"), "max_input_tokens"),
            max_output_tokens=_positive_int(limit.get("max_output_tokens"), "max_output_tokens"),
            max_requests_daily=_positive_int(limit.get("max_requests_daily"), "max_requests_daily"),
            max_concurrency=_positive_int(limit.get("max_concurrency"), "max_concurrency"),
            daily_cost=_decimal(limit.get("daily_cost_usd"), "daily_cost_usd"),
            monthly_cost=_decimal(limit.get("monthly_cost_usd"), "monthly_cost_usd"),
            gpu_seconds_daily=_decimal(limit.get("gpu_seconds_daily"), "gpu_seconds_daily"),
            runtime_seconds_daily=_decimal(limit.get("runtime_seconds_daily"), "runtime_seconds_daily"),
            warning_fraction=_decimal(limit.get("warning_fraction"), "warning_fraction"),
            max_retries=_nonnegative_int(limit.get("max_retries"), "max_retries"),
            max_retry_cost=_decimal(limit.get("max_retry_cost_usd"), "max_retry_cost_usd"),
        )
    if not any(scope.kind is ScopeKind.TENANT for scope in limits):
        raise P0AIProviderConfigError("P0 AI configuration requires at least one tenant limit")

    governor = UsageGovernor(registry, limits)
    adapter = GovernedAIProviderAdapter(registry, policy, governor, tuple(endpoints))
    return P0AIProviderConfiguration(
        adapter=adapter,
        provider_capabilities={
            provider_id: frozenset(capabilities)
            for provider_id, capabilities in provider_capabilities.items()
        },
        configured_scopes=tuple(sorted(limits, key=lambda item: (item.kind.value, item.scope_id))),
    )


def _object(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise P0AIProviderConfigError(f"{label} must be an object")
    return value


def _exact_fields(value: dict[str, Any], expected: set[str], label: str) -> None:
    if set(value) != expected:
        raise P0AIProviderConfigError(f"{label} has unknown or missing fields")


def _text(value: dict[str, Any], field: str) -> str:
    item = value.get(field)
    if not isinstance(item, str) or not item or item != item.strip():
        raise P0AIProviderConfigError(f"{field} must be non-empty and trimmed")
    return item


def _positive_int(value: object, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise P0AIProviderConfigError(f"{field} must be a positive integer")
    return value


def _nonnegative_int(value: object, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise P0AIProviderConfigError(f"{field} must be a non-negative integer")
    return value


def _positive_number(value: object, field: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or float(value) <= 0:
        raise P0AIProviderConfigError(f"{field} must be positive")
    return float(value)


def _decimal(value: object, field: str) -> Decimal:
    if not isinstance(value, str):
        raise P0AIProviderConfigError(f"{field} must be a decimal string")
    try:
        parsed = Decimal(value)
    except InvalidOperation as exc:
        raise P0AIProviderConfigError(f"{field} is not a decimal") from exc
    if not parsed.is_finite() or parsed < 0:
        raise P0AIProviderConfigError(f"{field} must be finite and non-negative")
    return parsed


def _string_set(value: object, field: str, *, allow_empty: bool = False) -> frozenset[str]:
    items = _string_tuple(value, field)
    if not items and not allow_empty:
        raise P0AIProviderConfigError(f"{field} cannot be empty")
    return frozenset(items)


def _string_tuple(value: object, field: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(
        isinstance(item, str) and item and item == item.strip() for item in value
    ):
        raise P0AIProviderConfigError(f"{field} must be a trimmed string list")
    return tuple(value)
