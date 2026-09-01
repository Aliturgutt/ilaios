from __future__ import annotations

from typing import Any

import pytest

from src.video_automation.pexels_stock_transport import PexelsStockHttpTransport
from src.video_automation.stock_source_adapters import (
    StockProvider,
    StockSearchResult,
    StockSourceError,
)


def _search(transport: PexelsStockHttpTransport) -> StockSearchResult:
    return transport.search(
        provider=StockProvider.PEXELS,
        tenant_id="tenant-1",
        job_id="job-1",
        query="enterprise office",
        max_results=1,
    )


def test_pexels_transport_binds_license_provenance_and_rate_limit() -> None:
    def fetch_json(url: str, api_key: str) -> tuple[dict[str, Any], dict[str, str]]:
        assert url.startswith("https://api.pexels.com/v1/search?")
        assert api_key == "test-key"
        return (
            {
                "photos": [
                    {
                        "id": 42,
                        "url": "https://www.pexels.com/photo/example-42/",
                        "photographer": "Example Creator",
                        "width": 1920,
                        "height": 1080,
                        "src": {
                            "original": "https://images.pexels.com/photos/42/original.jpeg",
                            "medium": "https://images.pexels.com/photos/42/medium.jpeg",
                        },
                    }
                ]
            },
            {"x-ratelimit-remaining": "99", "x-ratelimit-reset": "2030-01-01T00:00:00Z"},
        )

    result = _search(PexelsStockHttpTransport("test-key", fetch_json=fetch_json))
    assert len(result.candidates) == 1
    candidate = result.candidates[0]
    assert candidate.provenance.provider is StockProvider.PEXELS
    assert candidate.provenance.asset_id == "42"
    assert candidate.provenance.creator == "Example Creator"
    assert candidate.provenance.license_name == "Pexels License"
    assert candidate.provenance.license_url == "https://www.pexels.com/license/"
    assert candidate.provenance.attribution_required is False
    assert result.rate_limit.remaining == 99


def test_pexels_transport_drops_candidate_without_required_provenance() -> None:
    def fetch_json(_url: str, _api_key: str) -> tuple[dict[str, Any], dict[str, str]]:
        return ({"photos": [{"id": 42, "url": "https://www.pexels.com/photo/42/", "src": {"original": "https://images.pexels.com/42.jpeg"}}]}, {})

    result = _search(PexelsStockHttpTransport("test-key", fetch_json=fetch_json))
    assert result.candidates == ()


def test_pexels_transport_fails_closed_on_zero_rate_limit_without_reset() -> None:
    def fetch_json(_url: str, _api_key: str) -> tuple[dict[str, Any], dict[str, str]]:
        return ({"photos": []}, {"x-ratelimit-remaining": "0"})

    with pytest.raises(StockSourceError, match="rate-limit reset"):
        _search(PexelsStockHttpTransport("test-key", fetch_json=fetch_json))


def test_pexels_transport_rejects_wrong_provider_and_blank_key() -> None:
    with pytest.raises(StockSourceError, match="API key"):
        PexelsStockHttpTransport(" ")

    transport = PexelsStockHttpTransport("test-key", fetch_json=lambda _url, _key: ({"photos": []}, {}))
    with pytest.raises(StockSourceError, match="only accepts pexels"):
        transport.search(
            provider=StockProvider.WIKIMEDIA,
            tenant_id="tenant-1",
            job_id="job-1",
            query="office",
            max_results=1,
        )
