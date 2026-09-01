"""Tests for canonical M17 Timeline Engine."""

from __future__ import annotations

from hashlib import sha256

import pytest

from src.video_automation.models import (
    MediaAsset,
    MediaType,
    Timeline,
)
from src.video_automation.timeline_engine import (
    CanonicalTimelineEngine,
    TimelineEngineError,
)


def _asset(
    *,
    asset_id: str,
    media_type: MediaType,
    job_id: str = "job-1",
    validated: bool = True,
) -> MediaAsset:
    return MediaAsset(
        asset_id=asset_id,
        job_id=job_id,
        media_type=media_type,
        file_path=f"C:/canonical/{asset_id}.bin",
        checksum_sha256=sha256(
            asset_id.encode("utf-8")
        ).hexdigest(),
        provider_name="canonical-test",
        source_reference=f"local://{asset_id}",
        validated=validated,
    )


def test_builds_existing_canonical_timeline_model() -> None:
    video = _asset(
        asset_id="video-1",
        media_type=MediaType.VIDEO,
    )
    voice = _asset(
        asset_id="voice-1",
        media_type=MediaType.VOICE,
    )

    timeline = CanonicalTimelineEngine().build(
        job_id="job-1",
        assets=(video, voice),
        start_seconds_by_asset_id={
            "video-1": 0.0,
            "voice-1": 0.0,
        },
        duration_seconds_by_asset_id={
            "video-1": 5.0,
            "voice-1": 5.0,
        },
        layer_by_asset_id={
            "video-1": 0,
            "voice-1": 10,
        },
    )

    assert isinstance(timeline, Timeline)
    assert timeline.job_id == "job-1"
    assert len(timeline.items) == 2

    assert {
        item.asset_id
        for item in timeline.items
    } == {"video-1", "voice-1"}


def test_items_are_sorted_deterministically() -> None:
    image = _asset(
        asset_id="image-1",
        media_type=MediaType.IMAGE,
    )
    video = _asset(
        asset_id="video-1",
        media_type=MediaType.VIDEO,
    )
    overlay = _asset(
        asset_id="overlay-1",
        media_type=MediaType.OVERLAY,
    )

    timeline = CanonicalTimelineEngine().build(
        job_id="job-1",
        assets=(overlay, image, video),
        start_seconds_by_asset_id={
            "overlay-1": 2.0,
            "image-1": 0.0,
            "video-1": 0.0,
        },
        duration_seconds_by_asset_id={
            "overlay-1": 1.0,
            "image-1": 2.0,
            "video-1": 2.0,
        },
        layer_by_asset_id={
            "overlay-1": 20,
            "image-1": 5,
            "video-1": 0,
        },
    )

    assert tuple(
        item.asset_id
        for item in timeline.items
    ) == (
        "video-1",
        "image-1",
        "overlay-1",
    )


def test_all_canonical_asset_categories_are_supported() -> None:
    media_types = (
        MediaType.VIDEO,
        MediaType.IMAGE,
        MediaType.VOICE,
        MediaType.AUDIO,
        MediaType.MUSIC,
        MediaType.SOUND_EFFECT,
        MediaType.SUBTITLE,
        MediaType.OVERLAY,
    )

    assets = tuple(
        _asset(
            asset_id=f"asset-{index}",
            media_type=media_type,
        )
        for index, media_type in enumerate(
            media_types,
            start=1,
        )
    )

    starts = {
        asset.asset_id: float(index)
        for index, asset in enumerate(assets)
    }
    durations = {
        asset.asset_id: 1.0
        for asset in assets
    }
    layers = {
        asset.asset_id: index
        for index, asset in enumerate(assets)
    }

    timeline = CanonicalTimelineEngine().build(
        job_id="job-1",
        assets=assets,
        start_seconds_by_asset_id=starts,
        duration_seconds_by_asset_id=durations,
        layer_by_asset_id=layers,
    )

    assert len(timeline.items) == len(media_types)


def test_item_identifiers_are_deterministic() -> None:
    asset = _asset(
        asset_id="video-1",
        media_type=MediaType.VIDEO,
    )

    engine = CanonicalTimelineEngine()

    first = engine.build(
        job_id="job-1",
        assets=(asset,),
        start_seconds_by_asset_id={
            "video-1": 0.0,
        },
        duration_seconds_by_asset_id={
            "video-1": 4.0,
        },
        layer_by_asset_id={
            "video-1": 0,
        },
    )

    second = engine.build(
        job_id="job-1",
        assets=(asset,),
        start_seconds_by_asset_id={
            "video-1": 0.0,
        },
        duration_seconds_by_asset_id={
            "video-1": 4.0,
        },
        layer_by_asset_id={
            "video-1": 0,
        },
    )

    assert first == second
    assert (
        first.items[0].item_id
        == second.items[0].item_id
    )


def test_different_placement_changes_item_identity() -> None:
    asset = _asset(
        asset_id="video-1",
        media_type=MediaType.VIDEO,
    )

    engine = CanonicalTimelineEngine()

    first = engine.build(
        job_id="job-1",
        assets=(asset,),
        start_seconds_by_asset_id={"video-1": 0.0},
        duration_seconds_by_asset_id={"video-1": 4.0},
        layer_by_asset_id={"video-1": 0},
    )

    second = engine.build(
        job_id="job-1",
        assets=(asset,),
        start_seconds_by_asset_id={"video-1": 1.0},
        duration_seconds_by_asset_id={"video-1": 4.0},
        layer_by_asset_id={"video-1": 0},
    )

    assert (
        first.items[0].item_id
        != second.items[0].item_id
    )


def test_unvalidated_asset_fails_closed() -> None:
    asset = _asset(
        asset_id="video-1",
        media_type=MediaType.VIDEO,
        validated=False,
    )

    with pytest.raises(
        TimelineEngineError,
        match="must be validated",
    ):
        CanonicalTimelineEngine().build(
            job_id="job-1",
            assets=(asset,),
            start_seconds_by_asset_id={"video-1": 0.0},
            duration_seconds_by_asset_id={"video-1": 1.0},
            layer_by_asset_id={"video-1": 0},
        )


def test_job_identity_mismatch_fails_closed() -> None:
    asset = _asset(
        asset_id="video-1",
        media_type=MediaType.VIDEO,
        job_id="other-job",
    )

    with pytest.raises(
        TimelineEngineError,
        match="job_id",
    ):
        CanonicalTimelineEngine().build(
            job_id="job-1",
            assets=(asset,),
            start_seconds_by_asset_id={"video-1": 0.0},
            duration_seconds_by_asset_id={"video-1": 1.0},
            layer_by_asset_id={"video-1": 0},
        )


def test_duplicate_asset_identifiers_fail_closed() -> None:
    first = _asset(
        asset_id="video-1",
        media_type=MediaType.VIDEO,
    )
    second = _asset(
        asset_id="video-1",
        media_type=MediaType.VIDEO,
    )

    with pytest.raises(
        TimelineEngineError,
        match="identifiers must be unique",
    ):
        CanonicalTimelineEngine().build(
            job_id="job-1",
            assets=(first, second),
            start_seconds_by_asset_id={"video-1": 0.0},
            duration_seconds_by_asset_id={"video-1": 1.0},
            layer_by_asset_id={"video-1": 0},
        )


def test_missing_placement_key_fails_closed() -> None:
    asset = _asset(
        asset_id="video-1",
        media_type=MediaType.VIDEO,
    )

    with pytest.raises(
        TimelineEngineError,
        match="exactly match",
    ):
        CanonicalTimelineEngine().build(
            job_id="job-1",
            assets=(asset,),
            start_seconds_by_asset_id={},
            duration_seconds_by_asset_id={"video-1": 1.0},
            layer_by_asset_id={"video-1": 0},
        )


def test_unexpected_placement_key_fails_closed() -> None:
    asset = _asset(
        asset_id="video-1",
        media_type=MediaType.VIDEO,
    )

    with pytest.raises(
        TimelineEngineError,
        match="unexpected",
    ):
        CanonicalTimelineEngine().build(
            job_id="job-1",
            assets=(asset,),
            start_seconds_by_asset_id={
                "video-1": 0.0,
                "unknown": 1.0,
            },
            duration_seconds_by_asset_id={"video-1": 1.0},
            layer_by_asset_id={"video-1": 0},
        )


def test_negative_start_fails_closed() -> None:
    asset = _asset(
        asset_id="video-1",
        media_type=MediaType.VIDEO,
    )

    with pytest.raises(
        TimelineEngineError,
        match="start_seconds",
    ):
        CanonicalTimelineEngine().build(
            job_id="job-1",
            assets=(asset,),
            start_seconds_by_asset_id={"video-1": -1.0},
            duration_seconds_by_asset_id={"video-1": 1.0},
            layer_by_asset_id={"video-1": 0},
        )


def test_non_positive_duration_fails_closed() -> None:
    asset = _asset(
        asset_id="video-1",
        media_type=MediaType.VIDEO,
    )

    with pytest.raises(
        TimelineEngineError,
        match="duration_seconds",
    ):
        CanonicalTimelineEngine().build(
            job_id="job-1",
            assets=(asset,),
            start_seconds_by_asset_id={"video-1": 0.0},
            duration_seconds_by_asset_id={"video-1": 0.0},
            layer_by_asset_id={"video-1": 0},
        )


def test_negative_layer_fails_closed() -> None:
    asset = _asset(
        asset_id="video-1",
        media_type=MediaType.VIDEO,
    )

    with pytest.raises(
        TimelineEngineError,
        match="layer",
    ):
        CanonicalTimelineEngine().build(
            job_id="job-1",
            assets=(asset,),
            start_seconds_by_asset_id={"video-1": 0.0},
            duration_seconds_by_asset_id={"video-1": 1.0},
            layer_by_asset_id={"video-1": -1},
        )


def test_empty_assets_fail_closed() -> None:
    with pytest.raises(
        TimelineEngineError,
        match="at least one",
    ):
        CanonicalTimelineEngine().build(
            job_id="job-1",
            assets=(),
            start_seconds_by_asset_id={},
            duration_seconds_by_asset_id={},
            layer_by_asset_id={},
        )
