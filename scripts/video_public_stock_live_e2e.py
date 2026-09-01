from __future__ import annotations

import hashlib
import json
from pathlib import Path

from src.video_automation.internet_archive_stock_transport import (
    InternetArchiveStockHttpTransport,
)
from src.video_automation.stock_source_adapters import StockProvider
from src.video_automation.wikimedia_stock_transport import WikimediaStockHttpTransport


def _receipt(provider: StockProvider, candidate: object) -> dict[str, object]:
    provenance = candidate.provenance  # type: ignore[attr-defined]
    media_url = candidate.media_url  # type: ignore[attr-defined]
    if provenance.provider is not provider:
        raise SystemExit(f"{provider.value} live E2E failed closed: provider mismatch")
    if not isinstance(media_url, str) or not media_url.startswith("https://"):
        raise SystemExit(f"{provider.value} live E2E failed closed: non-HTTPS media URL")
    if not provenance.source_url.startswith("https://"):
        raise SystemExit(f"{provider.value} live E2E failed closed: non-HTTPS source URL")
    if not provenance.license_name:
        raise SystemExit(f"{provider.value} live E2E failed closed: missing license name")
    if provenance.attribution_required and not provenance.creator:
        raise SystemExit(
            f"{provider.value} live E2E failed closed: attribution required without creator"
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
    wikimedia = WikimediaStockHttpTransport().search(
        provider=StockProvider.WIKIMEDIA,
        tenant_id="video-live-e2e",
        job_id="wikimedia-stock-live-e2e",
        query="earth",
        max_results=3,
    )
    if not wikimedia.candidates:
        raise SystemExit("Wikimedia live E2E failed closed: no governed candidate returned")

    archive = InternetArchiveStockHttpTransport().search(
        provider=StockProvider.INTERNET_ARCHIVE,
        tenant_id="video-live-e2e",
        job_id="internet-archive-stock-live-e2e",
        query="licenseurl:*",
        max_results=5,
    )
    if not archive.candidates:
        raise SystemExit(
            "Internet Archive live E2E failed closed: no governed candidate returned"
        )

    receipt = {
        "status": "PASS",
        "providers": [
            _receipt(StockProvider.WIKIMEDIA, wikimedia.candidates[0]),
            _receipt(StockProvider.INTERNET_ARCHIVE, archive.candidates[0]),
        ],
    }
    output = Path("artifacts/video-stock-public-live-e2e/receipt.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
