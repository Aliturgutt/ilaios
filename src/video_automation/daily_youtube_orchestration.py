"""One daily Video Factory trigger path over existing execution/publication authorities.

This module does not implement a scheduler, Video runtime, publisher, retry loop,
or publication ledger. A platform scheduler may invoke ``run_once`` once per
scheduled window; the method reuses the canonical Video execution callback,
PublishingPackagePreparer, DurablePublishingCoordinator, OAuth-bound publisher,
and durable publication ledger semantics.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Protocol

from .daily_topic_selection import (
    DailyChannelPolicy,
    DailyTopicCandidate,
    DailyTopicSelectionError,
    DailyTopicSelector,
)
from .daily_youtube_planning import (
    DailySourceAggregator,
    DailySourceObservation,
    YouTubeEditorialPolicy,
    prepare_youtube_target,
)
from .episode_assembly_execution import EpisodeAssemblyArtifact
from .final_episode_acceptance import FinalEpisodeAcceptanceDecision
from .finished_product import FinishedVideoProduct
from .guarded_publishing import (
    DurablePublishingCoordinator,
    GuardedPublicationResult,
    PublicationAuthorityAwarePublisher,
    PublicationAuthorization,
)
from .publishing_execution import PublishingExecutionStatus
from .publishing_package_preparation import PublishingPackagePreparer


class DailyYouTubeOrchestrationError(RuntimeError):
    """Raised when canonical daily Video publication cannot advance safely."""


@dataclass(frozen=True, slots=True)
class DailyEpisodeEditorial:
    title: str
    description: str
    hashtags: tuple[str, ...]
    tags: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CanonicalDailyVideoExecution:
    """Accepted outputs returned by the existing canonical Video execution path."""

    artifact: EpisodeAssemblyArtifact
    acceptance: FinalEpisodeAcceptanceDecision
    product: FinishedVideoProduct
    thumbnail_path: str
    thumbnail_sha256: str

    def __post_init__(self) -> None:
        if self.product.final_sha256 != self.artifact.sha256_hex:
            raise DailyYouTubeOrchestrationError(
                "finished product SHA does not match canonical assembly artifact"
            )
        if self.product.thumbnail_sha256 != self.thumbnail_sha256:
            raise DailyYouTubeOrchestrationError(
                "thumbnail SHA does not match finished-product evidence"
            )
        if not self.thumbnail_path.strip():
            raise DailyYouTubeOrchestrationError(
                "canonical Video execution must return a thumbnail path"
            )


class CanonicalDailyVideoExecutor(Protocol):
    """Adapter to the existing Video generation/QA authority, not a new runtime."""

    def execute(self, candidate: DailyTopicCandidate) -> CanonicalDailyVideoExecution:
        ...


class DailyEditorialPlanner(Protocol):
    """Channel-bound editorial planner; factual claims remain source-bound."""

    def plan(self, candidate: DailyTopicCandidate) -> DailyEpisodeEditorial:
        ...


class DurableDailyVideoHistory:
    """Caller-owned durable dedupe history for successful daily publications."""

    def __init__(self, database_path: str | Path) -> None:
        self._database_path = Path(database_path)
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self._database_path) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS daily_video_history (
                    topic_id TEXT PRIMARY KEY,
                    content_fingerprint TEXT NOT NULL UNIQUE,
                    final_product_sha256 TEXT NOT NULL,
                    published_at TEXT NOT NULL
                )
                """
            )

    def recent_topic_ids(self) -> tuple[str, ...]:
        with sqlite3.connect(self._database_path) as connection:
            rows = connection.execute(
                "SELECT topic_id FROM daily_video_history ORDER BY published_at DESC, topic_id"
            ).fetchall()
        return tuple(str(row[0]) for row in rows)

    def recent_content_fingerprints(self) -> tuple[str, ...]:
        with sqlite3.connect(self._database_path) as connection:
            rows = connection.execute(
                "SELECT content_fingerprint FROM daily_video_history "
                "ORDER BY published_at DESC, content_fingerprint"
            ).fetchall()
        return tuple(str(row[0]) for row in rows)

    def record_success(
        self,
        candidate: DailyTopicCandidate,
        *,
        final_product_sha256: str,
        published_at: datetime,
    ) -> None:
        if len(final_product_sha256) != 64 or any(
            character not in "0123456789abcdef" for character in final_product_sha256
        ):
            raise DailyYouTubeOrchestrationError(
                "daily history final product SHA must be lowercase SHA-256"
            )
        if published_at.tzinfo is None or published_at.utcoffset() is None:
            raise DailyYouTubeOrchestrationError(
                "daily history published_at must be timezone-aware"
            )
        with sqlite3.connect(self._database_path) as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO daily_video_history (
                    topic_id, content_fingerprint, final_product_sha256, published_at
                ) VALUES (?, ?, ?, ?)
                """,
                (
                    candidate.topic_id,
                    candidate.content_fingerprint,
                    final_product_sha256,
                    published_at.isoformat(),
                ),
            )


class DailyYouTubeOrchestrator:
    """Run one idempotent daily attempt through canonical Video authorities."""

    def __init__(
        self,
        *,
        executor: CanonicalDailyVideoExecutor,
        editorial_planner: DailyEditorialPlanner,
        publishing_coordinator: DurablePublishingCoordinator,
        publisher: PublicationAuthorityAwarePublisher,
        authorization: PublicationAuthorization,
        package_preparer: PublishingPackagePreparer | None = None,
        source_aggregator: DailySourceAggregator | None = None,
        topic_selector: DailyTopicSelector | None = None,
        history: DurableDailyVideoHistory | None = None,
    ) -> None:
        self._executor = executor
        self._editorial_planner = editorial_planner
        self._publishing_coordinator = publishing_coordinator
        self._publisher = publisher
        self._authorization = authorization
        self._package_preparer = package_preparer or PublishingPackagePreparer()
        self._source_aggregator = source_aggregator or DailySourceAggregator()
        self._topic_selector = topic_selector or DailyTopicSelector()
        self._history = history

    def run_once(
        self,
        *,
        observations: tuple[DailySourceObservation, ...],
        channel_policy: DailyChannelPolicy,
        youtube_policy: YouTubeEditorialPolicy,
        scheduled_at: datetime,
        recent_topic_ids: tuple[str, ...] = (),
        recent_content_fingerprints: tuple[str, ...] = (),
        now: datetime | None = None,
    ) -> GuardedPublicationResult | None:
        """Publish one accepted episode, or return ``None`` when no topic qualifies."""

        candidates = self._source_aggregator.aggregate(observations)
        durable_topic_ids: tuple[str, ...] = ()
        durable_fingerprints: tuple[str, ...] = ()
        if self._history is not None:
            durable_topic_ids = self._history.recent_topic_ids()
            durable_fingerprints = self._history.recent_content_fingerprints()
        try:
            candidate = self._topic_selector.select(
                candidates,
                policy=channel_policy,
                now=now,
                recent_topic_ids=(*recent_topic_ids, *durable_topic_ids),
                recent_content_fingerprints=(
                    *recent_content_fingerprints,
                    *durable_fingerprints,
                ),
            )
        except DailyTopicSelectionError:
            return None

        execution = self._executor.execute(candidate)
        editorial = self._editorial_planner.plan(candidate)
        target = prepare_youtube_target(
            candidate=candidate,
            scheduled_at=scheduled_at,
            policy=youtube_policy,
            title=editorial.title,
            description=editorial.description,
            hashtags=editorial.hashtags,
            tags=editorial.tags,
            thumbnail_path=execution.thumbnail_path,
            thumbnail_sha256=execution.thumbnail_sha256,
        )
        manifest = self._package_preparer.prepare(
            execution.artifact,
            execution.acceptance,
            (target,),
        )
        if manifest.package_count != 1 or manifest.packages[0].platform != "youtube":
            raise DailyYouTubeOrchestrationError(
                "daily YouTube trigger produced an invalid publishing manifest"
            )
        result = self._publishing_coordinator.publish(
            package=manifest.packages[0],
            product=execution.product,
            authorization=self._authorization,
            publisher=self._publisher,
        )
        if (
            self._history is not None
            and result.observation.status is PublishingExecutionStatus.SUCCEEDED
        ):
            self._history.record_success(
                candidate,
                final_product_sha256=execution.product.final_sha256,
                published_at=now or scheduled_at,
            )
        return result
