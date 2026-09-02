from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from src.video_automation.governed_stock_composition import (
    GovernedStockCompositionError,
    composition_input_from_selection,
    ffmpeg_stock_input_args,
    stock_visual_filter,
)
from src.video_automation.governed_stock_selection import (
    GovernedStockSelection,
    StockSelectionAttempt,
)
from src.video_automation.stock_source_adapters import (
    SourceProvenance,
    StockAssetCandidate,
    StockProvider,
)


def _selection(*, media_type: str = "video") -> GovernedStockSelection:
    candidate = StockAssetCandidate(
        media_url="https://media.example.test/asset",
        preview_url=None,
        media_type=media_type,
        width=1920,
        height=1080,
        provenance=SourceProvenance(
            provider=StockProvider.WIKIMEDIA,
            source_url="https://commons.wikimedia.org/wiki/File:Example.webm",
            asset_id="File:Example.webm",
            creator="Example Creator",
            license_name="CC BY 4.0",
            license_url="https://creativecommons.org/licenses/by/4.0/",
            attribution_required=True,
            retrieved_at_iso8601="2026-09-02T00:00:00+00:00",
        ),
    )
    return GovernedStockSelection(
        candidate=candidate,
        attempts=(
            StockSelectionAttempt(StockProvider.PEXELS, "empty", 0),
            StockSelectionAttempt(StockProvider.WIKIMEDIA, "selected", 1),
        ),
    )


def _media(tmp_path: Path) -> Path:
    path = tmp_path / "stock.bin"
    path.write_bytes(b"governed-stock-media")
    return path


def test_composition_input_binds_selected_provenance_and_bytes(tmp_path: Path) -> None:
    media = _media(tmp_path)
    composition = composition_input_from_selection(_selection(), media_path=media)

    assert composition.media_sha256 == hashlib.sha256(media.read_bytes()).hexdigest()
    assert composition.provider == "wikimedia"
    assert composition.source_url.startswith("https://commons.wikimedia.org/")
    assert composition.license_name == "CC BY 4.0"
    assert composition.attribution_required is True
    assert composition.selection_attempts == (
        ("pexels", "empty", 0),
        ("wikimedia", "selected", 1),
    )


def test_exact_final_artifact_evidence_preserves_stock_provenance(tmp_path: Path) -> None:
    composition = composition_input_from_selection(_selection(), media_path=_media(tmp_path))
    final_sha = "a" * 64

    evidence = composition.evidence(final_mp4_sha256=final_sha)

    assert evidence["final_mp4_sha256"] == final_sha
    assert evidence["stock_provider"] == "wikimedia"
    assert evidence["stock_license_name"] == "CC BY 4.0"
    assert evidence["stock_selection_attempts"][-1]["status"] == "selected"


def test_ffmpeg_input_is_bounded_by_media_type(tmp_path: Path) -> None:
    video = composition_input_from_selection(_selection(media_type="video"), media_path=_media(tmp_path))
    assert ffmpeg_stock_input_args(video)[:2] == ("-stream_loop", "-1")

    image_selection = _selection(media_type="image")
    image = composition_input_from_selection(image_selection, media_path=_media(tmp_path))
    assert ffmpeg_stock_input_args(image)[:2] == ("-loop", "1")
    assert "crop=1920:1080" in stock_visual_filter()
    assert "fps=24" in stock_visual_filter()


def test_composition_rejects_audio_only_asset(tmp_path: Path) -> None:
    with pytest.raises(GovernedStockCompositionError, match="only image or video"):
        composition_input_from_selection(
            _selection(media_type="audio"),
            media_path=_media(tmp_path),
        )


def test_composition_rejects_missing_selection_terminal_state(tmp_path: Path) -> None:
    selection = _selection()
    invalid = GovernedStockSelection(
        candidate=selection.candidate,
        attempts=(StockSelectionAttempt(StockProvider.WIKIMEDIA, "empty", 1),),
    )
    with pytest.raises(GovernedStockCompositionError, match="terminate in selected"):
        composition_input_from_selection(invalid, media_path=_media(tmp_path))


def test_final_evidence_rejects_malformed_sha(tmp_path: Path) -> None:
    composition = composition_input_from_selection(_selection(), media_path=_media(tmp_path))
    with pytest.raises(GovernedStockCompositionError, match="SHA-256"):
        composition.evidence(final_mp4_sha256="bad")
