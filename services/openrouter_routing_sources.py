"""Read-only OpenRouter telemetry sources for canonical ILAIOS routing.

The sources in this module do not select a model and do not call inference
endpoints. They supply live, bounded catalog/pricing and account/gateway
telemetry to the existing :class:`services.routing_runtime.GovernedRoutingRuntime`.
Final selection therefore remains owned by ``services.ai_governance.route_model``.

Secrets are read from the environment at observation time and are never written
to snapshots, evidence, errors, or cache identities.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import time
import urllib.error
import urllib.request
from collections import deque
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation, ROUND_FLOOR
from pathlib import Path
from types import MappingProxyType
from typing import Protocol, cast

from services.ai_governance import GovernanceError, ModelRecord, ProviderRecord
from services.evidence import EvidenceStore
from services.provider_catalog import ProviderCatalogSnapshot
from services.provider_state import (
    ProviderHealthState,
    ProviderQuotaState,
    ProviderRuntimeSnapshot,
)
from services.routing_runtime import GovernedRoutingRuntime

_OPENROUTER_PROVIDER_ID = "openrouter"
_OPENROUTER_ADAPTER_ID = "openai-compatible"
_DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
_MILLION = Decimal(1_000_000)


class OpenRouterTelemetryError(GovernanceError):
    """Live OpenRouter telemetry is unavailable, malformed, or unsafe."""


@dataclass(frozen=True, slots=True)
class OpenRouterHTTPResponse:
    status_code: int
    payload: Mapping[str, object]
    latency_ms: int

    def __post_init__(self) -> None:
        if self.status_code < 100 or self.status_code > 599:
            raise ValueError("status_code must be a valid HTTP status")
        if self.latency_ms < 0:
            raise ValueError("latency_ms cannot be negative")


class OpenRouterReadOnlyTransport(Protocol):
    """Transport boundary limited to authenticated read-only JSON requests."""

    def get_json(
        self,
        url: str,
        *,
        api_key: str,
        timeout_seconds: float,
    ) -> OpenRouterHTTPResponse: ...


class UrllibOpenRouterReadOnlyTransport:
    """Minimal stdlib transport; it never logs credentials or response bodies."""

    def get_json(
        self,
        url: str,
        *,
        api_key: str,
        timeout_seconds: float,
    ) -> OpenRouterHTTPResponse:
        request = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Accept": "application/json",
            },
            method="GET",
        )
        started = time.monotonic()
        try:
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                status = int(response.status)
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            latency_ms = max(0, int((time.monotonic() - started) * 1000))
            return OpenRouterHTTPResponse(exc.code, {}, latency_ms)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise OpenRouterTelemetryError("OpenRouter telemetry transport failed") from exc
        latency_ms = max(0, int((time.monotonic() - started) * 1000))
        try:
            parsed = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise OpenRouterTelemetryError("OpenRouter telemetry returned malformed JSON") from exc
        if not isinstance(parsed, dict):
            raise OpenRouterTelemetryError("OpenRouter telemetry root must be an object")
        return OpenRouterHTTPResponse(status, cast(Mapping[str, object], parsed), latency_ms)


@dataclass(frozen=True, slots=True)
class _Probe:
    success: bool
    latency_ms: int | None


class OpenRouterProbeWindow:
    """Bounded observed gateway-health window shared by catalog and quota probes."""

    def __init__(self, *, max_observations: int = 20) -> None:
        if max_observations <= 0:
            raise ValueError("max_observations must be positive")
        self._samples: deque[_Probe] = deque(maxlen=max_observations)
        self._consecutive_failures = 0

    def record(self, *, success: bool, latency_ms: int | None) -> None:
        if latency_ms is not None and latency_ms < 0:
            raise ValueError("latency_ms cannot be negative")
        self._samples.append(_Probe(success, latency_ms))
        self._consecutive_failures = 0 if success else self._consecutive_failures + 1

    @property
    def success_rate(self) -> Decimal:
        if not self._samples:
            return Decimal(0)
        successes = sum(1 for sample in self._samples if sample.success)
        return Decimal(successes) / Decimal(len(self._samples))

    @property
    def p95_latency_ms(self) -> int:
        values = sorted(
            sample.latency_ms
            for sample in self._samples
            if sample.success and sample.latency_ms is not None
        )
        if not values:
            return 0
        index = max(0, math.ceil(len(values) * 0.95) - 1)
        return values[index]

    @property
    def consecutive_failures(self) -> int:
        return self._consecutive_failures


class OpenRouterCatalogSource:
    """Supply live user-filtered model/pricing facts without widening capability policy."""

    def __init__(
        self,
        model_capabilities: Mapping[str, frozenset[str]],
        *,
        api_key_env: str = "OPENROUTER_API_KEY",
        base_url: str = _DEFAULT_BASE_URL,
        timeout_seconds: float = 10.0,
        ttl_seconds: int = 60,
        transport: OpenRouterReadOnlyTransport | None = None,
        secret_reader: Callable[[str], str | None] = os.environ.get,
        probes: OpenRouterProbeWindow | None = None,
    ) -> None:
        if not model_capabilities:
            raise ValueError("at least one configured model capability mapping is required")
        normalized: dict[str, frozenset[str]] = {}
        for model_id, capabilities in model_capabilities.items():
            _text("model_id", model_id)
            if not capabilities or any(not item or item != item.strip() for item in capabilities):
                raise ValueError("configured model capabilities must be non-empty and trimmed")
            normalized[model_id] = frozenset(capabilities)
        _text("api_key_env", api_key_env)
        _text("base_url", base_url)
        if not base_url.startswith("https://"):
            raise ValueError("OpenRouter base_url must use HTTPS")
        if timeout_seconds <= 0 or ttl_seconds <= 0:
            raise ValueError("timeout and TTL must be positive")
        self._model_capabilities = MappingProxyType(normalized)
        self._api_key_env = api_key_env
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._ttl = timedelta(seconds=ttl_seconds)
        self._transport = transport or UrllibOpenRouterReadOnlyTransport()
        self._secret_reader = secret_reader
        self._probes = probes or OpenRouterProbeWindow()
        self._cached: ProviderCatalogSnapshot | None = None

    @property
    def probes(self) -> OpenRouterProbeWindow:
        return self._probes

    def observe_catalog(self, *, now: datetime) -> ProviderCatalogSnapshot:
        _aware("now", now)
        if self._cached is not None and self._cached.is_fresh(now, self._ttl):
            return self._cached
        secret = self._secret()
        try:
            response = self._transport.get_json(
                f"{self._base_url}/models/user",
                api_key=secret,
                timeout_seconds=self._timeout_seconds,
            )
        except Exception:
            self._probes.record(success=False, latency_ms=None)
            raise
        if response.status_code < 200 or response.status_code >= 300:
            self._probes.record(success=False, latency_ms=response.latency_ms)
            _raise_http("model catalog", response.status_code)
        self._probes.record(success=True, latency_ms=response.latency_ms)
        snapshot = self._parse_catalog(response.payload, now=now)
        self._cached = snapshot
        return snapshot

    def _parse_catalog(
        self,
        payload: Mapping[str, object],
        *,
        now: datetime,
    ) -> ProviderCatalogSnapshot:
        raw_data = payload.get("data")
        if not isinstance(raw_data, list):
            raise OpenRouterTelemetryError("OpenRouter model catalog requires a data list")
        configured = set(self._model_capabilities)
        seen: set[str] = set()
        records: list[ModelRecord] = []
        digest_rows: list[dict[str, object]] = []
        for raw in raw_data:
            if not isinstance(raw, dict):
                continue
            raw_id = raw.get("id")
            if not isinstance(raw_id, str) or raw_id not in configured:
                continue
            if raw_id in seen:
                raise OpenRouterTelemetryError("OpenRouter model catalog contains duplicate configured model")
            seen.add(raw_id)
            context_window = _positive_int(raw.get("context_length"), "context_length")
            top_provider = raw.get("top_provider")
            max_output = None
            if isinstance(top_provider, dict):
                candidate = top_provider.get("max_completion_tokens")
                if isinstance(candidate, int) and not isinstance(candidate, bool) and candidate > 0:
                    max_output = min(candidate, context_window)
            if max_output is None:
                max_output = min(4096, context_window)
            pricing = raw.get("pricing")
            if not isinstance(pricing, dict):
                raise OpenRouterTelemetryError("configured OpenRouter model lacks pricing evidence")
            prompt_per_token = _price(pricing.get("prompt"), "prompt")
            completion_per_token = _price(pricing.get("completion"), "completion")
            record = ModelRecord(
                raw_id,
                _OPENROUTER_PROVIDER_ID,
                self._model_capabilities[raw_id],
                context_window,
                max_output,
                input_cost_per_million=prompt_per_token * _MILLION,
                output_cost_per_million=completion_per_token * _MILLION,
            )
            records.append(record)
            digest_rows.append(
                {
                    "model_id": record.model_id,
                    "context_window": record.context_window,
                    "max_output_tokens": record.max_output_tokens,
                    "input_cost_per_million": str(record.input_cost_per_million),
                    "output_cost_per_million": str(record.output_cost_per_million),
                    "capabilities": sorted(record.capabilities),
                }
            )
        missing = configured - seen
        if missing:
            raise OpenRouterTelemetryError(
                "configured OpenRouter models are absent from the authenticated user catalog"
            )
        if not records:
            raise OpenRouterTelemetryError("no configured OpenRouter model is currently eligible")
        digest = hashlib.sha256(
            json.dumps(
                sorted(digest_rows, key=lambda item: str(item["model_id"])),
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        return ProviderCatalogSnapshot(
            f"openrouter:{digest}",
            now,
            (ProviderRecord(_OPENROUTER_PROVIDER_ID, _OPENROUTER_ADAPTER_ID),),
            tuple(sorted(records, key=lambda item: item.model_id)),
        )

    def _secret(self) -> str:
        secret = self._secret_reader(self._api_key_env) or ""
        if not secret.strip():
            raise OpenRouterTelemetryError("OpenRouter telemetry credential is unavailable")
        return secret.strip()


class OpenRouterRuntimeSource:
    """Supply live key quota plus observed OpenRouter gateway health evidence."""

    def __init__(
        self,
        catalog_source: OpenRouterCatalogSource,
        *,
        api_key_env: str = "OPENROUTER_API_KEY",
        base_url: str = _DEFAULT_BASE_URL,
        timeout_seconds: float = 10.0,
        transport: OpenRouterReadOnlyTransport | None = None,
        secret_reader: Callable[[str], str | None] = os.environ.get,
    ) -> None:
        _text("api_key_env", api_key_env)
        _text("base_url", base_url)
        if not base_url.startswith("https://"):
            raise ValueError("OpenRouter base_url must use HTTPS")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self._catalog_source = catalog_source
        self._api_key_env = api_key_env
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._transport = transport or UrllibOpenRouterReadOnlyTransport()
        self._secret_reader = secret_reader
        self._probes = catalog_source.probes

    def observe_runtime(self, *, now: datetime) -> ProviderRuntimeSnapshot:
        _aware("now", now)
        secret = self._secret_reader(self._api_key_env) or ""
        if not secret.strip():
            raise OpenRouterTelemetryError("OpenRouter telemetry credential is unavailable")
        try:
            response = self._transport.get_json(
                f"{self._base_url}/key",
                api_key=secret.strip(),
                timeout_seconds=self._timeout_seconds,
            )
        except Exception:
            self._probes.record(success=False, latency_ms=None)
            raise
        if response.status_code < 200 or response.status_code >= 300:
            self._probes.record(success=False, latency_ms=response.latency_ms)
            _raise_http("key quota", response.status_code)
        self._probes.record(success=True, latency_ms=response.latency_ms)
        raw_data = response.payload.get("data")
        if not isinstance(raw_data, dict):
            raise OpenRouterTelemetryError("OpenRouter key telemetry requires a data object")
        limit_remaining = _optional_decimal(raw_data.get("limit_remaining"), "limit_remaining")
        if limit_remaining is not None and limit_remaining < 0:
            raise OpenRouterTelemetryError("OpenRouter limit_remaining cannot be negative")

        catalog = self._catalog_source.observe_catalog(now=now)
        remaining_tokens = _conservative_remaining_tokens(catalog, limit_remaining)
        success_rate = self._probes.success_rate
        health = ProviderHealthState(
            _OPENROUTER_PROVIDER_ID,
            now,
            success_rate,
            self._probes.p95_latency_ms,
            consecutive_failures=self._probes.consecutive_failures,
            circuit_open=False,
        )
        quota = ProviderQuotaState(
            _OPENROUTER_PROVIDER_ID,
            now,
            remaining_requests=None,
            remaining_tokens=remaining_tokens,
            reset_at=None,
        )
        digest_material = {
            "provider_id": _OPENROUTER_PROVIDER_ID,
            "limit_remaining": None if limit_remaining is None else str(limit_remaining),
            "remaining_tokens": remaining_tokens,
            "success_rate": str(success_rate),
            "p95_latency_ms": health.p95_latency_ms,
        }
        digest = hashlib.sha256(
            json.dumps(digest_material, sort_keys=True, separators=(",", ":")).encode(
                "utf-8"
            )
        ).hexdigest()
        return ProviderRuntimeSnapshot(
            f"openrouter:{digest}",
            now,
            (health,),
            (quota,),
        )


def build_openrouter_governed_routing_runtime(
    *,
    evidence_root: Path,
    model_capabilities: Mapping[str, frozenset[str]],
    api_key_env: str = "OPENROUTER_API_KEY",
    base_url: str = _DEFAULT_BASE_URL,
    timeout_seconds: float = 10.0,
    catalog_ttl_seconds: int = 60,
    transport: OpenRouterReadOnlyTransport | None = None,
    secret_reader: Callable[[str], str | None] = os.environ.get,
) -> GovernedRoutingRuntime:
    """Compose live read-only OpenRouter telemetry into the existing router runtime."""

    probes = OpenRouterProbeWindow()
    catalog = OpenRouterCatalogSource(
        model_capabilities,
        api_key_env=api_key_env,
        base_url=base_url,
        timeout_seconds=timeout_seconds,
        ttl_seconds=catalog_ttl_seconds,
        transport=transport,
        secret_reader=secret_reader,
        probes=probes,
    )
    runtime = OpenRouterRuntimeSource(
        catalog,
        api_key_env=api_key_env,
        base_url=base_url,
        timeout_seconds=timeout_seconds,
        transport=transport,
        secret_reader=secret_reader,
    )
    return GovernedRoutingRuntime(catalog, runtime, EvidenceStore(evidence_root))


def _conservative_remaining_tokens(
    catalog: ProviderCatalogSnapshot,
    limit_remaining: Decimal | None,
) -> int | None:
    if limit_remaining is None:
        return None
    rates = [
        max(model.input_cost_per_million, model.output_cost_per_million) / _MILLION
        for model in catalog.models
    ]
    worst_per_token = max(rates, default=Decimal(0))
    if worst_per_token == 0:
        return None
    if limit_remaining <= 0:
        return 0
    token_budget = (limit_remaining / worst_per_token).to_integral_value(
        rounding=ROUND_FLOOR
    )
    if token_budget < 0:
        raise OpenRouterTelemetryError("derived OpenRouter token quota cannot be negative")
    return int(token_budget)


def _price(value: object, field: str) -> Decimal:
    parsed = _optional_decimal(value, field)
    if parsed is None:
        raise OpenRouterTelemetryError(f"OpenRouter {field} pricing is missing")
    if parsed < 0:
        raise OpenRouterTelemetryError(f"OpenRouter {field} pricing cannot be negative")
    return parsed


def _optional_decimal(value: object, field: str) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):
        raise OpenRouterTelemetryError(f"OpenRouter {field} must be numeric or null")
    try:
        parsed = Decimal(str(value))
    except InvalidOperation as exc:
        raise OpenRouterTelemetryError(f"OpenRouter {field} is not a decimal") from exc
    if not parsed.is_finite():
        raise OpenRouterTelemetryError(f"OpenRouter {field} must be finite")
    return parsed


def _positive_int(value: object, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise OpenRouterTelemetryError(f"OpenRouter {field} must be a positive integer")
    return value


def _raise_http(label: str, status_code: int) -> None:
    if status_code in {401, 403}:
        raise OpenRouterTelemetryError(f"OpenRouter {label} authentication failed")
    if status_code == 429:
        raise OpenRouterTelemetryError(f"OpenRouter {label} telemetry is rate limited")
    raise OpenRouterTelemetryError(
        f"OpenRouter {label} telemetry failed with HTTP {status_code}"
    )


def _text(name: str, value: str) -> None:
    if not value or value != value.strip():
        raise ValueError(f"{name} must be non-empty and trimmed")


def _aware(name: str, value: datetime) -> None:
    if value.tzinfo is None:
        raise ValueError(f"{name} must be timezone-aware")
