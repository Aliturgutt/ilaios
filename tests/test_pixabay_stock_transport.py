from __future__ import annotations

import pytest

from src.video_automation.pixabay_stock_transport import PixabayStockHttpTransport
from src.video_automation.stock_source_adapters import StockProvider, StockSourceError


def _search(transport: PixabayStockHttpTransport):
    return transport.search(
        provider=StockProvider.PIXABAY,
        tenant_id="tenant-1",
        job_id="job-1",
        query="city skyline",
        max_results=1,
    )


def test_pixabay_transport_binds_license_provenance_and_rate_limit() -> None:
    def fetch_json(url: str):
        assert url.startswith("https://pixabay.com/api/?")
        assert "key=test-key" in url
        return (
            {
                "hits": [
                    {
                        "id": 7,
                        "pageURL": "https://pixabay.com/photos/example-7/",
                        "user": "Example Creator",
                        "largeImageURL": "https://cdn.pixabay.com/photo/7_1280.jpg",
                        "webformatURL": "https://cdn.pixabay.com/photo/7_640.jpg",
                        "imageWidth": 1920,
                        "imageHeight": 1080,
                    }
                ]
            },
            {"x-ratelimit-remaining": "50", "x-ratelimit-reset": "2030-01-01T00:00:00Z"},
        )

    result = _search(PixabayStockHttpTransport("test-key", fetch_json=fetch_json))
    assert len(result.candidates) == 1
    candidate = result.candidates[0]
    assert candidate.provenance.provider is StockProvider.PIXABAY
    assert candidate.provenance.asset_id == "7"
    assert candidate.provenance.creator == "Example Creator"
    assert candidate.provenance.license_name == "Pixabay Content License"
    assert candidate.provenance.license_url == "https://pixabay.com/service/license-summary/"
    assert candidate.provenance.attribution_required is False
    assert result.rate_limit.remaining == 50


def test_pixabay_transport_drops_candidate_without_creator() -> None:
    def fetch_json(_url: str):
        return ({"hits": [{"id": 7, "pageURL": "https://pixabay.com/photos/7/", "largeImageURL": "https://cdn.pixabay.com/7.jpg"}]}, {})

    result = _search(PixabayStockHttpTransport("test-key", fetch_json=fetch_json))
    assert result.candidates == ()


def test_pixabay_transport_fails_closed_on_zero_rate_limit_without_reset() -> None:
    def fetch_json(_url: str):
        return ({"hits": []}, {"x-ratelimit-remaining": "0"})

    with pytest.raises(StockSourceError, match="rate-limit reset"):
        _search(PixabayStockHttpTransport("test-key", fetch_json=fetch_json))


def test_pixabay_transport_rejects_wrong_provider_and_blank_key() -> None:
    with pytest.raises(StockSourceError, match="API key"):
        PixabayStockHttpTransport(" ")

    transport = PixabayStockHttpTransport("test-key", fetch_json=lambda _url: ({"hits": []}, {}))
    with pytest.raises(StockSourceError, match="only accepts pixabay"):
        transport.search(
            provider=StockProvider.PEXELS,
            tenant_id="tenant-1",
            job_id="job-1",
            query="office",
            max_results=1,
        )
