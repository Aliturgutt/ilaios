"""Immutable provider/model catalog snapshots for ILAIOS routing intelligence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from types import MappingProxyType
from typing import Mapping

from services.ai_governance import ModelProviderRegistry, ModelRecord, ProviderRecord

_ZERO = Decimal(0)
_ONE = Decimal(1)


def _text(name: str, value: str) -> None:
    if not value or value != value.strip():
        raise ValueError(f"{name} must be non-empty and trimmed")


def _aware(name: str, value: datetime) -> None:
    if value.tzinfo is None:
        raise ValueError(f"{name} must be timezone-aware")


@dataclass(frozen=True, slots=True)
class ModelQualityRecord:
    model_id: str
    score: Decimal

    def __post_init__(self) -> None:
        _text("model_id", self.model_id)
        if self.score < _ZERO or self.score > _ONE:
            raise ValueError("quality score must be in [0, 1]")


@dataclass(frozen=True, slots=True)
class ProviderCatalogSnapshot:
    """Versioned catalog evidence; network retrieval belongs in replaceable adapters."""

    catalog_version: str
    observed_at: datetime
    providers: tuple[ProviderRecord, ...]
    models: tuple[ModelRecord, ...]
    quality: tuple[ModelQualityRecord, ...] = ()

    def __post_init__(self) -> None:
        _text("catalog_version", self.catalog_version)
        _aware("observed_at", self.observed_at)
        provider_ids = [provider.provider_id for provider in self.providers]
        model_ids = [model.model_id for model in self.models]
        quality_ids = [item.model_id for item in self.quality]
        if len(provider_ids) != len(set(provider_ids)):
            raise ValueError("provider catalog contains duplicate providers")
        if len(model_ids) != len(set(model_ids)):
            raise ValueError("provider catalog contains duplicate models")
        if len(quality_ids) != len(set(quality_ids)):
            raise ValueError("provider catalog contains duplicate quality records")
        known_providers = set(provider_ids)
        if any(model.provider_id not in known_providers for model in self.models):
            raise ValueError("catalog model references an unknown provider")
        known_models = set(model_ids)
        if any(model_id not in known_models for model_id in quality_ids):
            raise ValueError("quality record references an unknown model")

    def is_fresh(self, now: datetime, max_age: timedelta) -> bool:
        _aware("now", now)
        if max_age <= timedelta(0):
            raise ValueError("max_age must be positive")
        age = now - self.observed_at
        return timedelta(0) <= age <= max_age

    def provider_map(self) -> Mapping[str, ProviderRecord]:
        return MappingProxyType({provider.provider_id: provider for provider in self.providers})

    def quality_map(self) -> Mapping[str, Decimal]:
        return MappingProxyType({item.model_id: item.score for item in self.quality})

    def build_registry(self) -> ModelProviderRegistry:
        registry = ModelProviderRegistry()
        for provider in sorted(self.providers, key=lambda item: item.provider_id):
            registry.register_provider(provider)
        for model in sorted(self.models, key=lambda item: item.model_id):
            registry.register_model(model)
        return registry
