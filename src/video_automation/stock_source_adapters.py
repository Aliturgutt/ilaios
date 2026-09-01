"""Provider-neutral stock-source adapter contracts for ILAIOS Video Factory.

This module defines fail-closed request/result and governance boundaries for stock
media providers. Concrete provider adapters are deliberately transport-injected:
they do not resolve credentials, bypass governed routing, or select fallback
providers. Runtime/provider E2E evidence is required before VERIFIED maturity.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol


class StockSourceError(ValueError):
    """Raised when stock-source data violates the governed contract."""


class StockProvider(str, Enum):
    PEXELS = "pexels"
    PIXABAY = "pixabay"
    UNSPLASH = "unsplash"
    WIKIMEDIA = "wikimedia"
    NASA = "nasa"
    INTERNET_ARCHIVE = "internet_archive"


@dataclass(frozen=True, slots=True)
class StockSearchRequest:
    tenant_id: str
    job_id: str
    query: str
    provider: StockProvider
    max_results: int = 10

    def __post_init__(self) -> None:
        _require_non_blank("tenant_id", self.tenant_id)
        _require_non_blank("job_id", self.job_id)
        _require_non_blank("query", self.query)
        if self.max_results < 1 or self.max_results > 50:
            raise StockSourceError("max_results must be between 1 and 50")


@dataclass(frozen=True, slots=True)
class SourceProvenance:
    provider: StockProvider
    source_url: str
    asset_id: str
    creator: str | None
    license_name: str
    license_url: str | None
    attribution_required: bool
    retrieved_at_iso8601: str

    def __post_init__(self) -> None:
        _require_https_url("source_url", self.source_url)
        _require_non_blank("asset_id", self.asset_id)
        _require_non_blank("license_name", self.license_name)
        _require_non_blank("retrieved_at_iso8601", self.retrieved_at_iso8601)
        if self.license_url is not None:
            _require_https_url("license_url", self.license_url)
        if self.attribution_required and not self.creator:
            raise StockSourceError(
                "creator is required when attribution_required is true"
            )


@dataclass(frozen=True, slots=True)
class StockAssetCandidate:
    media_url: str
    preview_url: str | None
    media_type: str
    width: int | None
    height: int | None
    provenance: SourceProvenance

    def __post_init__(self) -> None:
        _require_https_url("media_url", self.media_url)
        if self.preview_url is not None:
            _require_https_url("preview_url", self.preview_url)
        if self.media_type not in {"image", "video", "audio"}:
            raise StockSourceError("media_type must be image, video, or audio")
        if self.width is not None and self.width <= 0:
            raise StockSourceError("width must be positive when present")
        if self.height is not None and self.height <= 0:
            raise StockSourceError("height must be positive when present")


@dataclass(frozen=True, slots=True)
class RateLimitState:
    remaining: int | None
    reset_at_iso8601: str | None

    def __post_init__(self) -> None:
        if self.remaining is not None and self.remaining < 0:
            raise StockSourceError("rate-limit remaining must not be negative")
        if self.remaining == 0 and not self.reset_at_iso8601:
            raise StockSourceError(
                "rate-limit reset time is required when remaining is zero"
            )


@dataclass(frozen=True, slots=True)
class StockSearchResult:
    request: StockSearchRequest
    candidates: tuple[StockAssetCandidate, ...]
    rate_limit: RateLimitState

    def __post_init__(self) -> None:
        if len(self.candidates) > self.request.max_results:
            raise StockSourceError("candidate count exceeds request max_results")
        for candidate in self.candidates:
            if candidate.provenance.provider is not self.request.provider:
                raise StockSourceError(
                    "candidate provenance provider must match request provider"
                )


class GovernedStockSourceAdapter(Protocol):
    """Boundary implemented only by adapters invoked through governed routing."""

    provider: StockProvider

    def search(self, request: StockSearchRequest) -> StockSearchResult:
        """Return validated candidates or fail closed; never silently fallback."""
        ...


class StockProviderTransport(Protocol):
    """Credential/network boundary supplied by the existing governed runtime."""

    def search(
        self,
        *,
        provider: StockProvider,
        tenant_id: str,
        job_id: str,
        query: str,
        max_results: int,
    ) -> StockSearchResult:
        """Execute one provider request and return a fully attributed result."""
        ...


class _BoundProviderAdapter:
    """Fail-closed provider binding shared by concrete stock adapters."""

    provider: StockProvider

    def __init__(self, transport: StockProviderTransport) -> None:
        self._transport = transport

    def search(self, request: StockSearchRequest) -> StockSearchResult:
        if request.provider is not self.provider:
            raise StockSourceError(
                f"{self.provider.value} adapter cannot execute "
                f"{request.provider.value} request"
            )
        result = self._transport.search(
            provider=self.provider,
            tenant_id=request.tenant_id,
            job_id=request.job_id,
            query=request.query,
            max_results=request.max_results,
        )
        if result.request != request:
            raise StockSourceError("transport result request must match adapter request")
        if result.request.provider is not self.provider:
            raise StockSourceError("transport result provider must match adapter provider")
        return result


class PexelsStockSourceAdapter(_BoundProviderAdapter):
    provider = StockProvider.PEXELS


class PixabayStockSourceAdapter(_BoundProviderAdapter):
    provider = StockProvider.PIXABAY


class UnsplashStockSourceAdapter(_BoundProviderAdapter):
    provider = StockProvider.UNSPLASH


class WikimediaStockSourceAdapter(_BoundProviderAdapter):
    provider = StockProvider.WIKIMEDIA


class NasaStockSourceAdapter(_BoundProviderAdapter):
    provider = StockProvider.NASA


class InternetArchiveStockSourceAdapter(_BoundProviderAdapter):
    provider = StockProvider.INTERNET_ARCHIVE


def _require_non_blank(name: str, value: str) -> None:
    if not value or not value.strip():
        raise StockSourceError(f"{name} must not be blank")
    if value != value.strip():
        raise StockSourceError(f"{name} must not contain surrounding whitespace")


def _require_https_url(name: str, value: str) -> None:
    _require_non_blank(name, value)
    if not value.startswith("https://"):
        raise StockSourceError(f"{name} must use https")
