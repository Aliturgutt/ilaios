"""Provider-neutral daily source aggregation and deterministic YouTube metadata planning.

This module is additive to the canonical Video Factory path. It does not call
external providers, schedule work, select accounts, or publish. Provider adapters
supply normalized observations; this layer groups independent sources into topic
candidates and prepares the existing ``PublishingTarget`` contract.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from urllib.parse import urlparse

from .daily_topic_selection import DailyTopicCandidate, DailyTopicSelectionError
from .publishing_package_preparation import PublishingTarget


class DailyYouTubePlanningError(ValueError):
    """Raised when source or metadata planning cannot fail closed safely."""


@dataclass(frozen=True, slots=True)
class DailySourceObservation:
    """One normalized factual observation supplied by an external source adapter."""

    topic_id: str
    title: str
    summary: str
    category: str
    published_at: datetime
    source_url: str
    relevance_score: float
    advertiser_value_score: float
    freshness_score: float

    def __post_init__(self) -> None:
        for name in ("topic_id", "title", "summary", "category", "source_url"):
            value = getattr(self, name)
            if not value or value != value.strip():
                raise DailyYouTubePlanningError(
                    f"{name} must be normalized non-blank text"
                )
        if self.published_at.tzinfo is None or self.published_at.utcoffset() is None:
            raise DailyYouTubePlanningError("published_at must be timezone-aware")
        parsed = urlparse(self.source_url)
        if parsed.scheme != "https" or not parsed.hostname:
            raise DailyYouTubePlanningError(
                "source_url must be an absolute HTTPS URL"
            )
        for name in (
            "relevance_score",
            "advertiser_value_score",
            "freshness_score",
        ):
            score = float(getattr(self, name))
            if score < 0.0 or score > 1.0:
                raise DailyYouTubePlanningError(
                    f"{name} must be between 0 and 1"
                )

    @property
    def source_origin(self) -> str:
        hostname = urlparse(self.source_url).hostname
        if hostname is None:  # guarded in __post_init__
            raise DailyYouTubePlanningError("source_url hostname is unavailable")
        return hostname.lower()


class DailySourceAggregator:
    """Build topic candidates only from genuinely independent source origins."""

    def aggregate(
        self,
        observations: tuple[DailySourceObservation, ...],
    ) -> tuple[DailyTopicCandidate, ...]:
        grouped: dict[str, list[DailySourceObservation]] = {}
        for observation in observations:
            grouped.setdefault(observation.topic_id, []).append(observation)

        candidates: list[DailyTopicCandidate] = []
        for topic_id in sorted(grouped):
            group = grouped[topic_id]
            origins = {item.source_origin for item in group}
            if len(origins) < 2:
                continue
            categories = {item.category.casefold() for item in group}
            if len(categories) != 1:
                continue

            representative = sorted(
                group,
                key=lambda item: (
                    item.relevance_score,
                    item.freshness_score,
                    item.published_at,
                    item.source_url,
                ),
                reverse=True,
            )[0]
            source_urls = tuple(sorted({item.source_url for item in group}))
            material = "|".join(
                (
                    representative.title.casefold().strip(),
                    representative.summary.casefold().strip(),
                )
            )
            candidates.append(
                DailyTopicCandidate(
                    topic_id=topic_id,
                    title=representative.title,
                    summary=representative.summary,
                    category=representative.category,
                    published_at=max(item.published_at for item in group),
                    independent_source_refs=source_urls,
                    relevance_score=max(item.relevance_score for item in group),
                    advertiser_value_score=max(
                        item.advertiser_value_score for item in group
                    ),
                    freshness_score=max(item.freshness_score for item in group),
                    content_fingerprint=sha256(
                        material.encode("utf-8")
                    ).hexdigest(),
                )
            )
        return tuple(candidates)


@dataclass(frozen=True, slots=True)
class YouTubeEditorialPolicy:
    """Channel-bound deterministic metadata policy for one YouTube target."""

    account_id: str
    category_id: str
    default_language: str = "en"
    visibility: str = "private"
    self_declared_made_for_kids: bool = False
    contains_synthetic_media: bool = False

    def __post_init__(self) -> None:
        for name in (
            "account_id",
            "category_id",
            "default_language",
            "visibility",
        ):
            value = getattr(self, name)
            if not value or value != value.strip():
                raise DailyYouTubePlanningError(
                    f"{name} must be normalized non-blank text"
                )
        if not self.category_id.isdigit():
            raise DailyYouTubePlanningError(
                "category_id must be a numeric YouTube category id"
            )
        if self.default_language != "en":
            raise DailyYouTubePlanningError(
                "daily channel metadata language must be English"
            )


def prepare_youtube_target(
    *,
    candidate: DailyTopicCandidate,
    scheduled_at: datetime,
    policy: YouTubeEditorialPolicy,
    title: str,
    description: str,
    hashtags: tuple[str, ...],
    tags: tuple[str, ...],
    thumbnail_path: str,
    thumbnail_sha256: str,
) -> PublishingTarget:
    """Prepare one validated existing PublishingTarget for the canonical publisher."""

    if scheduled_at.tzinfo is None or scheduled_at.utcoffset() is None:
        raise DailyYouTubePlanningError("scheduled_at must be timezone-aware")
    clean_title = title.strip()
    clean_description = description.strip()
    if (
        not clean_title
        or len(clean_title) > 100
        or "<" in clean_title
        or ">" in clean_title
    ):
        raise DailyYouTubePlanningError(
            "YouTube title must be 1-100 characters and exclude angle brackets"
        )
    if not clean_description:
        raise DailyYouTubePlanningError("YouTube description must not be blank")
    if len(hashtags) < 3 or len(hashtags) > 5:
        raise DailyYouTubePlanningError(
            "YouTube description must carry 3-5 hashtags"
        )

    normalized_hashtags: list[str] = []
    seen_hashtags: set[str] = set()
    for hashtag in hashtags:
        value = hashtag.strip()
        if (
            not value.startswith("#")
            or len(value) < 2
            or any(ch.isspace() for ch in value)
        ):
            raise DailyYouTubePlanningError("hashtags must be compact #tokens")
        folded = value.casefold()
        if folded in seen_hashtags:
            raise DailyYouTubePlanningError("hashtags must be unique")
        seen_hashtags.add(folded)
        normalized_hashtags.append(value)

    normalized_tags = tuple(tag.strip().lower() for tag in tags)
    if not normalized_tags or any(not tag for tag in normalized_tags):
        raise DailyYouTubePlanningError("YouTube tags must not be empty")
    if len(normalized_tags) != len(set(normalized_tags)):
        raise DailyYouTubePlanningError("YouTube tags must be unique")
    if any(any(ch.isspace() for ch in tag) for tag in normalized_tags):
        raise DailyYouTubePlanningError(
            "YouTube tags must not contain whitespace"
        )

    if len(candidate.independent_source_refs) < 2:
        raise DailyTopicSelectionError(
            "YouTube factual episode requires at least two source references"
        )
    sources = "\n".join(
        f"- {ref}" for ref in candidate.independent_source_refs
    )
    final_description = (
        f"{clean_description}\n\nSources:\n{sources}\n\n"
        f"{' '.join(normalized_hashtags)}"
    )
    if len(final_description.encode("utf-8")) > 5000:
        raise DailyYouTubePlanningError(
            "YouTube description exceeds the 5000-byte API limit"
        )

    thumb_path = thumbnail_path.strip()
    thumb_sha = thumbnail_sha256.strip().lower()
    if not thumb_path:
        raise DailyYouTubePlanningError("thumbnail_path must not be blank")
    if len(thumb_sha) != 64 or any(
        ch not in "0123456789abcdef" for ch in thumb_sha
    ):
        raise DailyYouTubePlanningError(
            "thumbnail_sha256 must be a lowercase SHA-256 digest"
        )

    return PublishingTarget(
        platform="youtube",
        account_id=policy.account_id,
        scheduled_at=scheduled_at,
        visibility=policy.visibility,
        title=clean_title,
        description=final_description,
        tags=normalized_tags,
        metadata={
            "youtube_category_id": policy.category_id,
            "youtube_default_language": policy.default_language,
            "youtube_self_declared_made_for_kids": str(
                policy.self_declared_made_for_kids
            ).lower(),
            "youtube_contains_synthetic_media": str(
                policy.contains_synthetic_media
            ).lower(),
            "youtube_thumbnail_path": thumb_path,
            "youtube_thumbnail_sha256": thumb_sha,
            "daily_topic_id": candidate.topic_id,
            "daily_content_fingerprint": candidate.content_fingerprint,
            "daily_source_count": str(len(candidate.independent_source_refs)),
        },
    )
