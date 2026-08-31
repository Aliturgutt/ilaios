from __future__ import annotations

from typing import Any

import pytest

from src.video_automation.stock_source_adapters import StockProvider, StockSourceError
from src.video_automation.wikimedia_stock_transport import WikimediaStockHttpTransport


def _payload() -> dict[str, Any]:
    return {
        "query": {
            "pages": [
                {
                    "title": "File:Example.jpg",
                    "imageinfo": [
                        {
                            "url": "https://upload.wikimedia.org/example.jpg",
                            "descriptionurl": "https://commons.wikimedia.org/wiki/File:Example.jpg",
                            "mime": "image/jpeg",
                            "width": 1920,
                            "height": 1080,
                            "extmetadata": {
                                "Artist": {"value": "<b>Example Creator</b>"},
                                "LicenseShortName": {"value": "CC BY-SA 4.0"},
                                "LicenseUrl": {
                                    "value": "https://creativecommons.org/licenses/by-sa/4.0/"
                                },
                            },
                        }
                    ],
                }
            ]
        }
    }


def test_wikimedia_transport_binds_real_provider_contract() -> None:
    seen: list[str] = []

    def fetch_json(url: str) -> dict[str, Any]:
        seen.append(url)
        return _payload()

    result = WikimediaStockHttpTransport(fetch_json).search(
        provider=StockProvider.WIKIMEDIA,
        tenant_id="tenant-1",
        job_id="job-1",
        query="satellite earth",
        max_results=3,
    )

    assert len(result.candidates) == 1
    candidate = result.candidates[0]
    assert candidate.media_type == "image"
    assert candidate.provenance.provider is StockProvider.WIKIMEDIA
    assert candidate.provenance.creator == "Example Creator"
    assert candidate.provenance.license_name == "CC BY-SA 4.0"
    assert candidate.provenance.attribution_required is True
    assert seen and seen[0].startswith("https://commons.wikimedia.org/w/api.php?")


def test_wikimedia_transport_fails_closed_without_license() -> None:
    payload = _payload()
    metadata = payload["query"]["pages"][0]["imageinfo"][0]["extmetadata"]
    metadata.pop("LicenseShortName")

    result = WikimediaStockHttpTransport(lambda _: payload).search(
        provider=StockProvider.WIKIMEDIA,
        tenant_id="tenant-1",
        job_id="job-1",
        query="earth",
        max_results=1,
    )
    assert result.candidates == ()


def test_wikimedia_transport_rejects_cross_provider_request() -> None:
    with pytest.raises(StockSourceError, match="only accepts wikimedia"):
        WikimediaStockHttpTransport(lambda _: _payload()).search(
            provider=StockProvider.NASA,
            tenant_id="tenant-1",
            job_id="job-1",
            query="earth",
            max_results=1,
        )
