"""Deterministic provider selection engine for ILAIOS Video Automation."""

from __future__ import annotations

from dataclasses import dataclass

from .configuration import VideoAutomationPolicy
from .provider_registry import ProviderRegistry
from .providers import Provider


def _validate_text(name: str, value: str) -> None:
    if not value or not value.strip():
        raise ValueError(f"{name} must not be empty")
    if value != value.strip():
        raise ValueError(f"{name} must not contain surrounding whitespace")


@dataclass(frozen=True, slots=True)
class ProviderSelectionRequest:
    """Provider-neutral selection request."""

    operation: str
    preferred_provider_name: str | None = None
    allow_fallback: bool = True

    def __post_init__(self) -> None:
        _validate_text("operation", self.operation)
        if self.preferred_provider_name is not None:
            _validate_text(
                "preferred_provider_name",
                self.preferred_provider_name,
            )


@dataclass(frozen=True, slots=True)
class ProviderSelectionResult:
    """Deterministic provider selection outcome."""

    provider: Provider
    reason: str
    used_fallback: bool

    def __post_init__(self) -> None:
        _validate_text("reason", self.reason)


class ProviderSelectionError(RuntimeError):
    """Raised when no provider can satisfy a selection request."""


class ProviderSelectionEngine:
    """Select providers deterministically from registry and policy."""

    def __init__(
        self,
        *,
        registry: ProviderRegistry,
        policy: VideoAutomationPolicy,
    ) -> None:
        self._registry = registry
        self._policy = policy

    def select(
        self,
        request: ProviderSelectionRequest,
    ) -> ProviderSelectionResult:
        """Select exactly one provider for an operation."""

        preferred = request.preferred_provider_name

        if preferred is not None:
            preferred_result = self._try_preferred(request, preferred)
            if preferred_result is not None:
                return preferred_result

            if self._policy.provider.require_explicit_provider:
                raise ProviderSelectionError(
                    f"preferred provider is unavailable or disallowed: {preferred}"
                )

            if not request.allow_fallback:
                raise ProviderSelectionError(
                    f"preferred provider could not satisfy request: {preferred}"
                )

        elif self._policy.provider.require_explicit_provider:
            raise ProviderSelectionError(
                "provider policy requires explicit provider selection"
            )

        candidates = self._eligible_candidates(request.operation)
        if not candidates:
            raise ProviderSelectionError(
                f"no eligible provider supports operation: {request.operation}"
            )

        provider = candidates[0]
        return ProviderSelectionResult(
            provider=provider,
            reason="selected first eligible provider in deterministic name order",
            used_fallback=preferred is not None,
        )

    def _try_preferred(
        self,
        request: ProviderSelectionRequest,
        provider_name: str,
    ) -> ProviderSelectionResult | None:
        if not self._registry.contains(provider_name):
            return None

        provider = self._registry.get(provider_name)
        capabilities = provider.capabilities

        if not capabilities.supports(request.operation):
            return None

        if not self._policy.can_use_provider(
            provider_name,
            is_paid=capabilities.is_paid,
        ):
            return None

        return ProviderSelectionResult(
            provider=provider,
            reason="preferred provider satisfied operation and policy",
            used_fallback=False,
        )

    def _eligible_candidates(self, operation: str) -> tuple[Provider, ...]:
        candidates = self._registry.providers_supporting(
            operation,
            include_paid=True,
        )

        eligible: list[Provider] = []
        for provider in candidates:
            capabilities = provider.capabilities
            if self._policy.can_use_provider(
                capabilities.provider_name,
                is_paid=capabilities.is_paid,
            ):
                eligible.append(provider)

        return tuple(eligible)
