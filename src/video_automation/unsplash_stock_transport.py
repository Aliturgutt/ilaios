"""Real Unsplash HTTP transport for the governed stock-source contract."""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any, cast
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

_SEARCH_URL = "https://api.unsplash.com/search/photos"
_LICENSE_URL = "https://unsplash.com/license"
_USER_AGENT = "ILAIOS-VideoFactory/1.0 (https://ilaios.com)"

JsonFetcher = Callable[[str, str], tuple[dict[str, Any], dict[str, str]]]


class UnsplashStockHttpTransport:
    """Execute Unsplash photo search with explicit credential and attribution binding."""

    def __init__(self, access_key: str, fetch_json: JsonFetcher | None = None) -> None:
        if not access_key or not access_key.strip() or access_key != access_key.strip():
            raise StockSourceError("Unsplash access key must be non-blank and trimmed")
        self._access_key = access_key
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
        if provider is not StockProvider.UNSPLASH:
            raise StockSourceError("Unsplash transport only accepts unsplash requests")

        params = urlencode({"query": query, "per_page": max_results, "page": 1})
        payload, headers = self._fetch_json(f"{_SEARCH_URL}?{params}", self._access_key)
        results = payload.get("results")
        if not isinstance(results, list):
            raise StockSourceError("Unsplash results must be a list")

        retrieved_at = datetime.now(UTC).isoformat()
        candidates: list[StockAssetCandidate] = []
        for photo in results:
            candidate = _candidate(photo, retrieved_at)
            if candidate is not None:
                candidates.append(candidate)
            if len(candidates) >= max_results:
                break

        remaining = _non_negative_int_header(headers, "x-ratelimit-remaining")
        reset = headers.get("x-ratelimit-reset")
        if remaining == 0 and not reset:
            raise StockSourceError("Unsplash rate-limit reset is required at zero remaining")

        return StockSearchResult(
            request=request,
            candidates=tuple(candidates),
            rate_limit=RateLimitState(remaining=remaining, reset_at_iso8601=reset),
        )


def _candidate(photo: Any, retrieved_at: str) -> StockAssetCandidate | None:
    if not isinstance(photo, dict):
        raise StockSourceError("Unsplash photo must be an object")
    asset_id = photo.get("id")
    links = photo.get("links")
    urls = photo.get("urls")
    user = photo.get("user")
    width = photo.get("width")
    height = photo.get("height")
    if not isinstance(asset_id, str) or not asset_id.strip():
        return None
    if not isinstance(links, dict) or not isinstance(urls, dict) or not isinstance(user, dict):
        return None
    source_url = links.get("html")
    media_url = urls.get("full")
    preview_url = urls.get("small")
    creator = user.get("name")
    if not isinstance(source_url, str) or not source_url.startswith("https://"):
        return None
    if not isinstance(media_url, str) or not media_url.startswith("https://"):
        return None
    if preview_url is not None and (
        not isinstance(preview_url, str) or not preview_url.startswith("https://")
    ):
        return None
    if not isinstance(creator, str) or not creator.strip():
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
            provider=StockProvider.UNSPLASH,
            source_url=source_url,
            asset_id=asset_id.strip(),
            creator=creator.strip(),
            license_name="Unsplash License",
            license_url=_LICENSE_URL,
            attribution_required=True,
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
        raise StockSourceError(f"Unsplash {name} header must be an integer") from exc
    if parsed < 0:
        raise StockSourceError(f"Unsplash {name} header must not be negative")
    return parsed


def _fetch_json(url: str, access_key: str) -> tuple[dict[str, Any], dict[str, str]]:
    request = Request(
        url,
        headers={
            "Authorization": f"Client-ID {access_key}",
            "User-Agent": _USER_AGENT,
            "Accept-Version": "v1",
            "Accept": "application/json",
        },
    )
    try:
        with urlopen(request, timeout=15) as response:  # noqa: S310 - fixed HTTPS host
            raw_payload: object = json.load(response)
            headers = {key.casefold(): value for key, value in response.headers.items()}
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise StockSourceError("Unsplash HTTP request failed closed") from exc
    if not isinstance(raw_payload, dict):
        raise StockSourceError("Unsplash response must be a JSON object")
    payload = cast(dict[str, Any], raw_payload)
    return payload, headers
