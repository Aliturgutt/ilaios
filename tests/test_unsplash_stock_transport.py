from __future__ import annotations

from typing import Any

import pytest

from src.video_automation.stock_source_adapters import (
    StockProvider,
    StockSearchResult,
    StockSourceError,
)
from src.video_automation.unsplash_stock_transport import UnsplashStockHttpTransport


def _search(transport: UnsplashStockHttpTransport) -> StockSearchResult:
    return transport.search(
        provider=StockProvider.UNSPLASH,
        tenant_id="tenant-1",
        job_id="job-1",
        query="architecture",
        max_results=1,
    )


def test_unsplash_transport_binds_attribution_provenance_and_rate_limit() -> None:
    def fetch_json(url: str, access_key: str) -> tuple[dict[str, Any], dict[str, str]]:
        assert url.startswith("https://api.unsplash.com/search/photos?")
        assert access_key == "test-key"
        return (
            {
                "results": [
                    {
                        "id": "abc123",
                        "width": 1600,
                        "height": 900,
                        "links": {"html": "https://unsplash.com/photos/abc123"},
                        "urls": {
                            "full": "https://images.unsplash.com/photo-abc123",
                            "small": "https://images.unsplash.com/photo-abc123-small",
                        },
                        "user": {"name": "Example Creator"},
                    }
                ]
            },
            {"x-ratelimit-remaining": "49", "x-ratelimit-reset": "2030-01-01T00:00:00Z"},
        )

    result = _search(UnsplashStockHttpTransport("test-key", fetch_json=fetch_json))
    assert len(result.candidates) == 1
    candidate = result.candidates[0]
    assert candidate.provenance.provider is StockProvider.UNSPLASH
    assert candidate.provenance.asset_id == "abc123"
    assert candidate.provenance.creator == "Example Creator"
    assert candidate.provenance.license_name == "Unsplash License"
    assert candidate.provenance.license_url == "https://unsplash.com/license"
    assert candidate.provenance.attribution_required is True
    assert result.rate_limit.remaining == 49


def test_unsplash_transport_drops_candidate_without_creator() -> None:
    def fetch_json(_url: str, _access_key: str) -> tuple[dict[str, Any], dict[str, str]]:
        return ({"results": [{"id": "abc", "links": {"html": "https://unsplash.com/photos/abc"}, "urls": {"full": "https://images.unsplash.com/abc"}, "user": {}}]}, {})

    result = _search(UnsplashStockHttpTransport("test-key", fetch_json=fetch_json))
    assert result.candidates == ()


def test_unsplash_transport_fails_closed_on_zero_rate_limit_without_reset() -> None:
    def fetch_json(_url: str, _access_key: str) -> tuple[dict[str, Any], dict[str, str]]:
        return ({"results": []}, {"x-ratelimit-remaining": "0"})

    with pytest.raises(StockSourceError, match="rate-limit reset"):
        _search(UnsplashStockHttpTransport("test-key", fetch_json=fetch_json))


def test_unsplash_transport_rejects_wrong_provider_and_blank_key() -> None:
    with pytest.raises(StockSourceError, match="access key"):
        UnsplashStockHttpTransport(" ")

    transport = UnsplashStockHttpTransport("test-key", fetch_json=lambda _url, _key: ({"results": []}, {}))
    with pytest.raises(StockSourceError, match="only accepts unsplash"):
        transport.search(
            provider=StockProvider.PIXABAY,
            tenant_id="tenant-1",
            job_id="job-1",
            query="office",
            max_results=1,
        )
