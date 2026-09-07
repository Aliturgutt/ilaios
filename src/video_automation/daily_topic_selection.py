"""Deterministic daily topic selection for governed Video Factory automation.

This module is provider-neutral. External news/trend integrations map their
observations into ``DailyTopicCandidate`` objects. Selection never treats one
provider as truth: candidates must carry independent source references before
they can be admitted.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterable


class DailyTopicSelectionError(ValueError):
    """Raised when a daily topic cannot be selected safely."""


@dataclass(frozen=True, slots=True)
class DailyTopicCandidate:
    topic_id: str
    title: str
    summary: str
    category: str
    published_at: datetime
    independent_source_refs: tuple[str, ...]
    relevance_score: float
    advertiser_value_score: float
    freshness_score: float

    def __post_init__(self) -> None:
        for name in ("topic_id", "title", "summary", "category"):
            value = getattr(self, name)
            if not value or value != value.strip():
                raise DailyTopicSelectionError(f"{name} must be normalized non-blank text")
        if self.published_at.tzinfo is None:
            raise DailyTopicSelectionError("published_at must be timezone-aware")
        refs = tuple(ref.strip() for ref in self.independent_source_refs)
        if any(not ref for ref in refs) or len(refs) != len(set(refs)):
            raise DailyTopicSelectionError("independent_source_refs must be unique and non-blank")
        object.__setattr__(self, "independent_source_refs", refs)
        for name in ("relevance_score", "advertiser_value_score", "freshness_score"):
            score = float(getattr(self, name))
            if score < 0.0 or score > 1.0:
                raise DailyTopicSelectionError(f"{name} must be between 0 and 1")

    @property
    def combined_score(self) -> float:
        return (
            self.relevance_score * 0.50
            + self.advertiser_value_score * 0.30
            + self.freshness_score * 0.20
        )


@dataclass(frozen=True, slots=True)
class DailyChannelPolicy:
    allowed_categories: tuple[str, ...]
    blocked_terms: tuple[str, ...] = ()
    minimum_independent_sources: int = 2
    maximum_age_hours: int = 72

    def __post_init__(self) -> None:
        categories = tuple(item.strip().lower() for item in self.allowed_categories)
        blocked = tuple(item.strip().lower() for item in self.blocked_terms)
        if not categories or any(not item for item in categories):
            raise DailyTopicSelectionError("allowed_categories must not be empty")
        if len(categories) != len(set(categories)):
            raise DailyTopicSelectionError("allowed_categories must be unique")
        if any(not item for item in blocked) or len(blocked) != len(set(blocked)):
            raise DailyTopicSelectionError("blocked_terms must be unique normalized text")
        if self.minimum_independent_sources < 2:
            raise DailyTopicSelectionError("minimum_independent_sources must be at least 2")
        if self.maximum_age_hours <= 0:
            raise DailyTopicSelectionError("maximum_age_hours must be positive")
        object.__setattr__(self, "allowed_categories", categories)
        object.__setattr__(self, "blocked_terms", blocked)


class DailyTopicSelector:
    """Select one bounded topic while failing closed on weak evidence."""

    def select(
        self,
        candidates: Iterable[DailyTopicCandidate],
        *,
        policy: DailyChannelPolicy,
        now: datetime | None = None,
    ) -> DailyTopicCandidate:
        current = now or datetime.now(timezone.utc)
        if current.tzinfo is None:
            raise DailyTopicSelectionError("now must be timezone-aware")
        oldest = current - timedelta(hours=policy.maximum_age_hours)

        admitted: list[DailyTopicCandidate] = []
        for candidate in candidates:
            category = candidate.category.lower()
            if category not in policy.allowed_categories:
                continue
            text = f"{candidate.title} {candidate.summary}".lower()
            if any(term in text for term in policy.blocked_terms):
                continue
            if candidate.published_at < oldest or candidate.published_at > current + timedelta(minutes=5):
                continue
            if len(candidate.independent_source_refs) < policy.minimum_independent_sources:
                continue
            admitted.append(candidate)

        if not admitted:
            raise DailyTopicSelectionError("no topic satisfies channel policy and source verification")

        admitted.sort(
            key=lambda item: (item.combined_score, item.published_at, item.topic_id),
            reverse=True,
        )
        return admitted[0]
