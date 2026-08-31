"""Real Internet Archive HTTP transport for the governed stock-source contract."""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any, cast
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

_SEARCH_URL = "https://archive.org/advancedsearch.php"
_USER_AGENT = "ILAIOS-VideoFactory/1.0 (https://ilaios.com)"

JsonFetcher = Callable[[str], dict[str, Any]]


class InternetArchiveStockHttpTransport:
    """Execute Internet Archive search and bind item/file provenance metadata."""

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
        if provider is not StockProvider.INTERNET_ARCHIVE:
            raise StockSourceError(
                "Internet Archive transport only accepts internet_archive requests"
            )

        params = urlencode(
            [
                ("q", query),
                ("fl[]", "identifier"),
                ("rows", str(max_results)),
                ("page", "1"),
                ("output", "json"),
            ]
        )
        payload = self._fetch_json(f"{_SEARCH_URL}?{params}")
        response = payload.get("response")
        if not isinstance(response, dict):
            raise StockSourceError("Internet Archive response must be an object")
        docs = response.get("docs", [])
        if not isinstance(docs, list):
            raise StockSourceError("Internet Archive docs must be a list")

        retrieved_at = datetime.now(UTC).isoformat()
        candidates: list[StockAssetCandidate] = []
        for doc in docs:
            candidate = self._candidate_from_doc(doc, retrieved_at)
            if candidate is not None:
                candidates.append(candidate)
            if len(candidates) >= max_results:
                break

        return StockSearchResult(
            request=request,
            candidates=tuple(candidates),
            rate_limit=RateLimitState(remaining=None, reset_at_iso8601=None),
        )

    def _candidate_from_doc(
        self, doc: Any, retrieved_at: str
    ) -> StockAssetCandidate | None:
        if not isinstance(doc, dict):
            raise StockSourceError("Internet Archive document must be an object")
        identifier = doc.get("identifier")
        if not isinstance(identifier, str) or not identifier.strip():
            return None

        encoded_id = quote(identifier, safe="")
        payload = self._fetch_json(f"https://archive.org/metadata/{encoded_id}")
        metadata = payload.get("metadata")
        files = payload.get("files")
        if not isinstance(metadata, dict) or not isinstance(files, list):
            raise StockSourceError("Internet Archive metadata payload is malformed")

        license_url = metadata.get("licenseurl")
        if not isinstance(license_url, str) or not license_url.startswith("https://"):
            return None
        license_name = metadata.get("license")
        if not isinstance(license_name, str) or not license_name.strip():
            license_name = license_url

        creator = _creator(metadata)
        attribution_required = _requires_attribution(license_name, license_url)
        if attribution_required and creator is None:
            return None

        selected = _select_file(files)
        if selected is None:
            return None
        filename, media_type = selected
        media_url = (
            f"https://archive.org/download/{encoded_id}/{quote(filename, safe='')}"
        )

        return StockAssetCandidate(
            media_url=media_url,
            preview_url=None,
            media_type=media_type,
            width=None,
            height=None,
            provenance=SourceProvenance(
                provider=StockProvider.INTERNET_ARCHIVE,
                source_url=f"https://archive.org/details/{encoded_id}",
                asset_id=identifier,
                creator=creator,
                license_name=license_name.strip(),
                license_url=license_url,
                attribution_required=attribution_required,
                retrieved_at_iso8601=retrieved_at,
            ),
        )


def _creator(metadata: dict[str, Any]) -> str | None:
    value = metadata.get("creator")
    if isinstance(value, str) and value.strip():
        return value.strip()
    if isinstance(value, list):
        creators = [
            part.strip()
            for part in value
            if isinstance(part, str) and part.strip()
        ]
        if creators:
            return ", ".join(creators)
    return None


def _requires_attribution(license_name: str, license_url: str) -> bool:
    normalized = f"{license_name} {license_url}".casefold().replace("-", " ")
    return (
        "public domain" not in normalized
        and "/publicdomain/" not in normalized
        and "cc0" not in normalized
    )


def _select_file(files: list[Any]) -> tuple[str, str] | None:
    extension_groups = (
        ("video", (".mp4", ".mov", ".webm")),
        ("image", (".jpg", ".jpeg", ".png", ".tif", ".tiff")),
        ("audio", (".wav", ".mp3", ".m4a", ".ogg")),
    )
    for media_type, suffixes in extension_groups:
        for entry in files:
            if not isinstance(entry, dict):
                continue
            name = entry.get("name")
            if entry.get("source") != "original":
                continue
            if isinstance(name, str) and name.casefold().endswith(suffixes):
                return name, media_type
    return None


def _fetch_json(url: str) -> dict[str, Any]:
    request = Request(
        url,
        headers={"User-Agent": _USER_AGENT, "Accept": "application/json"},
    )
    try:
        with urlopen(
            request, timeout=15
        ) as response:  # noqa: S310 - fixed HTTPS hosts
            raw_payload: object = json.load(response)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise StockSourceError("Internet Archive HTTP request failed closed") from exc
    if not isinstance(raw_payload, dict):
        raise StockSourceError("Internet Archive response must be a JSON object")
    return cast(dict[str, Any], raw_payload)
