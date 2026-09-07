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
) -> DailyTopicCandidate:
    now = datetime(2026, 9, 8, 0, 0, tzinfo=timezone.utc)
    return DailyTopicCandidate(
        topic_id=topic_id,
        title=f"Topic {topic_id}",
        summary="Verified technology development",
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
