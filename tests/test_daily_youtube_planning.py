from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.video_automation.daily_topic_selection import DailyTopicCandidate
from src.video_automation.daily_youtube_planning import (
    DailySourceAggregator,
    DailySourceObservation,
    DailyYouTubePlanningError,
    YouTubeEditorialPolicy,
    prepare_youtube_target,
)


NOW = datetime(2026, 9, 8, 0, 0, tzinfo=timezone.utc)


def _observation(url: str, *, topic_id: str = "topic-1") -> DailySourceObservation:
    return DailySourceObservation(
        topic_id=topic_id,
        title="AI chip market expands",
        summary="Two independent reports describe the same verified market development.",
        category="technology",
        published_at=NOW,
        source_url=url,
        relevance_score=0.9,
        advertiser_value_score=0.8,
        freshness_score=0.95,
    )


def test_source_aggregator_requires_two_independent_origins() -> None:
    aggregator = DailySourceAggregator()
    assert aggregator.aggregate((_observation("https://example.com/a"),)) == ()
    assert aggregator.aggregate(
        (
            _observation("https://example.com/a"),
            _observation("https://example.com/b"),
        )
    ) == ()

    candidates = aggregator.aggregate(
        (
            _observation("https://example.com/a"),
            _observation("https://second.example/b"),
        )
    )
    assert len(candidates) == 1
    assert candidates[0].independent_source_refs == (
        "https://example.com/a",
        "https://second.example/b",
    )


def test_source_aggregator_rejects_category_conflict() -> None:
    first = _observation("https://example.com/a")
    second = DailySourceObservation(
        topic_id="topic-1",
        title=first.title,
        summary=first.summary,
        category="business",
        published_at=NOW,
        source_url="https://second.example/b",
        relevance_score=0.9,
        advertiser_value_score=0.8,
        freshness_score=0.95,
    )
    assert DailySourceAggregator().aggregate((first, second)) == ()


def _candidate() -> DailyTopicCandidate:
    return DailySourceAggregator().aggregate(
        (
            _observation("https://example.com/a"),
            _observation("https://second.example/b"),
        )
    )[0]


def test_prepare_youtube_target_carries_complete_metadata() -> None:
    target = prepare_youtube_target(
        candidate=_candidate(),
        scheduled_at=NOW,
        policy=YouTubeEditorialPolicy(
            account_id="channel-001",
            category_id="28",
            contains_synthetic_media=True,
        ),
        title="AI Chip Market: What Changed",
        description="A concise evidence-bound explanation of today's development.",
        hashtags=("#AI", "#Technology", "#Business"),
        tags=("ai", "technology", "business"),
        thumbnail_path="/tmp/thumb.jpg",
        thumbnail_sha256="a" * 64,
    )

    assert target.platform == "youtube"
    assert target.tags == ("ai", "technology", "business")
    assert "#AI #Technology #Business" in target.description
    assert "https://example.com/a" in target.description
    assert target.metadata["youtube_category_id"] == "28"
    assert target.metadata["youtube_default_language"] == "en"
    assert target.metadata["youtube_self_declared_made_for_kids"] == "false"
    assert target.metadata["youtube_contains_synthetic_media"] == "true"
    assert target.metadata["daily_source_count"] == "2"


def test_prepare_youtube_target_fails_closed_on_hashtag_or_thumbnail_evidence() -> None:
    common = dict(
        candidate=_candidate(),
        scheduled_at=NOW,
        policy=YouTubeEditorialPolicy(account_id="channel-001", category_id="28"),
        title="AI Chip Market: What Changed",
        description="Evidence-bound explanation.",
        tags=("ai", "technology"),
        thumbnail_path="/tmp/thumb.jpg",
        thumbnail_sha256="a" * 64,
    )
    with pytest.raises(DailyYouTubePlanningError):
        prepare_youtube_target(hashtags=("#AI", "#Tech"), **common)
    with pytest.raises(DailyYouTubePlanningError):
        prepare_youtube_target(
            hashtags=("#AI", "#Tech", "#Business"),
            **{**common, "thumbnail_sha256": "bad"},
        )
