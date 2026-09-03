"""Exact-artifact composition contract for governed Video Factory stock media.

This module does not select providers and does not perform network access. It accepts
one already-selected governed stock asset, binds its provenance/license metadata to
one local admitted media file, and builds the deterministic ffmpeg input/filter
contract used by the final Video Factory compositor.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from src.video_automation.governed_stock_selection import GovernedStockSelection


class GovernedStockCompositionError(ValueError):
    """Raised when governed stock media cannot be admitted for final composition."""


@dataclass(frozen=True, slots=True)
class GovernedStockCompositionInput:
    media_path: Path
    media_sha256: str
    media_type: str
    provider: str
    source_url: str
    asset_id: str
    creator: str | None
    license_name: str
    license_url: str | None
    attribution_required: bool
    retrieved_at_iso8601: str
    selection_attempts: tuple[tuple[str, str, int], ...]

    def __post_init__(self) -> None:
        if self.media_type not in {"image", "video"}:
            raise GovernedStockCompositionError(
                "final stock composition accepts only image or video assets"
            )
        if not self.media_path.is_file() or self.media_path.stat().st_size <= 0:
            raise GovernedStockCompositionError(
                "stock composition media_path must reference a non-empty file"
            )
        digest = hashlib.sha256(self.media_path.read_bytes()).hexdigest()
        if digest != self.media_sha256:
            raise GovernedStockCompositionError(
                "stock composition media SHA does not match admitted bytes"
            )
        if not self.provider.strip() or self.provider != self.provider.strip():
            raise GovernedStockCompositionError("stock provider must be non-blank and trimmed")
        if not self.source_url.startswith("https://"):
            raise GovernedStockCompositionError("stock source URL must use https")
        if not self.asset_id.strip() or self.asset_id != self.asset_id.strip():
            raise GovernedStockCompositionError("stock asset id must be non-blank and trimmed")
        if not self.license_name.strip() or self.license_name != self.license_name.strip():
            raise GovernedStockCompositionError(
                "stock license name must be non-blank and trimmed"
            )
        if self.license_url is not None and not self.license_url.startswith("https://"):
            raise GovernedStockCompositionError("stock license URL must use https")
        if self.attribution_required and not self.creator:
            raise GovernedStockCompositionError(
                "stock creator is required when attribution is required"
            )
        if not self.selection_attempts:
            raise GovernedStockCompositionError(
                "stock composition requires provider selection-attempt evidence"
            )
        if self.selection_attempts[-1][1] != "selected":
            raise GovernedStockCompositionError(
                "stock composition selection evidence must terminate in selected"
            )

    def evidence(self, *, final_mp4_sha256: str) -> dict[str, object]:
        if len(final_mp4_sha256) != 64:
            raise GovernedStockCompositionError("final MP4 SHA must be SHA-256")
        try:
            int(final_mp4_sha256, 16)
        except ValueError as exc:
            raise GovernedStockCompositionError("final MP4 SHA must be hexadecimal") from exc
        return {
            "final_mp4_sha256": final_mp4_sha256,
            "stock_media_sha256": self.media_sha256,
            "stock_media_type": self.media_type,
            "stock_provider": self.provider,
            "stock_source_url": self.source_url,
            "stock_asset_id": self.asset_id,
            "stock_creator": self.creator,
            "stock_license_name": self.license_name,
            "stock_license_url": self.license_url,
            "stock_attribution_required": self.attribution_required,
            "stock_retrieved_at_iso8601": self.retrieved_at_iso8601,
            "stock_selection_attempts": [
                {
                    "provider": provider,
                    "status": status,
                    "candidate_count": candidate_count,
                }
                for provider, status, candidate_count in self.selection_attempts
            ],
        }


def composition_input_from_selection(
    selection: GovernedStockSelection,
    *,
    media_path: Path,
) -> GovernedStockCompositionInput:
    candidate = selection.candidate
    provenance = candidate.provenance
    return GovernedStockCompositionInput(
        media_path=media_path,
        media_sha256=hashlib.sha256(media_path.read_bytes()).hexdigest(),
        media_type=candidate.media_type,
        provider=provenance.provider.value,
        source_url=provenance.source_url,
        asset_id=provenance.asset_id,
        creator=provenance.creator,
        license_name=provenance.license_name,
        license_url=provenance.license_url,
        attribution_required=provenance.attribution_required,
        retrieved_at_iso8601=provenance.retrieved_at_iso8601,
        selection_attempts=tuple(
            (attempt.provider.value, attempt.status, attempt.candidate_count)
            for attempt in selection.attempts
        ),
    )


def ffmpeg_stock_input_args(composition: GovernedStockCompositionInput) -> tuple[str, ...]:
    """Return bounded ffmpeg input args for an admitted image/video stock asset."""
    if composition.media_type == "image":
        return ("-loop", "1", "-i", str(composition.media_path))
    return ("-stream_loop", "-1", "-i", str(composition.media_path))


def stock_visual_filter() -> str:
    """Normalize stock footage into the canonical 1920x1080 delivery canvas."""
    return (
        "scale=1920:1080:force_original_aspect_ratio=increase,"
        "crop=1920:1080,setsar=1,fps=24"
    )
