from __future__ import annotations

from typing import Any

import pytest

from src.video_automation.nasa_stock_transport import NasaStockHttpTransport
from src.video_automation.stock_source_adapters import StockProvider, StockSourceError


def _search_payload() -> dict[str, Any]:
    return {
        "collection": {
            "items": [
                {
                    "data": [
                        {
                            "nasa_id": "GSFC_20171208_Archive_e001465",
                            "media_type": "image",
                            "photographer": "NASA Photographer",
                        }
                    ],
                    "links": [
                        {"href": "https://images-assets.nasa.gov/image/preview.jpg"}
                    ],
                }
            ]
        }
    }


def _asset_payload() -> dict[str, Any]:
    return {
        "collection": {
            "items": [
                {
                    "href": "https://images-assets.nasa.gov/image/GSFC_20171208_Archive_e001465/GSFC_20171208_Archive_e001465~orig.jpg"
                }
            ]
        }
    }


def test_nasa_transport_binds_real_provider_contract() -> None:
    seen: list[str] = []

    def fetch_json(url: str) -> dict[str, Any]:
        seen.append(url)
        return _search_payload() if "/search?" in url else _asset_payload()

    result = NasaStockHttpTransport(fetch_json).search(
        provider=StockProvider.NASA,
        tenant_id="tenant-1",
        job_id="job-1",
        query="earth",
        max_results=2,
    )

    assert len(result.candidates) == 1
    candidate = result.candidates[0]
    assert candidate.media_type == "image"
    assert candidate.provenance.provider is StockProvider.NASA
    assert candidate.provenance.creator == "NASA Photographer"
    assert candidate.provenance.license_name == "NASA Images and Media Usage Guidelines"
    assert candidate.provenance.attribution_required is True
    assert candidate.provenance.license_url == (
        "https://www.nasa.gov/nasa-brand-center/images-and-media/"
    )
    assert candidate.provenance.source_url.startswith("https://images.nasa.gov/details/")
    assert any(url.startswith("https://images-api.nasa.gov/search?") for url in seen)
    assert any("/asset/GSFC_20171208_Archive_e001465" in url for url in seen)


def test_nasa_transport_fails_closed_without_usable_asset() -> None:
    def fetch_json(url: str) -> dict[str, Any]:
        if "/search?" in url:
            return _search_payload()
        return {"collection": {"items": [{"href": "http://example.com/file.jpg"}]}}

    result = NasaStockHttpTransport(fetch_json).search(
        provider=StockProvider.NASA,
        tenant_id="tenant-1",
        job_id="job-1",
        query="earth",
        max_results=1,
    )
    assert result.candidates == ()


def test_nasa_transport_rejects_cross_provider_request() -> None:
    with pytest.raises(StockSourceError, match="only accepts nasa"):
        NasaStockHttpTransport(lambda _: _search_payload()).search(
            provider=StockProvider.WIKIMEDIA,
            tenant_id="tenant-1",
            job_id="job-1",
            query="earth",
            max_results=1,
        )
