"""Deterministic, provider-neutral AI usage and cost governance.

This module is a control-plane reference implementation. It performs no
provider calls and grants no authorization; callers must pass an already
authorized request and cannot override the controls represented here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum


class GovernanceError(RuntimeError):
    """A request failed closed at an AI governance boundary."""


def _text(name: str, value: str) -> None:
    if not value or value != value.strip():
        raise ValueError(f"{name} must be non-empty without surrounding whitespace")


@dataclass(frozen=True, slots=True)
class ProviderRecord:
    provider_id: str
    adapter_id: str
    enabled: bool = True

    def __post_init__(self) -> None:
        _text("provider_id", self.provider_id)
        _text("adapter_id", self.adapter_id)


@dataclass(frozen=True, slots=True)
class ModelRecord:
    model_id: str
    provider_id: str
    capabilities: frozenset[str]
    context_window: int
    max_output_tokens: int
    input_cost_per_million: Decimal = Decimal(0)
    output_cost_per_million: Decimal = Decimal(0)
    gpu_seconds_per_request: Decimal = Decimal(0)
    enabled: bool = True

    def __post_init__(self) -> None:
        _text("model_id", self.model_id)
        _text("provider_id", self.provider_id)
        if self.context_window <= 0 or self.max_output_tokens <= 0:
            raise ValueError("token limits must be positive")
        if self.max_output_tokens > self.context_window:
            raise ValueError("max_output_tokens cannot exceed context_window")
        costs = (
            self.input_cost_per_million,
            self.output_cost_per_million,
            self.gpu_seconds_per_request,
        )
        if any(value < 0 for value in costs):
            raise ValueError("cost and runtime metadata cannot be negative")


class ModelProviderRegistry:
    """Immutable-record registry with explicit provider/model relationships."""

    def __init__(self) -> None:
        self._providers: dict[str, ProviderRecord] = {}
        self._models: dict[str, ModelRecord] = {}

    def register_provider(self, provider: ProviderRecord) -> None:
        if provider.provider_id in self._providers:
            raise ValueError("provider already registered")
        self._providers[provider.provider_id] = provider

    def register_model(self, model: ModelRecord) -> None:
        if model.model_id in self._models:
            raise ValueError("model already registered")
        if model.provider_id not in self._providers:
            raise ValueError("model provider is not registered")
        self._models[model.model_id] = model

    def model(self, model_id: str) -> ModelRecord:
        try:
            return self._models[model_id]
        except KeyError as exc:
            raise GovernanceError("model is not registered") from exc

    def provider(self, provider_id: str) -> ProviderRecord:
        try:
            return self._providers[provider_id]
        except KeyError as exc:
            raise GovernanceError("provider is not registered") from exc

    def eligible(self, capability: str) -> tuple[ModelRecord, ...]:
        return tuple(
            model
            for model in sorted(self._models.values(), key=lambda item: item.model_id)
            if model.enabled
            and capability in model.capabilities
            and self._providers[model.provider_id].enabled
        )


@dataclass(frozen=True, slots=True)
class RoutingPolicy:
    allowed_models: frozenset[str] = frozenset()
    denied_models: frozenset[str] = frozenset()
    allowed_providers: frozenset[str] = frozenset()
    denied_providers: frozenset[str] = frozenset()
    fallback_order: tuple[str, ...] = ()

    def permits(self, model: ModelRecord) -> bool:
        return bool(
            model.model_id not in self.denied_models
            and model.provider_id not in self.denied_providers
            and (not self.allowed_models or model.model_id in self.allowed_models)
            and (not self.allowed_providers or model.provider_id in self.allowed_providers)
        )


def route_model(
    registry: ModelProviderRegistry,
    policy: RoutingPolicy,
    capability: str,
    preferred_model: str | None = None,
) -> ModelRecord:
    """Route deterministically; policy applies to preferred and fallback paths."""
    candidates = {model.model_id: model for model in registry.eligible(capability)}
    order = ((preferred_model,) if preferred_model else ()) + policy.fallback_order
    order += tuple(sorted(set(candidates) - set(order)))
    for model_id in order:
        model = candidates.get(model_id)
        if model is not None and policy.permits(model):
            return model
    raise GovernanceError("no model satisfies capability and policy")


class ScopeKind(str, Enum):
    USER = "user"
    TENANT = "tenant"
    PROJECT = "project"
    JOB = "job"
    PROVIDER = "provider"
    MODEL = "model"


@dataclass(frozen=True, slots=True)
class Scope:
    kind: ScopeKind
    scope_id: str

    def __post_init__(self) -> None:
        _text("scope_id", self.scope_id)


@dataclass(frozen=True, slots=True)
class UsageLimits:
    max_input_tokens: int
    max_output_tokens: int
    max_requests_daily: int
    max_concurrency: int
    daily_cost: Decimal
    monthly_cost: Decimal
    gpu_seconds_daily: Decimal
    runtime_seconds_daily: Decimal
    warning_fraction: Decimal = Decimal("0.8")
    max_retries: int = 0
    max_retry_cost: Decimal = Decimal(0)

    def __post_init__(self) -> None:
        numeric = (
            self.max_input_tokens,
            self.max_output_tokens,
            self.max_requests_daily,
            self.max_concurrency,
        )
        if any(value <= 0 for value in numeric):
            raise ValueError("request and token limits must be positive")
        budgets = (
            self.daily_cost,
            self.monthly_cost,
            self.gpu_seconds_daily,
            self.runtime_seconds_daily,
            self.max_retry_cost,
        )
        if any(value < 0 for value in budgets) or self.max_retries < 0:
            raise ValueError("budgets cannot be negative")
        if not Decimal(0) < self.warning_fraction <= Decimal(1):
            raise ValueError("warning_fraction must be in (0, 1]")


@dataclass(frozen=True, slots=True)
class UsageRequest:
    request_id: str
    tenant_id: str
    scopes: tuple[Scope, ...]
    model_id: str
    input_tokens: int
    output_tokens: int
    estimated_cost: Decimal
    estimated_gpu_seconds: Decimal = Decimal(0)
    estimated_runtime_seconds: Decimal = Decimal(0)
    retry_number: int = 0
    retry_accumulated_cost: Decimal = Decimal(0)

    def __post_init__(self) -> None:
        _text("request_id", self.request_id)
        _text("tenant_id", self.tenant_id)
        _text("model_id", self.model_id)
        if not self.scopes or not any(s.kind is ScopeKind.TENANT for s in self.scopes):
            raise ValueError("every request requires a tenant scope")
        values = (self.input_tokens, self.output_tokens, self.retry_number)
        if any(value < 0 for value in values):
            raise ValueError("usage values cannot be negative")
        costs = (
            self.estimated_cost,
            self.estimated_gpu_seconds,
            self.estimated_runtime_seconds,
            self.retry_accumulated_cost,
        )
        if any(value < 0 for value in costs):
            raise ValueError("estimated consumption cannot be negative")


@dataclass(frozen=True, slots=True)
class UsageEvidence:
    request_id: str
    tenant_id: str
    model_id: str
    provider_id: str
    scopes: tuple[Scope, ...]
    input_tokens: int
    output_tokens: int
    cost: Decimal
    gpu_seconds: Decimal
    runtime_seconds: Decimal
    admitted_at: datetime
    warnings: tuple[str, ...]


@dataclass(slots=True)
class _Consumption:
    requests: int = 0
    cost: Decimal = Decimal(0)
    gpu: Decimal = Decimal(0)
    runtime: Decimal = Decimal(0)
    active: int = 0


@dataclass(slots=True)
class _Circuit:
    failures: list[datetime] = field(default_factory=list)
    open_until: datetime | None = None


class UsageGovernor:
    """Fail-closed admission, accounting, warnings, and circuit breaking."""

    def __init__(
        self,
        registry: ModelProviderRegistry,
        limits: dict[Scope, UsageLimits],
        *,
        circuit_failure_threshold: int = 3,
        circuit_window: timedelta = timedelta(minutes=5),
        circuit_cooldown: timedelta = timedelta(minutes=1),
    ) -> None:
        if circuit_failure_threshold <= 0:
            raise ValueError("circuit_failure_threshold must be positive")
        self._registry = registry
        self._limits = dict(limits)
        self._daily: dict[tuple[Scope, str], _Consumption] = {}
        self._monthly: dict[tuple[Scope, str], _Consumption] = {}
        self._requests: set[str] = set()
        self._reconciled: set[str] = set()
        self._circuits: dict[str, _Circuit] = {}
        self._threshold = circuit_failure_threshold
        self._window = circuit_window
        self._cooldown = circuit_cooldown

    def admit(self, request: UsageRequest, now: datetime) -> UsageEvidence:
        if request.request_id in self._requests:
            raise GovernanceError("duplicate request_id")
        model = self._registry.model(request.model_id)
        provider = self._registry.provider(model.provider_id)
        if not model.enabled or not provider.enabled:
            raise GovernanceError("model or provider is disabled")
        circuit = self._circuits.setdefault(provider.provider_id, _Circuit())
        if circuit.open_until is not None:
            if now < circuit.open_until:
                raise GovernanceError("provider circuit is open")
            circuit.open_until = None
            circuit.failures.clear()
        if request.input_tokens + request.output_tokens > model.context_window:
            raise GovernanceError("model context window exceeded")
        if request.output_tokens > model.max_output_tokens:
            raise GovernanceError("model output token limit exceeded")

        checks: list[tuple[UsageLimits, _Consumption, _Consumption]] = []
        for scope in request.scopes:
            limit = self._limits.get(scope)
            if limit is None:
                raise GovernanceError(f"no configured limit for {scope.kind.value} scope")
            daily = self._daily.setdefault(
                (scope, now.date().isoformat()), _Consumption()
            )
            month = now.strftime("%Y-%m")
            monthly = self._monthly.setdefault((scope, month), _Consumption())
            self._check(limit, daily, monthly, request)
            checks.append((limit, daily, monthly))

        warnings: set[str] = set()
        for limit, daily, monthly in checks:
            daily.requests += 1
            daily.cost += request.estimated_cost
            daily.gpu += request.estimated_gpu_seconds
            daily.runtime += request.estimated_runtime_seconds
            daily.active += 1
            monthly.cost += request.estimated_cost
            if daily.cost >= limit.daily_cost * limit.warning_fraction:
                warnings.add("daily_cost_warning")
            if monthly.cost >= limit.monthly_cost * limit.warning_fraction:
                warnings.add("monthly_cost_warning")
        self._requests.add(request.request_id)
        return UsageEvidence(
            request.request_id,
            request.tenant_id,
            model.model_id,
            provider.provider_id,
            request.scopes,
            request.input_tokens,
            request.output_tokens,
            request.estimated_cost,
            request.estimated_gpu_seconds,
            request.estimated_runtime_seconds,
            now,
            tuple(sorted(warnings)),
        )

    @staticmethod
    def _check(
        limit: UsageLimits,
        daily: _Consumption,
        monthly: _Consumption,
        request: UsageRequest,
    ) -> None:
        if request.input_tokens > limit.max_input_tokens:
            raise GovernanceError("input token ceiling exceeded")
        if request.output_tokens > limit.max_output_tokens:
            raise GovernanceError("output token ceiling exceeded")
        if daily.requests + 1 > limit.max_requests_daily:
            raise GovernanceError("daily request quota exhausted")
        if daily.active + 1 > limit.max_concurrency:
            raise GovernanceError("concurrency limit exhausted")
        if daily.cost + request.estimated_cost > limit.daily_cost:
            raise GovernanceError("daily cost budget exhausted")
        if monthly.cost + request.estimated_cost > limit.monthly_cost:
            raise GovernanceError("monthly cost budget exhausted")
        if daily.gpu + request.estimated_gpu_seconds > limit.gpu_seconds_daily:
            raise GovernanceError("daily GPU budget exhausted")
        if daily.runtime + request.estimated_runtime_seconds > limit.runtime_seconds_daily:
            raise GovernanceError("daily runtime budget exhausted")
        if request.retry_number > limit.max_retries:
            raise GovernanceError("retry limit exceeded")
        if request.retry_accumulated_cost > limit.max_retry_cost:
            raise GovernanceError("retry cost ceiling exceeded")

    def reconcile_cost(self, evidence: UsageEvidence, actual_cost: Decimal) -> None:
        """Reconcile a conservative reservation downward to observed provider cost."""
        if actual_cost < 0:
            raise GovernanceError("actual cost cannot be negative")
        if actual_cost > evidence.cost:
            raise GovernanceError("actual provider cost exceeded reserved cost")
        if evidence.request_id in self._reconciled:
            raise GovernanceError("usage request cost is already reconciled")
        difference = evidence.cost - actual_cost
        for scope in evidence.scopes:
            daily_key = (scope, evidence.admitted_at.date().isoformat())
            monthly_key = (scope, evidence.admitted_at.strftime("%Y-%m"))
            daily = self._daily.get(daily_key)
            monthly = self._monthly.get(monthly_key)
            if daily is None or monthly is None:
                raise GovernanceError("usage reservation is unavailable")
            if daily.cost < difference or monthly.cost < difference:
                raise GovernanceError("usage accounting would become negative")
            daily.cost -= difference
            monthly.cost -= difference
        self._reconciled.add(evidence.request_id)

    def complete(self, evidence: UsageEvidence) -> None:
        for scope in evidence.scopes:
            key = (scope, evidence.admitted_at.date().isoformat())
            consumption = self._daily.get(key)
            if consumption is None or consumption.active <= 0:
                raise GovernanceError("request is not active")
            consumption.active -= 1

    def record_provider_failure(self, provider_id: str, now: datetime) -> None:
        self._registry.provider(provider_id)
        circuit = self._circuits.setdefault(provider_id, _Circuit())
        cutoff = now - self._window
        circuit.failures = [stamp for stamp in circuit.failures if stamp >= cutoff]
        circuit.failures.append(now)
        if len(circuit.failures) >= self._threshold:
            circuit.open_until = now + self._cooldown

    def record_provider_success(self, provider_id: str, now: datetime) -> None:
        self._registry.provider(provider_id)
        circuit = self._circuits.setdefault(provider_id, _Circuit())
        circuit.failures.clear()
        circuit.open_until = None

    def provider_health(self, provider_id: str, now: datetime) -> dict[str, object]:
        """Return non-authoritative operational health derived from circuit state."""
        provider = self._registry.provider(provider_id)
        circuit = self._circuits.setdefault(provider_id, _Circuit())
        cutoff = now - self._window
        circuit.failures = [stamp for stamp in circuit.failures if stamp >= cutoff]
        open_until = circuit.open_until
        is_open = open_until is not None and now < open_until
        open_until_iso = open_until.isoformat() if is_open and open_until is not None else None
        return {
            "provider_id": provider.provider_id,
            "enabled": provider.enabled,
            "circuit": "open" if is_open else "closed",
            "recent_failures": len(circuit.failures),
            "open_until": open_until_iso,
        }

    def usage_snapshot(self, scope: Scope, now: datetime) -> dict[str, object]:
        if scope not in self._limits:
            raise GovernanceError(f"no configured limit for {scope.kind.value} scope")
        daily = self._daily.get((scope, now.date().isoformat()), _Consumption())
        monthly = self._monthly.get((scope, now.strftime("%Y-%m")), _Consumption())
        return {
            "scope_kind": scope.kind.value,
            "scope_id": scope.scope_id,
            "daily_requests": daily.requests,
            "daily_active": daily.active,
            "daily_cost": str(daily.cost),
            "monthly_cost": str(monthly.cost),
            "daily_gpu_seconds": str(daily.gpu),
            "daily_runtime_seconds": str(daily.runtime),
        }
