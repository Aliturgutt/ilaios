from __future__ import annotations

import hashlib
import json
from pathlib import Path

from src.video_automation.nasa_stock_transport import NasaStockHttpTransport
from src.video_automation.stock_source_adapters import StockProvider


def main() -> int:
    result = NasaStockHttpTransport().search(
        provider=StockProvider.NASA,
        tenant_id="video-live-e2e",
        job_id="nasa-stock-live-e2e",
        query="earth",
        max_results=1,
    )
    if not result.candidates:
        raise SystemExit("NASA live E2E failed closed: no governed candidate returned")

    candidate = result.candidates[0]
    provenance = candidate.provenance
    if provenance.provider is not StockProvider.NASA:
        raise SystemExit("NASA live E2E failed closed: provider provenance mismatch")
    if not provenance.source_url.startswith("https://images.nasa.gov/details/"):
        raise SystemExit("NASA live E2E failed closed: invalid source URL")
    if provenance.license_url != "https://www.nasa.gov/nasa-brand-center/images-and-media/":
        raise SystemExit("NASA live E2E failed closed: license metadata mismatch")
    if not candidate.media_url.startswith("https://"):
        raise SystemExit("NASA live E2E failed closed: non-HTTPS media URL")

    receipt = {
        "status": "PASS",
        "provider": provenance.provider.value,
        "asset_id": provenance.asset_id,
        "source_url": provenance.source_url,
        "media_url_sha256": hashlib.sha256(candidate.media_url.encode("utf-8")).hexdigest(),
        "license_name": provenance.license_name,
        "license_url": provenance.license_url,
        "attribution_required": provenance.attribution_required,
        "retrieved_at_iso8601": provenance.retrieved_at_iso8601,
    }
    output = Path("artifacts/video-stock-nasa-live-e2e/receipt.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
