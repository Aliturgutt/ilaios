"""Governed external AI provider adapter for the canonical ILAIOS runtime.

Model/provider selection stays in ``services.ai_governance``. This module only
turns an already governed model decision into a bounded provider call that can
be injected into ``GovernedRuntime``. Secrets are read from environment-backed
secret injection at call time and are never persisted in runtime evidence.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from hashlib import sha256
from typing import Any, Protocol

from services.ai_governance import (
    ModelProviderRegistry,
    RoutingPolicy,
    Scope,
    ScopeKind,
    UsageGovernor,
    UsageRequest,
    route_model,
)


class AIProviderError(RuntimeError):
    """External AI execution failed closed."""


@dataclass(frozen=True, slots=True)
class ProviderEndpoint:
    provider_id: str
    base_url: str
    api_key_env: str
    timeout_seconds: float = 45.0
    max_retries: int = 1
    requires_api_key: bool = True

    def __post_init__(self) -> None:
        values = (self.provider_id, self.base_url, self.api_key_env)
        if any(not value or value != value.strip() for value in values):
            raise ValueError("provider endpoint fields must be non-empty and trimmed")
        if not self.base_url.startswith(("https://", "http://127.0.0.1", "http://localhost")):
            raise ValueError("provider endpoint must use HTTPS or explicit localhost")
        if self.timeout_seconds <= 0 or self.max_retries < 0:
            raise ValueError("provider timeout/retry configuration is invalid")


@dataclass(frozen=True, slots=True)
class ProviderTransportResult:
    text: str
    input_tokens: int
    output_tokens: int
    response_id: str

    def __post_init__(self) -> None:
        if not self.text:
            raise AIProviderError("provider returned empty output")
        if self.input_tokens < 0 or self.output_tokens < 0:
            raise AIProviderError("provider returned invalid usage")
        if not self.response_id:
            raise AIProviderError("provider response identity is required")


@dataclass(frozen=True, slots=True)
class AIModelSelection:
    model_id: str
    provider_id: str


class AIProviderTransport(Protocol):
    def complete(
        self,
        endpoint: ProviderEndpoint,
        *,
        api_key: str,
        model_id: str,
        prompt: str,
        max_output_tokens: int,
    ) -> ProviderTransportResult: ...


class OpenAICompatibleTransport:
    """Minimal fail-closed transport for OpenAI-compatible chat endpoints."""

    def complete(
        self,
        endpoint: ProviderEndpoint,
        *,
        api_key: str,
        model_id: str,
        prompt: str,
        max_output_tokens: int,
    ) -> ProviderTransportResult:
        url = f"{endpoint.base_url.rstrip('/')}/chat/completions"
        body = json.dumps(
            {
                "model": model_id,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_output_tokens,
            },
            separators=(",", ":"),
        ).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        request = urllib.request.Request(url, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=endpoint.timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise AIProviderError("provider transport failed") from exc

        try:
            text = payload["choices"][0]["message"]["content"]
            usage = payload["usage"]
            input_tokens = int(usage["prompt_tokens"])
            output_tokens = int(usage["completion_tokens"])
            response_id = str(payload["id"])
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise AIProviderError("provider response contract is incomplete") from exc
        if not isinstance(text, str):
            raise AIProviderError("provider output must be text")
        return ProviderTransportResult(text, input_tokens, output_tokens, response_id)


class GovernedAIProviderAdapter:
    """Bind model routing, quota/cost governance, retries and provider calls."""

    def __init__(
        self,
        registry: ModelProviderRegistry,
        policy: RoutingPolicy,
        governor: UsageGovernor,
        endpoints: tuple[ProviderEndpoint, ...],
        *,
        transport: AIProviderTransport | None = None,
        secret_reader: Callable[[str], str | None] = os.environ.get,
    ) -> None:
        self._registry = registry
        self._policy = policy
        self._governor = governor
        self._endpoints = {item.provider_id: item for item in endpoints}
        if not self._endpoints:
            raise ValueError("at least one governed provider endpoint is required")
        if len(self._endpoints) != len(endpoints):
            raise ValueError("provider endpoint IDs must be unique")
        for provider_id in self._endpoints:
            self._registry.provider(provider_id)
        self._transport = transport or OpenAICompatibleTransport()
        self._secret_reader = secret_reader

    def select(
        self,
        capability: str,
        *,
        denied_models: frozenset[str] = frozenset(),
    ) -> AIModelSelection:
        """Select a model without exposing model choice to the product user."""
        denied = set(self._policy.denied_models) | set(denied_models)
        while True:
            policy = RoutingPolicy(
                allowed_models=self._policy.allowed_models,
                denied_models=frozenset(denied),
                allowed_providers=self._policy.allowed_providers,
                denied_providers=self._policy.denied_providers,
                fallback_order=self._policy.fallback_order,
            )
            model = route_model(self._registry, policy, capability)
            if model.provider_id in self._endpoints:
                return AIModelSelection(model.model_id, model.provider_id)
            denied.add(model.model_id)

    def adapter_kind(self, provider_id: str) -> str:
        if provider_id not in self._endpoints:
            raise AIProviderError("provider endpoint is not configured")
        digest = sha256(provider_id.encode("utf-8")).hexdigest()[:16]
        return f"ilaios.runtime.ai.{digest}"

    def runtime_adapters(self) -> Mapping[str, Callable[[dict[str, Any]], dict[str, Any]]]:
        """Return provider-specific adapters for injection into GovernedRuntime."""
        return {
            self.adapter_kind(provider_id): (
                lambda payload, bound_provider=provider_id: self._execute_provider(
                    bound_provider, payload
                )
            )
            for provider_id in sorted(self._endpoints)
        }

    def _execute_provider(
        self, provider_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        endpoint = self._endpoints[provider_id]
        model_id = _required_text(payload, "model_id")
        prompt = _required_text(payload, "prompt")
        request_id = _required_text(payload, "request_id")
        tenant_id = _required_text(payload, "tenant_id")
        model = self._registry.model(model_id)
        if model.provider_id != provider_id:
            raise AIProviderError("selected model/provider identity mismatch")

        input_tokens = _required_nonnegative_int(payload, "input_tokens")
        max_output_tokens = _required_positive_int(payload, "max_output_tokens")
        scopes = _parse_scopes(payload.get("scopes"))
        now = _parse_now(payload.get("now"))

        api_key = self._secret_reader(endpoint.api_key_env) or ""
        if endpoint.requires_api_key and not api_key:
            raise AIProviderError("provider credential is unavailable")

        retry_cost = Decimal(0)
        last_error: Exception | None = None
        for attempt in range(endpoint.max_retries + 1):
            estimated_cost = _cost(
                model.input_cost_per_million,
                model.output_cost_per_million,
                input_tokens,
                max_output_tokens,
            )
            usage_request = UsageRequest(
                request_id=f"{request_id}:attempt:{attempt}",
                tenant_id=tenant_id,
                scopes=scopes,
                model_id=model_id,
                input_tokens=input_tokens,
                output_tokens=max_output_tokens,
                estimated_cost=estimated_cost,
                retry_number=attempt,
                retry_accumulated_cost=retry_cost,
            )
            admitted = self._governor.admit(usage_request, now)
            started = time.monotonic()
            try:
                response = self._transport.complete(
                    endpoint,
                    api_key=api_key,
                    model_id=model_id,
                    prompt=prompt,
                    max_output_tokens=max_output_tokens,
                )
            except Exception as exc:  # transport boundary is intentionally fail-closed
                self._governor.complete(admitted)
                self._governor.record_provider_failure(provider_id, now)
                retry_cost += estimated_cost
                last_error = exc
                continue

            self._governor.complete(admitted)
            actual_cost = _cost(
                model.input_cost_per_million,
                model.output_cost_per_million,
                response.input_tokens,
                response.output_tokens,
            )
            return {
                "text": response.text,
                "response_id": response.response_id,
                "model_id": model_id,
                "provider_id": provider_id,
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
                "actual_cost_usd": str(actual_cost),
                "reserved_cost_usd": str(estimated_cost),
                "latency_ms": int((time.monotonic() - started) * 1000),
                "attempt": attempt,
                "usage_warnings": list(admitted.warnings),
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }

        raise AIProviderError("provider retries exhausted") from last_error


def _parse_scopes(value: object) -> tuple[Scope, ...]:
    if not isinstance(value, list) or not value:
        raise AIProviderError("provider execution requires governed scopes")
    scopes: list[Scope] = []
    for item in value:
        if not isinstance(item, dict):
            raise AIProviderError("scope evidence must be an object")
        try:
            kind = ScopeKind(str(item["kind"]))
            scope_id = str(item["scope_id"])
        except (KeyError, ValueError) as exc:
            raise AIProviderError("scope evidence is invalid") from exc
        scopes.append(Scope(kind, scope_id))
    return tuple(scopes)


def _parse_now(value: object) -> datetime:
    if not isinstance(value, str):
        raise AIProviderError("provider execution requires serialized timestamp")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise AIProviderError("provider execution timestamp is invalid") from exc
    if parsed.tzinfo is None:
        raise AIProviderError("provider execution timestamp must be timezone-aware")
    return parsed


def _cost(
    input_rate: Decimal,
    output_rate: Decimal,
    input_tokens: int,
    output_tokens: int,
) -> Decimal:
    million = Decimal(1_000_000)
    return (Decimal(input_tokens) * input_rate / million) + (
        Decimal(output_tokens) * output_rate / million
    )


def _required_text(payload: dict[str, Any], field: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value or value != value.strip():
        raise AIProviderError(f"{field} must be non-empty and trimmed")
    return value


def _required_nonnegative_int(payload: dict[str, Any], field: str) -> int:
    value = payload.get(field)
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise AIProviderError(f"{field} must be a non-negative integer")
    return value


def _required_positive_int(payload: dict[str, Any], field: str) -> int:
    value = _required_nonnegative_int(payload, field)
    if value <= 0:
        raise AIProviderError(f"{field} must be positive")
    return value
