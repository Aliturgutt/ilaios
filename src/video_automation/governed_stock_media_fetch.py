"""Bounded HTTPS fetch boundary for already-selected governed stock media."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from src.video_automation.stock_source_adapters import StockAssetCandidate


class GovernedStockMediaFetchError(ValueError):
    """Raised when selected stock media cannot be fetched safely."""


_MAX_STOCK_MEDIA_BYTES = 128 * 1024 * 1024
_USER_AGENT = "ILAIOS-VideoFactory/1.0 (https://ilaios.com)"


@dataclass(frozen=True, slots=True)
class GovernedStockFetchedMedia:
    path: Path
    sha256: str
    size: int


def fetch_selected_stock_media(
    candidate: StockAssetCandidate,
    *,
    destination: Path,
    max_bytes: int = _MAX_STOCK_MEDIA_BYTES,
) -> GovernedStockFetchedMedia:
    if candidate.media_type not in {"image", "video"}:
        raise GovernedStockMediaFetchError(
            "selected stock fetch accepts only image or video media"
        )
    if not candidate.media_url.startswith("https://"):
        raise GovernedStockMediaFetchError("selected stock media URL must use https")
    if max_bytes < 1 or max_bytes > _MAX_STOCK_MEDIA_BYTES:
        raise GovernedStockMediaFetchError("stock media byte cap is invalid")

    request = Request(
        candidate.media_url,
        headers={"User-Agent": _USER_AGENT, "Accept": "image/*,video/*"},
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp = destination.with_suffix(destination.suffix + ".part")
    temp.unlink(missing_ok=True)
    digest = hashlib.sha256()
    size = 0
    try:
        with urlopen(request, timeout=20) as response:  # noqa: S310 - admitted HTTPS URL
            final_url = response.geturl()
            if not isinstance(final_url, str) or not final_url.startswith("https://"):
                raise GovernedStockMediaFetchError(
                    "selected stock redirect must remain on https"
                )
            content_type = response.headers.get_content_type()
            expected_prefix = "image/" if candidate.media_type == "image" else "video/"
            if not content_type.startswith(expected_prefix):
                raise GovernedStockMediaFetchError(
                    "selected stock response content type does not match admitted media"
                )
            declared = response.headers.get("Content-Length")
            if declared is not None:
                try:
                    declared_size = int(declared)
                except ValueError as exc:
                    raise GovernedStockMediaFetchError(
                        "selected stock content length is malformed"
                    ) from exc
                if declared_size < 1 or declared_size > max_bytes:
                    raise GovernedStockMediaFetchError(
                        "selected stock content length exceeds bounded limit"
                    )
            with temp.open("wb") as handle:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > max_bytes:
                        raise GovernedStockMediaFetchError(
                            "selected stock media exceeded bounded byte limit"
                        )
                    digest.update(chunk)
                    handle.write(chunk)
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        temp.unlink(missing_ok=True)
        raise GovernedStockMediaFetchError(
            "selected stock media fetch failed closed"
        ) from exc
    except GovernedStockMediaFetchError:
        temp.unlink(missing_ok=True)
        raise

    if size <= 0:
        temp.unlink(missing_ok=True)
        raise GovernedStockMediaFetchError("selected stock media response was empty")
    temp.replace(destination)
    return GovernedStockFetchedMedia(destination, digest.hexdigest(), size)
