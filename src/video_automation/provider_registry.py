"""Deterministic provider registry for ILAIOS Video Automation."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from types import MappingProxyType

from .providers import Provider, ProviderCapabilities


def _validate_text(name: str, value: str) -> None:
    if not value or not value.strip():
        raise ValueError(f"{name} must not be empty")
    if value != value.strip():
        raise ValueError(f"{name} must not contain surrounding whitespace")


@dataclass(frozen=True, slots=True)
class ProviderDescriptor:
    """Immutable registry-facing provider description."""

    provider_name: str
    capabilities: ProviderCapabilities

    def __post_init__(self) -> None:
        _validate_text("provider_name", self.provider_name)
        if self.provider_name != self.capabilities.provider_name:
            raise ValueError(
                "provider_name must match capabilities.provider_name"
            )


class ProviderRegistry:
    """Deterministic registry for provider implementations and capabilities."""

    def __init__(self, providers: Iterable[Provider] = ()) -> None:
        self._providers: dict[str, Provider] = {}
        for provider in providers:
            self.register(provider)

    def register(self, provider: Provider) -> None:
        """Register one provider by its canonical provider name."""

        name = provider.capabilities.provider_name
        _validate_text("provider_name", name)

        if name in self._providers:
            raise ValueError(f"provider already registered: {name}")

        self._providers[name] = provider

    def unregister(self, provider_name: str) -> Provider:
        """Remove and return one registered provider."""

        _validate_text("provider_name", provider_name)

        try:
            return self._providers.pop(provider_name)
        except KeyError as exc:
            raise KeyError(f"provider not registered: {provider_name}") from exc

    def get(self, provider_name: str) -> Provider:
        """Return a registered provider."""

        _validate_text("provider_name", provider_name)

        try:
            return self._providers[provider_name]
        except KeyError as exc:
            raise KeyError(f"provider not registered: {provider_name}") from exc

    def contains(self, provider_name: str) -> bool:
        """Return whether a provider name is registered."""

        _validate_text("provider_name", provider_name)
        return provider_name in self._providers

    def list_provider_names(self) -> tuple[str, ...]:
        """Return provider names in deterministic sorted order."""

        return tuple(sorted(self._providers))

    def list_capabilities(self) -> tuple[ProviderCapabilities, ...]:
        """Return capabilities in deterministic provider-name order."""

        return tuple(
            self._providers[name].capabilities
            for name in self.list_provider_names()
        )

    def descriptors(self) -> tuple[ProviderDescriptor, ...]:
        """Return immutable registry descriptors in deterministic order."""

        return tuple(
            ProviderDescriptor(
                provider_name=name,
                capabilities=self._providers[name].capabilities,
            )
            for name in self.list_provider_names()
        )

    def providers_supporting(
        self,
        operation: str,
        *,
        include_paid: bool = True,
    ) -> tuple[Provider, ...]:
        """Return providers supporting an operation in deterministic order."""

        _validate_text("operation", operation)

        matches: list[Provider] = []
        for name in self.list_provider_names():
            provider = self._providers[name]
            capabilities = provider.capabilities

            if not capabilities.supports(operation):
                continue
            if not include_paid and capabilities.is_paid:
                continue

            matches.append(provider)

        return tuple(matches)

    def capability_map(self) -> Mapping[str, ProviderCapabilities]:
        """Return an immutable provider-name to capability mapping."""

        ordered = {
            name: self._providers[name].capabilities
            for name in self.list_provider_names()
        }
        return MappingProxyType(ordered)

    def __len__(self) -> int:
        return len(self._providers)
