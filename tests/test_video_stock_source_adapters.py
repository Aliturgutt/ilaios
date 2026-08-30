from __future__ import annotations

import pytest

from src.video_automation.stock_source_adapters import (
    RateLimitState,
    SourceProvenance,
    StockAssetCandidate,
    StockProvider,
    StockSearchRequest,
    StockSearchResult,
    StockSourceError,
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
    request = StockSearchRequest(
        tenant_id="tenant-1",
        job_id="job-1",
        query="city skyline",
        provider=StockProvider.PEXELS,
        max_results=10,
    )
    with pytest.raises(StockSourceError, match="provider must match"):
        StockSearchResult(
            request=request,
            candidates=(_candidate(StockProvider.PIXABAY),),
            rate_limit=RateLimitState(remaining=9, reset_at_iso8601=None),
        )


def test_valid_result_preserves_provider_provenance_and_rate_limit() -> None:
    request = StockSearchRequest(
        tenant_id="tenant-1",
        job_id="job-1",
        query="city skyline",
        provider=StockProvider.PEXELS,
        max_results=10,
    )
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
