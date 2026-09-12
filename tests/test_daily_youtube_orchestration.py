from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timezone
from typing import cast

from src.video_automation.daily_topic_selection import (
    DailyChannelPolicy,
    DailyTopicCandidate,
    DailyTopicSelectionError,
    DailyTopicSelector,
)
from src.video_automation.daily_youtube_orchestration import (
    CanonicalDailyVideoExecutor,
    DailyEditorialPlanner,
    DailyYouTubeOrchestrator,
    DurableDailyVideoHistory,
)
from src.video_automation.daily_youtube_planning import (
    DailySourceObservation,
    YouTubeEditorialPolicy,
)
from src.video_automation.guarded_publishing import (
    DurablePublishingCoordinator,
    PublicationAuthorityAwarePublisher,
    PublicationAuthorization,
)


class _RejectingSelector(DailyTopicSelector):
    def __init__(self) -> None:
        self.recent_topic_ids: tuple[str, ...] = ()
        self.recent_content_fingerprints: tuple[str, ...] = ()

    def select(
        self,
        candidates: Iterable[DailyTopicCandidate],
        *,
        policy: DailyChannelPolicy,
        now: datetime | None = None,
        recent_topic_ids: Iterable[str] = (),
        recent_content_fingerprints: Iterable[str] = (),
    ) -> DailyTopicCandidate:
        del candidates, policy, now
        self.recent_topic_ids = tuple(recent_topic_ids)
        self.recent_content_fingerprints = tuple(recent_content_fingerprints)
        raise DailyTopicSelectionError("bounded test stop")


def _candidate() -> DailyTopicCandidate:
    return DailyTopicCandidate(
        topic_id="topic-001",
        title="Verified topic",
        summary="Two independent sources confirm the same bounded event.",
        category="technology",
        published_at=datetime(2026, 9, 12, 8, 0, tzinfo=timezone.utc),
        independent_source_refs=(
            "https://source-a.example/report",
            "https://source-b.example/report",
        ),
        relevance_score=0.9,
        advertiser_value_score=0.8,
        freshness_score=0.95,
    )


def _observations() -> tuple[DailySourceObservation, ...]:
    common = {
        "topic_id": "topic-002",
        "title": "Another verified topic",
        "summary": "Independent reports describe the same current event.",
        "category": "technology",
        "published_at": datetime(2026, 9, 12, 9, 0, tzinfo=timezone.utc),
        "relevance_score": 0.9,
        "advertiser_value_score": 0.8,
        "freshness_score": 0.95,
    }
    return (
        DailySourceObservation(source_url="https://one.example/report", **common),
        DailySourceObservation(source_url="https://two.example/report", **common),
    )


def test_durable_daily_history_round_trips_successful_topic_and_fingerprint(tmp_path) -> None:
    history = DurableDailyVideoHistory(tmp_path / "daily.sqlite3")
    candidate = _candidate()

    history.record_success(
        candidate,
        final_product_sha256="a" * 64,
        published_at=datetime(2026, 9, 12, 10, 0, tzinfo=timezone.utc),
    )
    history.record_success(
        candidate,
        final_product_sha256="a" * 64,
        published_at=datetime(2026, 9, 12, 10, 0, tzinfo=timezone.utc),
    )

    assert history.recent_topic_ids() == ("topic-001",)
    assert history.recent_content_fingerprints() == (candidate.content_fingerprint,)


def test_orchestrator_supplies_durable_history_to_topic_selector(tmp_path) -> None:
    history = DurableDailyVideoHistory(tmp_path / "daily.sqlite3")
    prior = _candidate()
    history.record_success(
        prior,
        final_product_sha256="b" * 64,
        published_at=datetime(2026, 9, 12, 10, 0, tzinfo=timezone.utc),
    )
    selector = _RejectingSelector()
    orchestrator = DailyYouTubeOrchestrator(
        executor=cast(CanonicalDailyVideoExecutor, object()),
        editorial_planner=cast(DailyEditorialPlanner, object()),
        publishing_coordinator=cast(DurablePublishingCoordinator, object()),
        publisher=cast(PublicationAuthorityAwarePublisher, object()),
        authorization=PublicationAuthorization(
            platform="youtube",
            account_id="channel-001",
            oauth_authorization_ref="oauth://youtube/channel-001",
            scopes=("youtube.upload",),
        ),
        topic_selector=selector,
        history=history,
    )

    result = orchestrator.run_once(
        observations=_observations(),
        channel_policy=DailyChannelPolicy(allowed_categories=("technology",)),
        youtube_policy=YouTubeEditorialPolicy(
            account_id="channel-001",
            category_id="28",
        ),
        scheduled_at=datetime(2026, 9, 12, 11, 0, tzinfo=timezone.utc),
        recent_topic_ids=("caller-topic",),
        recent_content_fingerprints=("c" * 64,),
        now=datetime(2026, 9, 12, 11, 0, tzinfo=timezone.utc),
    )

    assert result is None
    assert selector.recent_topic_ids == ("caller-topic", "topic-001")
    assert selector.recent_content_fingerprints == (
        "c" * 64,
        prior.content_fingerprint,
    )
