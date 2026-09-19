"""Bounded health and quota evidence for ILAIOS provider routing."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from types import MappingProxyType
from typing import Mapping

_ZERO = Decimal(0)
_ONE = Decimal(1)


def _text(name: str, value: str) -> None:
    if not value or value != value.strip():
        raise ValueError(f"{name} must be non-empty and trimmed")


def _aware(name: str, value: datetime) -> None:
    if value.tzinfo is None:
        raise ValueError(f"{name} must be timezone-aware")


@dataclass(frozen=True, slots=True)
class ProviderHealthState:
    provider_id: str
    observed_at: datetime
    success_rate: Decimal
    p95_latency_ms: int
    consecutive_failures: int = 0
    circuit_open: bool = False

    def __post_init__(self) -> None:
        _text("provider_id", self.provider_id)
        _aware("observed_at", self.observed_at)
        if self.success_rate < _ZERO or self.success_rate > _ONE:
            raise ValueError("success_rate must be in [0, 1]")
        if self.p95_latency_ms < 0 or self.consecutive_failures < 0:
            raise ValueError("health counters cannot be negative")

    def is_fresh(self, now: datetime, max_age: timedelta) -> bool:
        _aware("now", now)
        age = now - self.observed_at
        return timedelta(0) <= age <= max_age


@dataclass(frozen=True, slots=True)
class ProviderQuotaState:
    provider_id: str
    observed_at: datetime
    remaining_requests: int | None = None
    remaining_tokens: int | None = None
    reset_at: datetime | None = None

    def __post_init__(self) -> None:
        _text("provider_id", self.provider_id)
        _aware("observed_at", self.observed_at)
        if self.remaining_requests is not None and self.remaining_requests < 0:
            raise ValueError("remaining_requests cannot be negative")
        if self.remaining_tokens is not None and self.remaining_tokens < 0:
            raise ValueError("remaining_tokens cannot be negative")
        if self.reset_at is not None:
            _aware("reset_at", self.reset_at)

    def is_fresh(self, now: datetime, max_age: timedelta) -> bool:
        _aware("now", now)
        age = now - self.observed_at
        return timedelta(0) <= age <= max_age


@dataclass(frozen=True, slots=True)
class ProviderRuntimeSnapshot:
    state_version: str
    observed_at: datetime
    health: tuple[ProviderHealthState, ...]
    quota: tuple[ProviderQuotaState, ...]

    def __post_init__(self) -> None:
        _text("state_version", self.state_version)
        _aware("observed_at", self.observed_at)
        health_ids = [item.provider_id for item in self.health]
        quota_ids = [item.provider_id for item in self.quota]
        if len(health_ids) != len(set(health_ids)):
            raise ValueError("runtime snapshot contains duplicate health state")
        if len(quota_ids) != len(set(quota_ids)):
            raise ValueError("runtime snapshot contains duplicate quota state")

    def is_fresh(self, now: datetime, max_age: timedelta) -> bool:
        _aware("now", now)
        if max_age <= timedelta(0):
            raise ValueError("max_age must be positive")
        age = now - self.observed_at
        return timedelta(0) <= age <= max_age

    def health_map(self) -> Mapping[str, ProviderHealthState]:
        return MappingProxyType({item.provider_id: item for item in self.health})

    def quota_map(self) -> Mapping[str, ProviderQuotaState]:
        return MappingProxyType({item.provider_id: item for item in self.quota})

    def health_for(self, provider_id: str) -> ProviderHealthState | None:
        _text("provider_id", provider_id)
        return self.health_map().get(provider_id)

    def quota_for(self, provider_id: str) -> ProviderQuotaState | None:
        _text("provider_id", provider_id)
        return self.quota_map().get(provider_id)
