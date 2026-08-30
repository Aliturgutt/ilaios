from __future__ import annotations

from dataclasses import dataclass

import pytest

from src.video_automation.stock_source_adapters import (
    InternetArchiveStockSourceAdapter,
    NasaStockSourceAdapter,
    PexelsStockSourceAdapter,
    PixabayStockSourceAdapter,
    RateLimitState,
    SourceProvenance,
    StockAssetCandidate,
    StockProvider,
    StockSearchRequest,
    StockSearchResult,
    StockSourceError,
    UnsplashStockSourceAdapter,
    WikimediaStockSourceAdapter,
)


def _provenance(provider: StockProvider = StockProvider.PEXELS) -> SourceProvenance:
    return SourceProvenance(
        provider=provider,
        source_url="https://example.test/source/1",
        asset_id="asset-1",
        creator="creator",
        license_name="provider-license",
        license_url="https://example.test/license",
        attribution_required=True,
        retrieved_at_iso8601="2026-08-29T20:00:00Z",
    )


def _candidate(provider: StockProvider = StockProvider.PEXELS) -> StockAssetCandidate:
    return StockAssetCandidate(
        media_url="https://example.test/media.mp4",
        preview_url="https://example.test/preview.jpg",
        media_type="video",
        width=1920,
        height=1080,
        provenance=_provenance(provider),
    )


def _request(provider: StockProvider) -> StockSearchRequest:
    return StockSearchRequest(
        tenant_id="tenant-1",
        job_id="job-1",
        query="city skyline",
        provider=provider,
        max_results=10,
    )


@dataclass
class _FakeTransport:
    request_override: StockSearchRequest | None = None

    def search(
        self,
        *,
        provider: StockProvider,
        tenant_id: str,
        job_id: str,
        query: str,
        max_results: int,
    ) -> StockSearchResult:
        request = self.request_override or StockSearchRequest(
            tenant_id=tenant_id,
            job_id=job_id,
            query=query,
            provider=provider,
            max_results=max_results,
        )
        return StockSearchResult(
            request=request,
            candidates=(_candidate(provider),),
            rate_limit=RateLimitState(remaining=9, reset_at_iso8601=None),
        )


def test_request_bounds_result_count() -> None:
    with pytest.raises(StockSourceError, match="between 1 and 50"):
        StockSearchRequest(
            tenant_id="tenant-1",
            job_id="job-1",
            query="city skyline",
            provider=StockProvider.PEXELS,
            max_results=51,
        )


def test_provenance_requires_license_and_https_source() -> None:
    with pytest.raises(StockSourceError, match="source_url must use https"):
        SourceProvenance(
            provider=StockProvider.WIKIMEDIA,
            source_url="http://example.test/source/1",
            asset_id="asset-1",
            creator=None,
            license_name="public-domain",
            license_url=None,
            attribution_required=False,
            retrieved_at_iso8601="2026-08-29T20:00:00Z",
        )

    with pytest.raises(StockSourceError, match="license_name must not be blank"):
        SourceProvenance(
            provider=StockProvider.WIKIMEDIA,
            source_url="https://example.test/source/1",
            asset_id="asset-1",
            creator=None,
            license_name="",
            license_url=None,
            attribution_required=False,
            retrieved_at_iso8601="2026-08-29T20:00:00Z",
        )


def test_attribution_required_fails_closed_without_creator() -> None:
    with pytest.raises(StockSourceError, match="creator is required"):
        SourceProvenance(
            provider=StockProvider.UNSPLASH,
            source_url="https://example.test/source/1",
            asset_id="asset-1",
            creator=None,
            license_name="provider-license",
            license_url="https://example.test/license",
            attribution_required=True,
            retrieved_at_iso8601="2026-08-29T20:00:00Z",
        )


def test_rate_limit_exhaustion_requires_reset_time() -> None:
    with pytest.raises(StockSourceError, match="reset time is required"):
        RateLimitState(remaining=0, reset_at_iso8601=None)


def test_result_rejects_cross_provider_provenance() -> None:
    request = _request(StockProvider.PEXELS)
    with pytest.raises(StockSourceError, match="provider must match"):
        StockSearchResult(
            request=request,
            candidates=(_candidate(StockProvider.PIXABAY),),
            rate_limit=RateLimitState(remaining=9, reset_at_iso8601=None),
        )


def test_valid_result_preserves_provider_provenance_and_rate_limit() -> None:
    request = _request(StockProvider.PEXELS)
    result = StockSearchResult(
        request=request,
        candidates=(_candidate(),),
        rate_limit=RateLimitState(
            remaining=9,
            reset_at_iso8601="2026-08-29T21:00:00Z",
        ),
    )
    assert result.candidates[0].provenance.provider is StockProvider.PEXELS
    assert result.candidates[0].provenance.license_name == "provider-license"
    assert result.rate_limit.remaining == 9


@pytest.mark.parametrize(
    ("provider", "adapter_type"),
    [
        (StockProvider.PEXELS, PexelsStockSourceAdapter),
        (StockProvider.PIXABAY, PixabayStockSourceAdapter),
        (StockProvider.UNSPLASH, UnsplashStockSourceAdapter),
        (StockProvider.WIKIMEDIA, WikimediaStockSourceAdapter),
        (StockProvider.NASA, NasaStockSourceAdapter),
        (StockProvider.INTERNET_ARCHIVE, InternetArchiveStockSourceAdapter),
    ],
)
def test_concrete_provider_adapters_preserve_governed_provenance(
    provider: StockProvider,
    adapter_type: type[PexelsStockSourceAdapter],
) -> None:
    request = _request(provider)
    result = adapter_type(_FakeTransport()).search(request)
    assert result.request == request
    assert result.candidates[0].provenance.provider is provider
    assert result.candidates[0].provenance.license_name == "provider-license"


def test_provider_adapter_rejects_cross_provider_request() -> None:
    adapter = PexelsStockSourceAdapter(_FakeTransport())
    with pytest.raises(StockSourceError, match="cannot execute pixabay request"):
        adapter.search(_request(StockProvider.PIXABAY))


def test_provider_adapter_rejects_transport_request_substitution() -> None:
    original = _request(StockProvider.PEXELS)
    substituted = StockSearchRequest(
        tenant_id="other-tenant",
        job_id="job-1",
        query="city skyline",
        provider=StockProvider.PEXELS,
        max_results=10,
    )
    adapter = PexelsStockSourceAdapter(_FakeTransport(request_override=substituted))
    with pytest.raises(StockSourceError, match="must match adapter request"):
        adapter.search(original)
