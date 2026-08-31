"""Real Wikimedia Commons HTTP transport for the governed stock-source contract."""

from __future__ import annotations

import html
import json
import re
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

_API_URL = "https://commons.wikimedia.org/w/api.php"
_USER_AGENT = "ILAIOS-VideoFactory/1.0 (https://ilaios.com)"
_TAG_RE = re.compile(r"<[^>]+>")

JsonFetcher = Callable[[str], dict[str, Any]]


class WikimediaStockHttpTransport:
    """Execute one real Commons search and bind license/provenance metadata."""

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
        if provider is not StockProvider.WIKIMEDIA:
            raise StockSourceError("Wikimedia transport only accepts wikimedia requests")

        params = {
            "action": "query",
            "format": "json",
            "formatversion": "2",
            "generator": "search",
            "gsrnamespace": "6",
            "gsrsearch": query,
            "gsrlimit": str(max_results),
            "prop": "imageinfo",
            "iiprop": "url|size|mime|extmetadata",
            "iiextmetadatafilter": "Artist|LicenseShortName|LicenseUrl|UsageTerms",
        }
        payload = self._fetch_json(f"{_API_URL}?{urlencode(params)}")
        pages = payload.get("query", {}).get("pages", [])
        if not isinstance(pages, list):
            raise StockSourceError("Wikimedia response pages must be a list")

        candidates: list[StockAssetCandidate] = []
        retrieved_at = datetime.now(UTC).isoformat()
        for page in pages:
            candidate = _candidate_from_page(page, retrieved_at)
            if candidate is not None:
                candidates.append(candidate)
            if len(candidates) >= max_results:
                break

        return StockSearchResult(
            request=request,
            candidates=tuple(candidates),
            rate_limit=RateLimitState(remaining=None, reset_at_iso8601=None),
        )


def _candidate_from_page(page: Any, retrieved_at: str) -> StockAssetCandidate | None:
    if not isinstance(page, dict):
        raise StockSourceError("Wikimedia page entry must be an object")
    title = page.get("title")
    imageinfo = page.get("imageinfo")
    if not isinstance(title, str) or not isinstance(imageinfo, list) or not imageinfo:
        return None
    info = imageinfo[0]
    if not isinstance(info, dict):
        raise StockSourceError("Wikimedia imageinfo entry must be an object")
    media_url = info.get("url")
    source_url = info.get("descriptionurl")
    metadata = info.get("extmetadata", {})
    if not isinstance(media_url, str) or not isinstance(source_url, str):
        return None
    if not isinstance(metadata, dict):
        raise StockSourceError("Wikimedia extmetadata must be an object")

    license_name = _metadata_value(metadata, "LicenseShortName")
    if not license_name:
        license_name = _metadata_value(metadata, "UsageTerms")
    if not license_name:
        return None
    license_url = _metadata_value(metadata, "LicenseUrl") or None
    creator = _clean_creator(_metadata_value(metadata, "Artist")) or None
    attribution_required = _requires_attribution(license_name)
    if attribution_required and creator is None:
        return None

    mime = info.get("mime")
    media_type = _media_type(mime)
    if media_type is None:
        return None
    width = info.get("width") if isinstance(info.get("width"), int) else None
    height = info.get("height") if isinstance(info.get("height"), int) else None

    return StockAssetCandidate(
        media_url=media_url,
        preview_url=None,
        media_type=media_type,
        width=width,
        height=height,
        provenance=SourceProvenance(
            provider=StockProvider.WIKIMEDIA,
            source_url=source_url,
            asset_id=title,
            creator=creator,
            license_name=license_name,
            license_url=license_url,
            attribution_required=attribution_required,
            retrieved_at_iso8601=retrieved_at,
        ),
    )


def _metadata_value(metadata: dict[str, Any], key: str) -> str:
    entry = metadata.get(key)
    if not isinstance(entry, dict):
        return ""
    value = entry.get("value")
    return value.strip() if isinstance(value, str) else ""


def _clean_creator(value: str) -> str:
    return html.unescape(_TAG_RE.sub(" ", value)).strip()


def _requires_attribution(license_name: str) -> bool:
    normalized = license_name.casefold().replace("-", " ")
    return "public domain" not in normalized and "cc0" not in normalized


def _media_type(mime: Any) -> str | None:
    if not isinstance(mime, str):
        return None
    if mime.startswith("image/"):
        return "image"
    if mime.startswith("video/"):
        return "video"
    if mime.startswith("audio/"):
        return "audio"
    return None


def _fetch_json(url: str) -> dict[str, Any]:
    request = Request(url, headers={"User-Agent": _USER_AGENT, "Accept": "application/json"})
    try:
        with urlopen(request, timeout=15) as response:  # noqa: S310 - fixed HTTPS host
            payload = json.load(response)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise StockSourceError("Wikimedia HTTP request failed closed") from exc
    if not isinstance(payload, dict):
        raise StockSourceError("Wikimedia response must be a JSON object")
    return payload
