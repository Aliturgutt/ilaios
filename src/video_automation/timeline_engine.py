"""Canonical M17 Timeline Engine for ILAIOS Video Automation.

M17 converts canonical MediaAsset records and explicit deterministic placement
data into the pre-existing M01 Timeline and TimelineItem contracts.

It does not render media, execute transitions, invoke FFmpeg, invoke Remotion,
mix audio, generate captions, or create uncontrolled filesystem references.
Programmatic transition/effect execution remains a later composition concern.
"""

from __future__ import annotations

from collections.abc import Mapping
from hashlib import sha256

from .models import (
    MediaAsset,
    MediaType,
    Timeline,
    TimelineItem,
)

_ALLOWED_MEDIA_TYPES = frozenset(
    {
        MediaType.VIDEO,
        MediaType.IMAGE,
        MediaType.VOICE,
        MediaType.AUDIO,
        MediaType.MUSIC,
        MediaType.SOUND_EFFECT,
        MediaType.SUBTITLE,
        MediaType.OVERLAY,
    }
)


class TimelineEngineError(ValueError):
    """Raised when canonical timeline construction cannot proceed safely."""


class CanonicalTimelineEngine:
    """Build the canonical M01 Timeline from validated placement evidence."""

    def build(
        self,
        *,
        job_id: str,
        assets: tuple[MediaAsset, ...],
        start_seconds_by_asset_id: Mapping[str, float],
        duration_seconds_by_asset_id: Mapping[str, float],
        layer_by_asset_id: Mapping[str, int],
    ) -> Timeline:
        """Return one deterministic timeline without rendering anything."""

        _require_non_blank("job_id", job_id)

        if not assets:
            raise TimelineEngineError(
                "assets must contain at least one MediaAsset"
            )

        asset_ids = tuple(asset.asset_id for asset in assets)

        if len(asset_ids) != len(set(asset_ids)):
            raise TimelineEngineError(
                "asset identifiers must be unique"
            )

        expected_ids = set(asset_ids)

        _require_exact_keys(
            "start_seconds_by_asset_id",
            start_seconds_by_asset_id,
            expected_ids,
        )
        _require_exact_keys(
            "duration_seconds_by_asset_id",
            duration_seconds_by_asset_id,
            expected_ids,
        )
        _require_exact_keys(
            "layer_by_asset_id",
            layer_by_asset_id,
            expected_ids,
        )

        items: list[TimelineItem] = []

        for asset in assets:
            self._validate_asset(
                job_id=job_id,
                asset=asset,
            )

            start_seconds = start_seconds_by_asset_id[
                asset.asset_id
            ]
            duration_seconds = duration_seconds_by_asset_id[
                asset.asset_id
            ]
            layer = layer_by_asset_id[asset.asset_id]

            if start_seconds < 0:
                raise TimelineEngineError(
                    "timeline start_seconds must be >= 0"
                )

            if duration_seconds <= 0:
                raise TimelineEngineError(
                    "timeline duration_seconds must be greater than 0"
                )

            if layer < 0:
                raise TimelineEngineError(
                    "timeline layer must be >= 0"
                )

            identity_material = "\n".join(
                (
                    f"job_id={job_id}",
                    f"asset_id={asset.asset_id}",
                    f"checksum={asset.checksum_sha256}",
                    f"start={start_seconds:.9f}",
                    f"duration={duration_seconds:.9f}",
                    f"layer={layer}",
                )
            )

            item_id = (
                "timeline-item-"
                + sha256(
                    identity_material.encode("utf-8")
                ).hexdigest()[:24]
            )

            items.append(
                TimelineItem(
                    item_id=item_id,
                    asset_id=asset.asset_id,
                    start_seconds=start_seconds,
                    duration_seconds=duration_seconds,
                    layer=layer,
                )
            )

        ordered_items = tuple(
            sorted(
                items,
                key=lambda item: (
                    item.start_seconds,
                    item.layer,
                    item.asset_id,
                    item.item_id,
                ),
            )
        )

        return Timeline(
            job_id=job_id,
            items=ordered_items,
        )

    def _validate_asset(
        self,
        *,
        job_id: str,
        asset: MediaAsset,
    ) -> None:
        if asset.job_id != job_id:
            raise TimelineEngineError(
                "timeline asset job_id does not match requested job_id"
            )

        if asset.media_type not in _ALLOWED_MEDIA_TYPES:
            raise TimelineEngineError(
                "asset media_type is not supported by canonical timeline"
            )

        if not asset.validated:
            raise TimelineEngineError(
                f"timeline asset must be validated: {asset.asset_id}"
            )


def _require_exact_keys(
    name: str,
    values: Mapping[str, object],
    expected_ids: set[str],
) -> None:
    actual_ids = set(values)

    if actual_ids != expected_ids:
        missing = sorted(expected_ids - actual_ids)
        unexpected = sorted(actual_ids - expected_ids)

        raise TimelineEngineError(
            f"{name} keys must exactly match asset identifiers; "
            f"missing={missing}, unexpected={unexpected}"
        )


def _require_non_blank(name: str, value: str) -> None:
    if not value or not value.strip():
        raise TimelineEngineError(
            f"{name} must not be blank"
        )

    if value != value.strip():
        raise TimelineEngineError(
            f"{name} must not contain surrounding whitespace"
        )
