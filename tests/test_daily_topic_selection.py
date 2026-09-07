from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from src.video_automation.daily_topic_selection import (
    DailyChannelPolicy,
    DailyTopicCandidate,
    DailyTopicSelectionError,
    DailyTopicSelector,
)


def _candidate(
    topic_id: str,
    *,
    category: str = "ai",
    sources: tuple[str, ...] = ("source:a", "source:b"),
    relevance: float = 0.8,
    advertiser: float = 0.8,
    freshness: float = 0.8,
    age_hours: int = 1,
    title: str | None = None,
    summary: str = "Verified technology development",
) -> DailyTopicCandidate:
    now = datetime(2026, 9, 8, 0, 0, tzinfo=timezone.utc)
    return DailyTopicCandidate(
        topic_id=topic_id,
        title=title or f"Topic {topic_id}",
        summary=summary,
        category=category,
        published_at=now - timedelta(hours=age_hours),
        independent_source_refs=sources,
        relevance_score=relevance,
        advertiser_value_score=advertiser,
        freshness_score=freshness,
    )


def _policy() -> DailyChannelPolicy:
    return DailyChannelPolicy(
        allowed_categories=("ai", "technology", "business", "economy"),
        blocked_terms=("celebrity gossip",),
    )


def test_selector_requires_two_independent_sources() -> None:
    selector = DailyTopicSelector()
    with pytest.raises(DailyTopicSelectionError):
        selector.select(
            [_candidate("one-source", sources=("source:a",))],
            policy=_policy(),
            now=datetime(2026, 9, 8, 0, 0, tzinfo=timezone.utc),
        )


def test_selector_rejects_out_of_policy_category() -> None:
    selector = DailyTopicSelector()
    with pytest.raises(DailyTopicSelectionError):
        selector.select(
            [_candidate("sports", category="sports")],
            policy=_policy(),
            now=datetime(2026, 9, 8, 0, 0, tzinfo=timezone.utc),
        )


def test_selector_prefers_best_combined_score() -> None:
    selector = DailyTopicSelector()
    selected = selector.select(
        [
            _candidate("lower", relevance=0.5, advertiser=0.5, freshness=0.9),
            _candidate("higher", relevance=0.9, advertiser=0.9, freshness=0.7),
        ],
        policy=_policy(),
        now=datetime(2026, 9, 8, 0, 0, tzinfo=timezone.utc),
    )
    assert selected.topic_id == "higher"


def test_selector_rejects_recent_topic_id_and_uses_next_candidate() -> None:
    selector = DailyTopicSelector()
    selected = selector.select(
        [
            _candidate("already-published", relevance=1.0, advertiser=1.0, freshness=1.0),
            _candidate("fresh", relevance=0.8, advertiser=0.8, freshness=0.8),
        ],
        policy=_policy(),
        now=datetime(2026, 9, 8, 0, 0, tzinfo=timezone.utc),
        recent_topic_ids=("already-published",),
    )
    assert selected.topic_id == "fresh"


def test_selector_rejects_duplicate_content_fingerprint() -> None:
    selector = DailyTopicSelector()
    previous = _candidate(
        "previous",
        title="Same verified development",
        summary="Same factual summary",
    )
    recycled = _candidate(
        "renamed-id",
        title="Same verified development",
        summary="Same factual summary",
    )
    with pytest.raises(DailyTopicSelectionError):
        selector.select(
            [recycled],
            policy=_policy(),
            now=datetime(2026, 9, 8, 0, 0, tzinfo=timezone.utc),
            recent_content_fingerprints=(previous.content_fingerprint,),
        )
