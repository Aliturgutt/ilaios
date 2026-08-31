from __future__ import annotations

from typing import Any

import pytest

from src.video_automation.internet_archive_stock_transport import (
    InternetArchiveStockHttpTransport,
)
from src.video_automation.stock_source_adapters import StockProvider, StockSourceError


def _search_payload() -> dict[str, Any]:
    return {"response": {"docs": [{"identifier": "example-item"}]}}


def _metadata_payload() -> dict[str, Any]:
    return {
        "metadata": {
            "creator": "Example Creator",
            "license": "CC BY 4.0",
            "licenseurl": "https://creativecommons.org/licenses/by/4.0/",
        },
        "files": [
            {
                "name": "example.mp4",
                "source": "original",
            }
        ],
    }


def test_internet_archive_transport_binds_real_provider_contract() -> None:
    seen: list[str] = []

    def fetch_json(url: str) -> dict[str, Any]:
        seen.append(url)
        return _search_payload() if "advancedsearch.php" in url else _metadata_payload()

    result = InternetArchiveStockHttpTransport(fetch_json).search(
        provider=StockProvider.INTERNET_ARCHIVE,
        tenant_id="tenant-1",
        job_id="job-1",
        query="documentary earth",
        max_results=2,
    )

    assert len(result.candidates) == 1
    candidate = result.candidates[0]
    assert candidate.media_type == "video"
    assert candidate.provenance.provider is StockProvider.INTERNET_ARCHIVE
    assert candidate.provenance.creator == "Example Creator"
    assert candidate.provenance.license_name == "CC BY 4.0"
    assert candidate.provenance.attribution_required is True
    assert candidate.provenance.source_url == "https://archive.org/details/example-item"
    assert candidate.media_url == (
        "https://archive.org/download/example-item/example.mp4"
    )
    assert any("advancedsearch.php?" in url for url in seen)
    assert any("/metadata/example-item" in url for url in seen)


def test_internet_archive_transport_fails_closed_without_license() -> None:
    payload = _metadata_payload()
    payload["metadata"].pop("licenseurl")

    def fetch_json(url: str) -> dict[str, Any]:
        return _search_payload() if "advancedsearch.php" in url else payload

    result = InternetArchiveStockHttpTransport(fetch_json).search(
        provider=StockProvider.INTERNET_ARCHIVE,
        tenant_id="tenant-1",
        job_id="job-1",
        query="earth",
        max_results=1,
    )
    assert result.candidates == ()


def test_internet_archive_transport_rejects_cross_provider_request() -> None:
    with pytest.raises(StockSourceError, match="only accepts internet_archive"):
        InternetArchiveStockHttpTransport(lambda _: _search_payload()).search(
            provider=StockProvider.NASA,
            tenant_id="tenant-1",
            job_id="job-1",
            query="earth",
            max_results=1,
        )
