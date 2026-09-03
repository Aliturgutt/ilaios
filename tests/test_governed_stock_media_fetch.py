from __future__ import annotations

from email.message import Message
from pathlib import Path

import pytest

import src.video_automation.governed_stock_media_fetch as media_fetch
from src.video_automation.governed_stock_media_fetch import (
    GovernedStockMediaFetchError,
    fetch_selected_stock_media,
)
from src.video_automation.stock_source_adapters import (
    SourceProvenance,
    StockAssetCandidate,
    StockProvider,
)


class _Headers(Message):
    pass


class _Response:
    def __init__(
        self,
        payload: bytes,
        *,
        content_type: str = "video/mp4",
        final_url: str = "https://cdn.example.test/asset.mp4",
    ) -> None:
        self._payload = payload
        self._offset = 0
        self._final_url = final_url
        self.headers = _Headers()
        self.headers["Content-Type"] = content_type
        self.headers["Content-Length"] = str(len(payload))

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def geturl(self) -> str:
        return self._final_url

    def read(self, size: int) -> bytes:
        chunk = self._payload[self._offset : self._offset + size]
        self._offset += len(chunk)
        return chunk


def _candidate(*, media_type: str = "video") -> StockAssetCandidate:
    return StockAssetCandidate(
        media_url="https://media.example.test/asset.mp4",
        preview_url=None,
        media_type=media_type,
        width=1920,
        height=1080,
        provenance=SourceProvenance(
            provider=StockProvider.WIKIMEDIA,
            source_url="https://commons.wikimedia.org/wiki/File:Example.webm",
            asset_id="File:Example.webm",
            creator="Creator",
            license_name="CC BY 4.0",
            license_url="https://creativecommons.org/licenses/by/4.0/",
            attribution_required=True,
            retrieved_at_iso8601="2026-09-02T00:00:00+00:00",
        ),
    )


def test_fetch_selected_stock_media_writes_bounded_exact_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = b"video-bytes"
    monkeypatch.setattr(media_fetch, "urlopen", lambda *_args, **_kwargs: _Response(payload))
    destination = tmp_path / "stock.mp4"

    fetched = fetch_selected_stock_media(_candidate(), destination=destination)

    assert destination.read_bytes() == payload
    assert fetched.size == len(payload)
    assert len(fetched.sha256) == 64
    assert not destination.with_suffix(".mp4.part").exists()


def test_fetch_rejects_content_type_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        media_fetch,
        "urlopen",
        lambda *_args, **_kwargs: _Response(b"not-video", content_type="image/jpeg"),
    )
    destination = tmp_path / "stock.mp4"

    with pytest.raises(GovernedStockMediaFetchError, match="content type"):
        fetch_selected_stock_media(_candidate(), destination=destination)

    assert not destination.exists()
    assert not destination.with_suffix(".mp4.part").exists()


def test_fetch_rejects_https_to_http_redirect(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        media_fetch,
        "urlopen",
        lambda *_args, **_kwargs: _Response(
            b"video",
            final_url="http://insecure.example.test/asset.mp4",
        ),
    )

    with pytest.raises(GovernedStockMediaFetchError, match="remain on https"):
        fetch_selected_stock_media(_candidate(), destination=tmp_path / "stock.mp4")


def test_fetch_rejects_audio_candidate_before_network(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = 0

    def _unexpected(*_args: object, **_kwargs: object) -> _Response:
        nonlocal calls
        calls += 1
        return _Response(b"audio")

    monkeypatch.setattr(media_fetch, "urlopen", _unexpected)
    with pytest.raises(GovernedStockMediaFetchError, match="only image or video"):
        fetch_selected_stock_media(
            _candidate(media_type="audio"),
            destination=tmp_path / "stock.bin",
        )
    assert calls == 0
