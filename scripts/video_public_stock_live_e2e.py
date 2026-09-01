from __future__ import annotations

import hashlib
import json
from pathlib import Path

from src.video_automation.internet_archive_stock_transport import (
    InternetArchiveStockHttpTransport,
)
from src.video_automation.stock_source_adapters import StockProvider
from src.video_automation.wikimedia_stock_transport import WikimediaStockHttpTransport

_OUTPUT = Path("artifacts/video-stock-public-live-e2e/receipt.json")


def _write_receipt(receipt: dict[str, object]) -> None:
    _OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    _OUTPUT.write_text(
        json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(receipt, sort_keys=True))


def _receipt(provider: StockProvider, candidate: object) -> dict[str, object]:
    provenance = candidate.provenance  # type: ignore[attr-defined]
    media_url = candidate.media_url  # type: ignore[attr-defined]
    if provenance.provider is not provider:
        raise ValueError(f"{provider.value} failed closed: provider mismatch")
    if not isinstance(media_url, str) or not media_url.startswith("https://"):
        raise ValueError(f"{provider.value} failed closed: non-HTTPS media URL")
    if not provenance.source_url.startswith("https://"):
        raise ValueError(f"{provider.value} failed closed: non-HTTPS source URL")
    if not provenance.license_name:
        raise ValueError(f"{provider.value} failed closed: missing license name")
    if provenance.attribution_required and not provenance.creator:
        raise ValueError(
            f"{provider.value} failed closed: attribution required without creator"
        )
    return {
        "provider": provenance.provider.value,
        "asset_id": provenance.asset_id,
        "source_url": provenance.source_url,
        "media_url_sha256": hashlib.sha256(media_url.encode("utf-8")).hexdigest(),
        "license_name": provenance.license_name,
        "license_url": provenance.license_url,
        "creator": provenance.creator,
        "attribution_required": provenance.attribution_required,
        "retrieved_at_iso8601": provenance.retrieved_at_iso8601,
    }


def main() -> int:
    provider = StockProvider.WIKIMEDIA
    try:
        wikimedia = WikimediaStockHttpTransport().search(
            provider=provider,
            tenant_id="video-live-e2e",
            job_id="wikimedia-stock-live-e2e",
            query="earth",
            max_results=3,
        )
        if not wikimedia.candidates:
            raise ValueError("no governed candidate returned")
        wikimedia_receipt = _receipt(provider, wikimedia.candidates[0])

        provider = StockProvider.INTERNET_ARCHIVE
        archive = InternetArchiveStockHttpTransport().search(
            provider=provider,
            tenant_id="video-live-e2e",
            job_id="internet-archive-stock-live-e2e",
            query="licenseurl:*",
            max_results=5,
        )
        if not archive.candidates:
            raise ValueError("no governed candidate returned")
        archive_receipt = _receipt(provider, archive.candidates[0])
    except Exception as exc:
        _write_receipt(
            {
                "status": "FAIL",
                "provider": provider.value,
                "error_type": type(exc).__name__,
                "error": str(exc),
            }
        )
        return 1

    _write_receipt(
        {
            "status": "PASS",
            "providers": [wikimedia_receipt, archive_receipt],
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
