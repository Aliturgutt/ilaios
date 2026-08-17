"""Dynamic OpenRouter video capability catalog for governed ILAIOS routing.

This module discovers capability/availability/pricing evidence. It deliberately
DOES NOT select providers and therefore does not create a second ILAIOS routing
authority. Canonical RouteDecision remains upstream of provider dispatch.
"""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from enum import Enum
from types import MappingProxyType

from .openrouter_video_provider import (
    OpenRouterTransport,
    UrllibOpenRouterTransport,
)

_DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"


class OpenRouterCatalogError(ValueError):
    """Raised when live managed-video catalog evidence is unusable."""


class OpenRouterCatalogHealth(str, Enum):
    CONNECTED = "CONNECTED"
    AUTH_FAILED = "AUTH_FAILED"
    CATALOG_UNAVAILABLE = "CATALOG_UNAVAILABLE"
    CATALOG_INVALID = "CATALOG_INVALID"
    RATE_LIMITED = "RATE_LIMITED"
    TEMPORARILY_UNAVAILABLE = "TEMPORARILY_UNAVAILABLE"


class ManagedVideoFamily(str, Enum):
    SEEDANCE = "SEEDANCE"
    KLING = "KLING"
    HAILUO = "HAILUO"
    WAN = "WAN"


@dataclass(frozen=True, slots=True)
class OpenRouterVideoModel:
    model_id: str
    canonical_slug: str
    name: str
    generate_audio: bool
    supported_aspect_ratios: tuple[str, ...]
    supported_durations: tuple[int, ...]
    supported_frame_images: tuple[str, ...]
    supported_resolutions: tuple[str, ...]
    supported_sizes: tuple[str, ...]
    allowed_passthrough_parameters: tuple[str, ...]
    pricing_skus: Mapping[str, str]
    family: ManagedVideoFamily | None

    def __post_init__(self) -> None:
        for field_name, value in (
            ("model_id", self.model_id),
            ("canonical_slug", self.canonical_slug),
            ("name", self.name),
        ):
            _text(field_name, value)
        object.__setattr__(
            self,
            "pricing_skus",
            MappingProxyType(dict(sorted(self.pricing_skus.items()))),
        )

    @property
    def has_valid_pricing(self) -> bool:
        if not self.pricing_skus:
            return False
        for sku, raw_price in self.pricing_skus.items():
            if not sku.strip() or not raw_price.strip():
                return False
            try:
                value = Decimal(raw_price)
            except InvalidOperation:
                return False
            if not value.is_finite() or value < 0:
                return False
        return True

    def resolve_supported_duration(self, preferred_seconds: float) -> int:
        """Resolve directorial timing intent against this live model capability.

        This is capability resolution only, not routing. If OpenRouter publishes
        explicit durations, the closest supported value wins and equal-distance
        ties choose the shorter clip to avoid avoidable provider spend. If the
        catalog publishes no duration restriction, a positive whole-second value
        nearest to the directorial preference is returned.
        """

        if preferred_seconds <= 0:
            raise OpenRouterCatalogError("preferred_seconds must be positive")
        if self.supported_durations:
            return min(
                self.supported_durations,
                key=lambda value: (abs(float(value) - preferred_seconds), value),
            )
        return max(1, int(round(preferred_seconds)))

    def supports_frame_role(self, role: str) -> bool:
        """Report whether live catalog evidence permits a first/last frame role."""

        _text("frame role", role)
        normalized = role.strip().lower().replace("-", "_")
        published = {
            item.strip().lower().replace("-", "_")
            for item in self.supported_frame_images
        }
        return normalized in published


@dataclass(frozen=True, slots=True)
class OpenRouterCatalogSnapshot:
    observed_at_epoch_s: float
    catalog_digest: str
    models: tuple[OpenRouterVideoModel, ...]

    def by_id(self) -> Mapping[str, OpenRouterVideoModel]:
        return MappingProxyType({model.model_id: model for model in self.models})


@dataclass(frozen=True, slots=True)
class OpenRouterCatalogObservation:
    health: OpenRouterCatalogHealth
    snapshot: OpenRouterCatalogSnapshot | None
    last_good_snapshot: OpenRouterCatalogSnapshot | None
    detail: str


class OpenRouterVideoCatalogClient:
    """Bounded authenticated video-model discovery with TTL and LKG retention."""

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = _DEFAULT_BASE_URL,
        timeout_seconds: float = 30.0,
        ttl_seconds: float = 300.0,
        max_paid_staleness_seconds: float = 1800.0,
        transport: OpenRouterTransport | None = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        _text("api_key", api_key)
        _text("base_url", base_url)
        if timeout_seconds <= 0:
            raise OpenRouterCatalogError("timeout_seconds must be positive")
        if ttl_seconds <= 0:
            raise OpenRouterCatalogError("ttl_seconds must be positive")
        if max_paid_staleness_seconds < ttl_seconds:
            raise OpenRouterCatalogError(
                "max_paid_staleness_seconds must be >= ttl_seconds"
            )
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._ttl_seconds = ttl_seconds
        self._max_paid_staleness_seconds = max_paid_staleness_seconds
        self._transport = transport or UrllibOpenRouterTransport()
        self._clock = clock
        self._last_good: OpenRouterCatalogSnapshot | None = None
        self._last_observation: OpenRouterCatalogObservation | None = None

    @property
    def last_good_snapshot(self) -> OpenRouterCatalogSnapshot | None:
        return self._last_good

    def refresh(self) -> OpenRouterCatalogObservation:
        now = self._clock()
        try:
            response = self._transport.get_json(
                f"{self._base_url}/videos/models",
                headers={"Authorization": f"Bearer {self._api_key}"},
                timeout_seconds=self._timeout_seconds,
            )
        except Exception as exc:  # noqa: BLE001
            observation = OpenRouterCatalogObservation(
                OpenRouterCatalogHealth.CATALOG_UNAVAILABLE,
                None,
                self._last_good,
                f"catalog transport failure: {exc.__class__.__name__}",
            )
            self._last_observation = observation
            return observation

        if response.status_code in {401, 403}:
            return self._record_failure(
                OpenRouterCatalogHealth.AUTH_FAILED,
                f"catalog authentication failed: HTTP {response.status_code}",
            )
        if response.status_code == 429:
            return self._record_failure(
                OpenRouterCatalogHealth.RATE_LIMITED,
                "catalog rate limited: HTTP 429",
            )
        if response.status_code >= 500:
            return self._record_failure(
                OpenRouterCatalogHealth.TEMPORARILY_UNAVAILABLE,
                f"catalog temporarily unavailable: HTTP {response.status_code}",
            )
        if not 200 <= response.status_code < 300:
            return self._record_failure(
                OpenRouterCatalogHealth.CATALOG_UNAVAILABLE,
                f"catalog unavailable: HTTP {response.status_code}",
            )

        try:
            snapshot = _parse_snapshot(response.payload, observed_at=now)
        except OpenRouterCatalogError as exc:
            return self._record_failure(
                OpenRouterCatalogHealth.CATALOG_INVALID,
                str(exc),
            )
        self._last_good = snapshot
        observation = OpenRouterCatalogObservation(
            OpenRouterCatalogHealth.CONNECTED,
            snapshot,
            snapshot,
            "authenticated catalog validated",
        )
        self._last_observation = observation
        return observation

    def observe(self) -> OpenRouterCatalogObservation:
        """Use bounded TTL caching; refresh only when current evidence is old."""

        now = self._clock()
        if self._last_good is not None:
            age = now - self._last_good.observed_at_epoch_s
            if 0 <= age <= self._ttl_seconds:
                observation = OpenRouterCatalogObservation(
                    OpenRouterCatalogHealth.CONNECTED,
                    self._last_good,
                    self._last_good,
                    "fresh cached catalog",
                )
                self._last_observation = observation
                return observation
        return self.refresh()

    def paid_eligible_models(self) -> tuple[OpenRouterVideoModel, ...]:
        """Return candidate capability facts only; does not choose a route."""

        observation = self.observe()
        snapshot = observation.snapshot or observation.last_good_snapshot
        if snapshot is None:
            raise OpenRouterCatalogError(
                f"paid dispatch blocked: {observation.health.value}"
            )
        age = self._clock() - snapshot.observed_at_epoch_s
        if age < 0 or age > self._max_paid_staleness_seconds:
            raise OpenRouterCatalogError("paid dispatch blocked: catalog pricing is stale")
        if observation.health in {
            OpenRouterCatalogHealth.AUTH_FAILED,
            OpenRouterCatalogHealth.CATALOG_INVALID,
        }:
            raise OpenRouterCatalogError(
                f"paid dispatch blocked: {observation.health.value}"
            )
        eligible = tuple(
            model
            for model in snapshot.models
            if model.family is not None and model.has_valid_pricing
        )
        if not eligible:
            raise OpenRouterCatalogError(
                "paid dispatch blocked: no governed candidate has valid pricing"
            )
        return eligible

    def _record_failure(
        self,
        health: OpenRouterCatalogHealth,
        detail: str,
    ) -> OpenRouterCatalogObservation:
        observation = OpenRouterCatalogObservation(
            health,
            None,
            self._last_good,
            detail,
        )
        self._last_observation = observation
        return observation


def _parse_snapshot(
    payload: Mapping[str, object],
    *,
    observed_at: float,
) -> OpenRouterCatalogSnapshot:
    data = payload.get("data")
    if not isinstance(data, Sequence) or isinstance(data, (str, bytes)):
        raise OpenRouterCatalogError("catalog schema requires data list")
    models: list[OpenRouterVideoModel] = []
    seen: set[str] = set()
    for raw in data:
        if not isinstance(raw, Mapping):
            raise OpenRouterCatalogError("catalog model entry must be an object")
        model = _parse_model(raw)
        if model.model_id in seen:
            raise OpenRouterCatalogError(
                f"catalog contains duplicate model id: {model.model_id}"
            )
        seen.add(model.model_id)
        models.append(model)
    if not models:
        raise OpenRouterCatalogError("catalog must contain at least one video model")
    models.sort(key=lambda item: item.model_id)
    canonical = [_model_material(model) for model in models]
    digest = hashlib.sha256(
        json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return OpenRouterCatalogSnapshot(observed_at, digest, tuple(models))


def _parse_model(raw: Mapping[object, object]) -> OpenRouterVideoModel:
    model_id = _mapping_string(raw, "id")
    canonical_slug = _mapping_string(raw, "canonical_slug")
    name = _mapping_string(raw, "name")
    generate_audio_raw = raw.get("generate_audio")
    if generate_audio_raw is None:
        # A null capability is not affirmative evidence that audio generation is
        # supported. Normalize it conservatively to False while still rejecting
        # malformed non-null values.
        generate_audio = False
    elif isinstance(generate_audio_raw, bool):
        generate_audio = generate_audio_raw
    else:
        raise OpenRouterCatalogError("generate_audio must be boolean or null")
    pricing_raw = raw.get("pricing_skus")
    if pricing_raw is None:
        pricing: dict[str, str] = {}
    elif isinstance(pricing_raw, Mapping):
        pricing = {}
        for key, value in pricing_raw.items():
            if not isinstance(key, str) or not isinstance(value, str):
                raise OpenRouterCatalogError("pricing_skus must map strings to strings")
            pricing[key] = value
    else:
        raise OpenRouterCatalogError("pricing_skus must be an object or null")
    return OpenRouterVideoModel(
        model_id=model_id,
        canonical_slug=canonical_slug,
        name=name,
        generate_audio=generate_audio,
        supported_aspect_ratios=_string_tuple(raw, "supported_aspect_ratios"),
        supported_durations=_int_tuple(raw, "supported_durations"),
        supported_frame_images=_string_tuple(raw, "supported_frame_images"),
        supported_resolutions=_string_tuple(raw, "supported_resolutions"),
        supported_sizes=_string_tuple(raw, "supported_sizes"),
        allowed_passthrough_parameters=_string_tuple(
            raw, "allowed_passthrough_parameters"
        ),
        pricing_skus=pricing,
        family=_managed_family(model_id),
    )


def _managed_family(model_id: str) -> ManagedVideoFamily | None:
    prefixes = (
        ("bytedance/seedance-", ManagedVideoFamily.SEEDANCE),
        ("kwaivgi/kling-", ManagedVideoFamily.KLING),
        ("minimax/hailuo-", ManagedVideoFamily.HAILUO),
        ("alibaba/wan-", ManagedVideoFamily.WAN),
    )
    for prefix, family in prefixes:
        if model_id.startswith(prefix):
            return family
    return None


def _mapping_string(raw: Mapping[object, object], key: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value.strip():
        raise OpenRouterCatalogError(f"catalog model {key} must be non-empty string")
    return value


def _string_tuple(raw: Mapping[object, object], key: str) -> tuple[str, ...]:
    value = raw.get(key)
    if value is None:
        return ()
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise OpenRouterCatalogError(f"catalog model {key} must be list or null")
    output: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise OpenRouterCatalogError(f"catalog model {key} entries must be strings")
        output.append(item)
    return tuple(output)


def _int_tuple(raw: Mapping[object, object], key: str) -> tuple[int, ...]:
    value = raw.get(key)
    if value is None:
        return ()
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise OpenRouterCatalogError(f"catalog model {key} must be list or null")
    output: list[int] = []
    for item in value:
        if isinstance(item, bool) or not isinstance(item, int) or item <= 0:
            raise OpenRouterCatalogError(
                f"catalog model {key} entries must be positive integers"
            )
        output.append(item)
    return tuple(output)


def _model_material(model: OpenRouterVideoModel) -> dict[str, object]:
    return {
        "id": model.model_id,
        "canonical_slug": model.canonical_slug,
        "name": model.name,
        "generate_audio": model.generate_audio,
        "supported_aspect_ratios": model.supported_aspect_ratios,
        "supported_durations": model.supported_durations,
        "supported_frame_images": model.supported_frame_images,
        "supported_resolutions": model.supported_resolutions,
        "supported_sizes": model.supported_sizes,
        "allowed_passthrough_parameters": model.allowed_passthrough_parameters,
        "pricing_skus": dict(model.pricing_skus),
        "family": None if model.family is None else model.family.value,
    }


def _text(name: str, value: str) -> None:
    if not value or not value.strip():
        raise OpenRouterCatalogError(f"{name} must not be blank")
