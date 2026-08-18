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
    GovernanceError,
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


class AIProviderAuthorizationError(AIProviderError):
    """Provider credential/credit/permission failure; model fallback cannot fix it."""


class AIProviderTransportError(AIProviderError):
    """Provider transport failure with explicit retryability metadata."""

    def __init__(
        self,
        message: str,
        *,
        retryable: bool,
        retry_after_seconds: float | None = None,
    ) -> None:
        super().__init__(message)
        self.retryable = retryable
        self.retry_after_seconds = retry_after_seconds


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
        if not self.base_url.startswith(
            ("https://", "http://127.0.0.1", "http://localhost")
        ):
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


@dataclass(frozen=True, slots=True)
class RuntimeSkillContext:
    skill_id: str
    sha256: str
    instructions: str


class AIProviderTransport(Protocol):
    def complete(
        self,
        endpoint: ProviderEndpoint,
        *,
        api_key: str,
        model_id: str,
        system_instructions: str,
        prompt: str,
        max_output_tokens: int,
    ) -> ProviderTransportResult: ...


RuntimeAdapter = Callable[[dict[str, Any]], dict[str, Any]]
_INDEPENDENT_VERIFIER_SKILL_ID = "ilaios.skill.meta.independent-verification.v1"


class OpenAICompatibleTransport:
    """Fail-closed OpenAI-compatible transport with bounded error classification."""

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
        url = f"{endpoint.base_url.rstrip('/')}/chat/completions"
        request_document: dict[str, Any] = {
            "model": model_id,
            "messages": [
                {"role": "system", "content": system_instructions},
                {"role": "user", "content": prompt},
            ],
        }
        if endpoint.provider_id == "openrouter":
            request_document["max_completion_tokens"] = max_output_tokens
            # P0 text agents must not silently route into image/audio output.
            request_document["modalities"] = ["text"]
        else:
            request_document["max_tokens"] = max_output_tokens
        if endpoint.provider_id == "openrouter" and response_format is None:
            request_document["reasoning"] = {
                "effort": "minimal",
                "exclude": True,
            }
        if response_format is not None:
            request_document["response_format"] = response_format
        if require_parameters:
            request_document["provider"] = {"require_parameters": True}
        body = json.dumps(request_document, separators=(",", ":")).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        request = urllib.request.Request(url, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(
                request, timeout=endpoint.timeout_seconds
            ) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            retry_after = _retry_after_seconds(exc)
            if exc.code in {401, 402, 403}:
                raise AIProviderAuthorizationError(
                    f"provider authorization/billing failure: HTTP {exc.code}"
                ) from exc
            raise AIProviderTransportError(
                f"provider HTTP failure: {exc.code}",
                retryable=exc.code in {408, 429, 500, 502, 503, 504},
                retry_after_seconds=retry_after,
            ) from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            raise AIProviderTransportError(
                "provider transport failed", retryable=True
            ) from exc
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise AIProviderTransportError(
                "provider returned malformed JSON", retryable=True
            ) from exc

        try:
            choice = payload["choices"][0]
            usage = payload["usage"]
            input_tokens = int(usage["prompt_tokens"])
            output_tokens = int(usage["completion_tokens"])
            response_id = str(payload["id"])
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise AIProviderTransportError(
                "provider response contract is incomplete", retryable=True
            ) from exc
        text = _completion_text(choice)
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

    def runtime_adapters(self) -> Mapping[str, RuntimeAdapter]:
        return {
            self.adapter_kind(provider_id): self._bind_runtime_adapter(provider_id)
            for provider_id in sorted(self._endpoints)
        }

    def _bind_runtime_adapter(self, provider_id: str) -> RuntimeAdapter:
        def execute(payload: dict[str, Any]) -> dict[str, Any]:
            return self._execute_provider(provider_id, payload)

        return execute

    def provider_health(self, now: datetime) -> tuple[dict[str, object], ...]:
        return tuple(
            self._governor.provider_health(provider_id, now)
            for provider_id in sorted(self._endpoints)
        )

    def usage_snapshot(self, scope: Scope, now: datetime) -> dict[str, object]:
        return self._governor.usage_snapshot(scope, now)

    def _execute_provider(
        self, provider_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        endpoint = self._endpoints[provider_id]
        model_id = _required_text(payload, "model_id")
        prompt = _required_text(payload, "prompt")
        request_id = _required_text(payload, "request_id")
        tenant_id = _required_text(payload, "tenant_id")
        skill = _parse_runtime_skill(payload.get("_ilaios_skill"))
        model = self._registry.model(model_id)
        if model.provider_id != provider_id:
            raise AIProviderError("selected model/provider identity mismatch")

        input_tokens = _required_nonnegative_int(payload, "input_tokens")
        max_output_tokens = _required_positive_int(payload, "max_output_tokens")
        reserved_input_tokens = max(
            input_tokens,
            len(prompt.encode("utf-8"))
            + len(skill.instructions.encode("utf-8")),
        )
        scopes = _parse_scopes(payload.get("scopes"))
        now = _parse_now(payload.get("now"))

        api_key = self._secret_reader(endpoint.api_key_env) or ""
        if endpoint.requires_api_key and not api_key:
            raise AIProviderAuthorizationError("provider credential is unavailable")

        retry_cost = Decimal(0)
        last_error: Exception | None = None
        for attempt in range(endpoint.max_retries + 1):
            estimated_cost = _cost(
                model.input_cost_per_million,
                model.output_cost_per_million,
                reserved_input_tokens,
                max_output_tokens,
            )
            usage_request = UsageRequest(
                request_id=(
                    f"{request_id}:provider:{provider_id}:model:{model_id}:attempt:{attempt}"
                ),
                tenant_id=tenant_id,
                scopes=scopes,
                model_id=model_id,
                input_tokens=reserved_input_tokens,
                output_tokens=max_output_tokens,
                estimated_cost=estimated_cost,
                retry_number=attempt,
                retry_accumulated_cost=retry_cost,
            )
            admitted = self._governor.admit(usage_request, now)
            started = time.monotonic()
            try:
                response_format = _structured_response_format(skill.skill_id)
                if response_format is not None and isinstance(
                    self._transport, OpenAICompatibleTransport
                ):
                    response = self._transport.complete(
                        endpoint,
                        api_key=api_key,
                        model_id=model_id,
                        system_instructions=skill.instructions,
                        prompt=prompt,
                        max_output_tokens=max_output_tokens,
                        response_format=response_format,
                        require_parameters=True,
                    )
                else:
                    response = self._transport.complete(
                        endpoint,
                        api_key=api_key,
                        model_id=model_id,
                        system_instructions=skill.instructions,
                        prompt=prompt,
                        max_output_tokens=max_output_tokens,
                    )
            except AIProviderAuthorizationError:
                self._governor.complete(admitted)
                self._governor.record_provider_failure(provider_id, now)
                raise
            except AIProviderTransportError as exc:
                self._governor.complete(admitted)
                self._governor.record_provider_failure(provider_id, now)
                retry_cost += estimated_cost
                last_error = exc
                if not exc.retryable or attempt >= endpoint.max_retries:
                    raise
                if exc.retry_after_seconds is not None:
                    time.sleep(min(exc.retry_after_seconds, 2.0))
                continue
            except Exception:
                self._governor.complete(admitted)
                self._governor.record_provider_failure(provider_id, now)
                raise

            if response.input_tokens > reserved_input_tokens:
                self._governor.complete(admitted)
                self._governor.record_provider_failure(provider_id, now)
                raise AIProviderError(
                    "provider exceeded reserved input-token ceiling: "
                    f"requested={reserved_input_tokens} observed={response.input_tokens}"
                )
            if response.output_tokens > max_output_tokens:
                self._governor.complete(admitted)
                self._governor.record_provider_failure(provider_id, now)
                raise AIProviderError(
                    "provider exceeded requested output-token ceiling: "
                    f"requested={max_output_tokens} observed={response.output_tokens}"
                )
            actual_cost = _cost(
                model.input_cost_per_million,
                model.output_cost_per_million,
                response.input_tokens,
                response.output_tokens,
            )
            try:
                self._governor.reconcile_cost(admitted, actual_cost)
                self._governor.complete(admitted)
            except GovernanceError as exc:
                try:
                    self._governor.complete(admitted)
                except GovernanceError:
                    pass
                self._governor.record_provider_failure(provider_id, now)
                raise AIProviderError(
                    "provider usage reconciliation failed"
                ) from exc
            self._governor.record_provider_success(provider_id, now)
            health = self._governor.provider_health(provider_id, now)
            return {
                "text": response.text,
                "response_id": response.response_id,
                "model_id": model_id,
                "provider_id": provider_id,
                "skill_id": skill.skill_id,
                "skill_sha256": skill.sha256,
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
                "actual_cost_usd": str(actual_cost),
                "reserved_cost_usd": str(estimated_cost),
                "latency_ms": int((time.monotonic() - started) * 1000),
                "attempt": attempt,
                "usage_warnings": list(admitted.warnings),
                "provider_health": health,
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }

        raise AIProviderError("provider retries exhausted") from last_error


def _completion_text(choice: object) -> str:
    """Return only canonical assistant text; classify no-content responses safely."""
    if not isinstance(choice, dict):
        raise AIProviderTransportError(
            "provider completion choice is malformed", retryable=True
        )
    embedded_error = choice.get("error")
    if embedded_error is not None:
        raise AIProviderTransportError(
            "provider completion ended with an in-body error", retryable=True
        )
    message = choice.get("message")
    if not isinstance(message, dict):
        raise AIProviderTransportError(
            "provider completion message is missing", retryable=True
        )
    content = message.get("content")
    finish_reason = choice.get("finish_reason")
    if isinstance(content, str) and content.strip():
        return content
    if content is None and finish_reason == "length":
        raise AIProviderTransportError(
            "provider exhausted completion budget before returning text",
            retryable=True,
        )
    if content is None:
        raise AIProviderTransportError(
            "provider returned no text content", retryable=True
        )
    if isinstance(content, str):
        raise AIProviderTransportError(
            "provider returned empty text content", retryable=True
        )
    raise AIProviderTransportError(
        "provider returned a non-text completion despite text-only request",
        retryable=True,
    )


def _structured_response_format(skill_id: str) -> dict[str, Any] | None:
    if skill_id != _INDEPENDENT_VERIFIER_SKILL_ID:
        return None
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "ilaios_independent_verification",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "verdict": {"type": "string", "enum": ["PASS", "FAIL"]},
                    "producer_evidence_digest": {
                        "type": "string",
                        "pattern": "^[0-9a-f]{64}$",
                    },
                    "findings": {
                        "type": "array",
                        "items": {"type": "string", "minLength": 1},
                    },
                },
                "required": [
                    "verdict",
                    "producer_evidence_digest",
                    "findings",
                ],
                "additionalProperties": False,
            },
        },
    }


def _retry_after_seconds(error: urllib.error.HTTPError) -> float | None:
    if error.code not in {429, 503}:
        return None
    raw = error.headers.get("Retry-After") if error.headers is not None else None
    if raw is None:
        return None
    try:
        value = float(raw)
    except ValueError:
        return None
    return value if 0 < value <= 60 else None


def _parse_runtime_skill(value: object) -> RuntimeSkillContext:
    if not isinstance(value, dict) or set(value) != {
        "skill_id",
        "sha256",
        "instructions",
    }:
        raise AIProviderError("runtime skill context is missing or malformed")
    skill_id = value.get("skill_id")
    digest = value.get("sha256")
    instructions = value.get("instructions")
    if not isinstance(skill_id, str) or not skill_id.strip():
        raise AIProviderError("runtime skill identity is invalid")
    if not isinstance(digest, str) or len(digest) != 64 or any(
        character not in "0123456789abcdef" for character in digest
    ):
        raise AIProviderError("runtime skill digest is invalid")
    if not isinstance(instructions, str) or not instructions.strip():
        raise AIProviderError("runtime skill instructions are invalid")
    if sha256(instructions.encode("utf-8")).hexdigest() != digest:
        raise AIProviderError("runtime skill digest does not match instructions")
    return RuntimeSkillContext(skill_id.strip(), digest, instructions)


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
        raise AIProviderError(
            "provider execution requires serialized timestamp"
        )
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise AIProviderError("provider execution timestamp is invalid") from exc
    if parsed.tzinfo is None:
        raise AIProviderError(
            "provider execution timestamp must be timezone-aware"
        )
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
