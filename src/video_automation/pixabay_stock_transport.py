"""Real Pixabay HTTP transport for the governed stock-source contract."""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
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

_SEARCH_URL = "https://pixabay.com/api/"
_LICENSE_URL = "https://pixabay.com/service/license-summary/"
_USER_AGENT = "ILAIOS-VideoFactory/1.0 (https://ilaios.com)"

JsonFetcher = Callable[[str], tuple[dict[str, Any], dict[str, str]]]


class PixabayStockHttpTransport:
    """Execute Pixabay image search with explicit credential and provenance binding."""

    def __init__(self, api_key: str, fetch_json: JsonFetcher | None = None) -> None:
        if not api_key or not api_key.strip() or api_key != api_key.strip():
            raise StockSourceError("Pixabay API key must be non-blank and trimmed")
        self._api_key = api_key
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
        if provider is not StockProvider.PIXABAY:
            raise StockSourceError("Pixabay transport only accepts pixabay requests")

        per_page = max(3, max_results)
        params = urlencode(
            {
                "key": self._api_key,
                "q": query,
                "per_page": per_page,
                "page": 1,
                "safesearch": "true",
                "image_type": "photo",
            }
        )
        payload, headers = self._fetch_json(f"{_SEARCH_URL}?{params}")
        hits = payload.get("hits")
        if not isinstance(hits, list):
            raise StockSourceError("Pixabay hits must be a list")

        retrieved_at = datetime.now(UTC).isoformat()
        candidates: list[StockAssetCandidate] = []
        for hit in hits:
            candidate = _candidate(hit, retrieved_at)
            if candidate is not None:
                candidates.append(candidate)
            if len(candidates) >= max_results:
                break

        remaining = _non_negative_int_header(headers, "x-ratelimit-remaining")
        reset = headers.get("x-ratelimit-reset")
        if remaining == 0 and not reset:
            raise StockSourceError("Pixabay rate-limit reset is required at zero remaining")

        return StockSearchResult(
            request=request,
            candidates=tuple(candidates),
            rate_limit=RateLimitState(remaining=remaining, reset_at_iso8601=reset),
        )


def _candidate(hit: Any, retrieved_at: str) -> StockAssetCandidate | None:
    if not isinstance(hit, dict):
        raise StockSourceError("Pixabay hit must be an object")
    asset_id = hit.get("id")
    source_url = hit.get("pageURL")
    creator = hit.get("user")
    media_url = hit.get("largeImageURL")
    preview_url = hit.get("webformatURL")
    width = hit.get("imageWidth")
    height = hit.get("imageHeight")
    if not isinstance(asset_id, int) or asset_id <= 0:
        return None
    if not isinstance(source_url, str) or not source_url.startswith("https://"):
        return None
    if not isinstance(creator, str) or not creator.strip():
        return None
    if not isinstance(media_url, str) or not media_url.startswith("https://"):
        return None
    if preview_url is not None and (
        not isinstance(preview_url, str) or not preview_url.startswith("https://")
    ):
        return None
    if not isinstance(width, int) or width <= 0:
        width = None
    if not isinstance(height, int) or height <= 0:
        height = None

    return StockAssetCandidate(
        media_url=media_url,
        preview_url=preview_url,
        media_type="image",
        width=width,
        height=height,
        provenance=SourceProvenance(
            provider=StockProvider.PIXABAY,
            source_url=source_url,
            asset_id=str(asset_id),
            creator=creator.strip(),
            license_name="Pixabay Content License",
            license_url=_LICENSE_URL,
            attribution_required=False,
            retrieved_at_iso8601=retrieved_at,
        ),
    )


def _non_negative_int_header(headers: dict[str, str], name: str) -> int | None:
    value = headers.get(name)
    if value is None:
        return None
    try:
        parsed = int(value)
    except ValueError as exc:
        raise StockSourceError(f"Pixabay {name} header must be an integer") from exc
    if parsed < 0:
        raise StockSourceError(f"Pixabay {name} header must not be negative")
    return parsed


def _fetch_json(url: str) -> tuple[dict[str, Any], dict[str, str]]:
    request = Request(url, headers={"User-Agent": _USER_AGENT, "Accept": "application/json"})
    try:
        with urlopen(request, timeout=15) as response:  # noqa: S310 - fixed HTTPS host
            payload = json.load(response)
            headers = {key.casefold(): value for key, value in response.headers.items()}
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise StockSourceError("Pixabay HTTP request failed closed") from exc
    if not isinstance(payload, dict):
        raise StockSourceError("Pixabay response must be a JSON object")
    return payload, headers
