"""Real NASA Images HTTP transport for the governed stock-source contract."""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from src.video_automation.stock_source_adapters import (
    RateLimitState,
    SourceProvenance,
    StockAssetCandidate,
    StockProvider,
    StockSearchRequest,
    StockSearchResult,
    StockSourceError,
)

_API_URL = "https://images-api.nasa.gov"
_LICENSE_URL = "https://www.nasa.gov/nasa-brand-center/images-and-media/"
_USER_AGENT = "ILAIOS-VideoFactory/1.0 (https://ilaios.com)"

JsonFetcher = Callable[[str], dict[str, Any]]


class NasaStockHttpTransport:
    """Execute NASA Images search and preserve source/licensing provenance."""

    def __init__(self, fetch_json: JsonFetcher | None = None) -> None:
        self._fetch_json = fetch_json or _fetch_json

    def search(
        self,
        *,
        provider: StockProvider,
        tenant_id: str,
        job_id: str,
        query: str,
        max_results: int,
    ) -> StockSearchResult:
        request = StockSearchRequest(
            tenant_id=tenant_id,
            job_id=job_id,
            query=query,
            provider=provider,
            max_results=max_results,
        )
        if provider is not StockProvider.NASA:
            raise StockSourceError("NASA transport only accepts nasa requests")

        params = urlencode({"q": query, "page_size": str(max_results)})
        payload = self._fetch_json(f"{_API_URL}/search?{params}")
        collection = payload.get("collection")
        if not isinstance(collection, dict):
            raise StockSourceError("NASA response collection must be an object")
        items = collection.get("items", [])
        if not isinstance(items, list):
            raise StockSourceError("NASA response items must be a list")

        retrieved_at = datetime.now(UTC).isoformat()
        candidates: list[StockAssetCandidate] = []
        for item in items:
            candidate = self._candidate_from_item(item, retrieved_at)
            if candidate is not None:
                candidates.append(candidate)
            if len(candidates) >= max_results:
                break

        return StockSearchResult(
            request=request,
            candidates=tuple(candidates),
            rate_limit=RateLimitState(remaining=None, reset_at_iso8601=None),
        )

    def _candidate_from_item(
        self, item: Any, retrieved_at: str
    ) -> StockAssetCandidate | None:
        if not isinstance(item, dict):
            raise StockSourceError("NASA item must be an object")
        data = item.get("data")
        if not isinstance(data, list) or not data or not isinstance(data[0], dict):
            return None
        metadata = data[0]

        nasa_id = metadata.get("nasa_id")
        media_type = metadata.get("media_type")
        if not isinstance(nasa_id, str) or not nasa_id.strip():
            return None
        if media_type not in {"image", "video", "audio"}:
            return None

        manifest = self._fetch_json(f"{_API_URL}/asset/{quote(nasa_id, safe='')}")
        media_url = _best_asset_url(manifest, media_type)
        if media_url is None:
            return None

        preview_url = _preview_url(item)
        creator = _creator(metadata)
        source_url = f"https://images.nasa.gov/details/{quote(nasa_id, safe='')}"

        return StockAssetCandidate(
            media_url=media_url,
            preview_url=preview_url,
            media_type=media_type,
            width=None,
            height=None,
            provenance=SourceProvenance(
                provider=StockProvider.NASA,
                source_url=source_url,
                asset_id=nasa_id,
                creator=creator,
                license_name="NASA Images and Media Usage Guidelines",
                license_url=_LICENSE_URL,
                attribution_required=True,
                retrieved_at_iso8601=retrieved_at,
            ),
        )


def _best_asset_url(manifest: dict[str, Any], media_type: str) -> str | None:
    collection = manifest.get("collection")
    if not isinstance(collection, dict):
        raise StockSourceError("NASA asset collection must be an object")
    items = collection.get("items", [])
    if not isinstance(items, list):
        raise StockSourceError("NASA asset items must be a list")

    allowed_suffixes = {
        "image": (".jpg", ".jpeg", ".png", ".tif", ".tiff"),
        "video": (".mp4", ".mov"),
        "audio": (".wav", ".mp3", ".m4a"),
    }[media_type]
    urls: list[str] = []
    for entry in items:
        if not isinstance(entry, dict):
            continue
        href = entry.get("href")
        if not isinstance(href, str) or not href.startswith("https://"):
            continue
        urls.append(href)
    for href in urls:
        lowered = href.casefold().split("?", 1)[0]
        if lowered.endswith(allowed_suffixes):
            return href
    return None


def _preview_url(item: dict[str, Any]) -> str | None:
    links = item.get("links", [])
    if not isinstance(links, list):
        return None
    for link in links:
        if not isinstance(link, dict):
            continue
        href = link.get("href")
        if isinstance(href, str) and href.startswith("https://"):
            return href
    return None


def _creator(metadata: dict[str, Any]) -> str:
    for key in ("photographer", "secondary_creator", "center"):
        value = metadata.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return "NASA"


def _fetch_json(url: str) -> dict[str, Any]:
    request = Request(url, headers={"User-Agent": _USER_AGENT, "Accept": "application/json"})
    try:
        with urlopen(request, timeout=15) as response:  # noqa: S310 - fixed HTTPS host
            payload = json.load(response)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise StockSourceError("NASA HTTP request failed closed") from exc
    if not isinstance(payload, dict):
        raise StockSourceError("NASA response must be a JSON object")
    return payload
