"""Bounded Commerce/Growth Factory for deterministic review-only growth proposals."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import TypedDict


class CommerceGrowthError(PermissionError):
    """Commerce/growth work violates a bounded governance or cost gate."""


_ALLOWED_CHANNELS = frozenset(
    {
        "content_draft",
        "email_draft",
        "sales_enablement",
        "social_draft",
    }
)


class GrowthSourceProjection(TypedDict):
    source_id: str
    locator: str
    content_sha256: str


class GrowthReviewProjection(TypedDict):
    plan_id: str
    objective: str
    audience: str
    channels: tuple[str, ...]
    plan_sha256: str
    approved_for_review: bool
    approver: str
    paid_spend_cents: int
    sources: tuple[GrowthSourceProjection, ...]


@dataclass(frozen=True, slots=True)
class GrowthSource:
    source_id: str
    locator: str
    content_sha256: str
    trusted: bool


@dataclass(frozen=True, slots=True)
class GrowthPlan:
    plan_id: str
    objective: str
    audience: str
    channels: tuple[str, ...]
    source_ids: tuple[str, ...]
    paid_spend_cents: int
    plan_sha256: str
    approved_for_review: bool
    approver: str | None
    external_applied: bool = False


class CommerceGrowthFactory:
    """Produce bounded growth proposals without billing, publishing or external mutation."""

    def __init__(self) -> None:
        self._sources: dict[str, GrowthSource] = {}
        self._plans: dict[str, GrowthPlan] = {}

    def register_source(
        self,
        source_id: str,
        *,
        locator: str,
        content: bytes,
        trusted: bool,
    ) -> GrowthSource:
        _require_id(source_id, "source_id")
        _require_text(locator, "locator")
        if not content:
            raise CommerceGrowthError("source content must not be empty")
        if source_id in self._sources:
            raise CommerceGrowthError("source_id already exists")
        source = GrowthSource(
            source_id=source_id,
            locator=locator,
            content_sha256=hashlib.sha256(content).hexdigest(),
            trusted=trusted,
        )
        self._sources[source_id] = source
        return source

    def propose(
        self,
        plan_id: str,
        *,
        objective: str,
        audience: str,
        channels: tuple[str, ...],
        source_ids: tuple[str, ...],
        paid_spend_cents: int = 0,
    ) -> GrowthPlan:
        _require_id(plan_id, "plan_id")
        _require_text(objective, "objective")
        _require_text(audience, "audience")
        if plan_id in self._plans:
            raise CommerceGrowthError("plan_id already exists")
        if paid_spend_cents != 0:
            raise CommerceGrowthError("paid spend is outside the bounded factory")
        normalized_channels = _unique_ids(channels, "channels")
        unsupported = sorted(set(normalized_channels) - _ALLOWED_CHANNELS)
        if unsupported:
            raise CommerceGrowthError(f"unsupported growth channels: {unsupported}")
        normalized_sources = _unique_ids(source_ids, "source_ids")
        missing = [source_id for source_id in normalized_sources if source_id not in self._sources]
        if missing:
            raise CommerceGrowthError(f"plan references unknown sources: {missing}")
        if any(not self._sources[source_id].trusted for source_id in normalized_sources):
            raise CommerceGrowthError("growth plan sources must be trusted")

        canonical = json.dumps(
            {
                "audience": audience.strip(),
                "channels": normalized_channels,
                "objective": objective.strip(),
                "paid_spend_cents": paid_spend_cents,
                "sources": tuple(
                    {
                        "content_sha256": self._sources[source_id].content_sha256,
                        "source_id": source_id,
                    }
                    for source_id in normalized_sources
                ),
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        plan = GrowthPlan(
            plan_id=plan_id,
            objective=objective.strip(),
            audience=audience.strip(),
            channels=normalized_channels,
            source_ids=normalized_sources,
            paid_spend_cents=paid_spend_cents,
            plan_sha256=hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
            approved_for_review=False,
            approver=None,
        )
        self._plans[plan_id] = plan
        return plan

    def approve_for_review(self, plan_id: str, *, approver: str) -> GrowthPlan:
        _require_text(approver, "approver")
        plan = self._plans.get(plan_id)
        if plan is None:
            raise CommerceGrowthError("growth plan does not exist")
        if plan.approved_for_review:
            raise CommerceGrowthError("growth plan already approved for review")
        approved = GrowthPlan(
            plan_id=plan.plan_id,
            objective=plan.objective,
            audience=plan.audience,
            channels=plan.channels,
            source_ids=plan.source_ids,
            paid_spend_cents=plan.paid_spend_cents,
            plan_sha256=plan.plan_sha256,
            approved_for_review=True,
            approver=approver.strip(),
        )
        self._plans[plan_id] = approved
        return approved

    def review_projection(self, plan_id: str) -> GrowthReviewProjection:
        plan = self._plans.get(plan_id)
        if plan is None:
            raise CommerceGrowthError("growth plan does not exist")
        if not plan.approved_for_review or plan.approver is None:
            raise CommerceGrowthError("only approved growth plans may project for review")
        return {
            "plan_id": plan.plan_id,
            "objective": plan.objective,
            "audience": plan.audience,
            "channels": plan.channels,
            "plan_sha256": plan.plan_sha256,
            "approved_for_review": True,
            "approver": plan.approver,
            "paid_spend_cents": plan.paid_spend_cents,
            "sources": tuple(
                {
                    "source_id": source_id,
                    "locator": self._sources[source_id].locator,
                    "content_sha256": self._sources[source_id].content_sha256,
                }
                for source_id in plan.source_ids
            ),
        }

    def apply_external(self, plan_id: str) -> None:
        if plan_id not in self._plans:
            raise CommerceGrowthError("growth plan does not exist")
        raise CommerceGrowthError("external commerce/growth mutation is forbidden")


def _require_id(value: str, field: str) -> None:
    if not value or value != value.strip():
        raise CommerceGrowthError(f"{field} must be non-blank and trimmed")


def _require_text(value: str, field: str) -> None:
    if not value or not value.strip():
        raise CommerceGrowthError(f"{field} must be non-blank")


def _unique_ids(values: tuple[str, ...], field: str) -> tuple[str, ...]:
    if not values:
        raise CommerceGrowthError(f"{field} must not be empty")
    if any(not item or item != item.strip() for item in values):
        raise CommerceGrowthError(f"{field} must contain trimmed values")
    if len(values) != len(set(values)):
        raise CommerceGrowthError(f"{field} must not contain duplicates")
    return values
