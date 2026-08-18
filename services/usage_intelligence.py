"""Read-only, fail-closed usage intelligence over authoritative ILAIOS projections.

This module does not authorize work, meter billing, admit evidence, or inspect
prompt/output content. It derives bounded usage summaries only from existing
runtime-route metadata, governance state, and verified-evidence counts.
"""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Iterable, Mapping
from datetime import datetime, timezone
from typing import cast


class UsageIntelligenceError(ValueError):
    """Authoritative usage source data cannot be projected safely."""


def project_usage_stats(
    routes: Iterable[Mapping[str, object]],
    governance_state: Mapping[str, object],
    *,
    evidence_count: int,
) -> dict[str, object]:
    """Build a privacy-minimized local usage projection.

    The scope is intentionally the authenticated local control-plane instance.
    Token, latency, and model-level usage remain unavailable until an
    authoritative source is wired; this projector never infers them.
    """

    if isinstance(evidence_count, bool) or evidence_count < 0:
        raise UsageIntelligenceError("evidence_count must be non-negative")

    normalized_routes = tuple(_route_metadata(route) for route in routes)
    timestamps = tuple(item["created_at"] for item in normalized_routes)
    dates = tuple(sorted({stamp.date() for stamp in timestamps}))

    providers = Counter(item["provider_id"] for item in normalized_routes)
    skills = Counter(item["skill_id"] for item in normalized_routes)
    capabilities = Counter(item["capability"] for item in normalized_routes)
    agents = Counter(item["agent_id"] for item in normalized_routes)
    hours = Counter(stamp.hour for stamp in timestamps)
    activity = Counter(stamp.date().isoformat() for stamp in timestamps)

    status_counts = _governance_status_counts(governance_state)
    cost_projection = _explicit_cost_projection(governance_state)

    return {
        "schema_version": "ilaios.usage-stats.v1",
        "scope": "local_authenticated_control_plane",
        "time_zone": "UTC",
        "route_count": len(normalized_routes),
        "unique_agent_count": len(agents),
        "unique_skill_count": len(skills),
        "unique_provider_count": len(providers),
        "unique_capability_count": len(capabilities),
        "active_days": len(dates),
        "latest_streak_days": _latest_streak_days(dates),
        "longest_streak_days": _longest_streak_days(dates),
        "latest_activity_at": (
            max(timestamps).isoformat() if timestamps else None
        ),
        "peak_execution_hour_utc": _peak_hour(hours),
        "activity_by_date": _count_rows(activity),
        "provider_distribution": _count_rows(providers),
        "skill_distribution": _count_rows(skills),
        "capability_distribution": _count_rows(capabilities),
        "governance_status_counts": _count_rows(status_counts),
        "verified_evidence_count": evidence_count,
        "costs": cost_projection,
        "coverage": {
            "runtime_routes": "authoritative_route_metadata",
            "governance": "authoritative_governance_state",
            "evidence": "verified_evidence_count",
            "costs": cost_projection["coverage"],
            "tokens": "unavailable",
            "latency": "unavailable",
            "models": "unavailable",
        },
    }


def _route_metadata(route: Mapping[str, object]) -> dict[str, object]:
    required = ("agent_id", "skill_id", "provider_id", "capability", "created_at")
    values: dict[str, str] = {}
    for field in required:
        raw = route.get(field)
        if not isinstance(raw, str) or not raw or raw != raw.strip():
            raise UsageIntelligenceError(f"runtime route {field} is malformed")
        values[field] = raw
    try:
        created_at = datetime.fromisoformat(values["created_at"])
    except ValueError as error:
        raise UsageIntelligenceError("runtime route created_at is malformed") from error
    if created_at.tzinfo is None:
        raise UsageIntelligenceError("runtime route created_at must be timezone-aware")
    return {
        "agent_id": values["agent_id"],
        "skill_id": values["skill_id"],
        "provider_id": values["provider_id"],
        "capability": values["capability"],
        "created_at": created_at.astimezone(timezone.utc),
    }


def _governance_status_counts(state: Mapping[str, object]) -> Counter[str]:
    raw_work = state.get("work")
    if raw_work is None:
        return Counter()
    if not isinstance(raw_work, list):
        raise UsageIntelligenceError("governance work projection is malformed")
    counts: Counter[str] = Counter()
    for item in raw_work:
        if not isinstance(item, Mapping):
            raise UsageIntelligenceError("governance work projection is malformed")
        status = item.get("status")
        if not isinstance(status, str) or not status or status != status.strip():
            raise UsageIntelligenceError("governance work status is malformed")
        counts[status] += 1
    return counts


def _explicit_cost_projection(state: Mapping[str, object]) -> dict[str, object]:
    raw = state.get("costs")
    if raw is None:
        return {"coverage": "unavailable", "currency": None, "total_cost": None}
    if not isinstance(raw, Mapping):
        raise UsageIntelligenceError("cost projection is malformed")

    currency = raw.get("currency")
    coverage = raw.get("coverage")
    if currency != "USD" or coverage != "explicit_currency_only":
        raise UsageIntelligenceError("cost projection lacks explicit USD semantics")

    total = raw.get("total_cost_usd")
    if total is None:
        value: float | None = None
    elif isinstance(total, bool) or not isinstance(total, (int, float)):
        raise UsageIntelligenceError("total_cost_usd is malformed")
    else:
        value = float(total)
        if not math.isfinite(value) or value < 0:
            raise UsageIntelligenceError("total_cost_usd is malformed")

    records = raw.get("records", [])
    if not isinstance(records, list):
        raise UsageIntelligenceError("cost records projection is malformed")

    return {
        "coverage": "explicit_currency_only",
        "currency": "USD",
        "total_cost": value,
        "record_count": len(records),
    }


def _count_rows(counter: Mapping[object, int]) -> list[dict[str, object]]:
    items = sorted(
        ((str(key), value) for key, value in counter.items()),
        key=lambda item: (-item[1], item[0]),
    )
    return [{"key": key, "count": count} for key, count in items]


def _peak_hour(hours: Mapping[int, int]) -> int | None:
    if not hours:
        return None
    maximum = max(hours.values())
    return min(hour for hour, count in hours.items() if count == maximum)


def _latest_streak_days(dates: tuple[object, ...]) -> int:
    if not dates:
        return 0
    typed = cast(tuple[datetime.date, ...], dates)
    streak = 1
    for index in range(len(typed) - 1, 0, -1):
        if (typed[index] - typed[index - 1]).days != 1:
            break
        streak += 1
    return streak


def _longest_streak_days(dates: tuple[object, ...]) -> int:
    if not dates:
        return 0
    typed = cast(tuple[datetime.date, ...], dates)
    longest = current = 1
    for previous, current_date in zip(typed, typed[1:], strict=False):
        if (current_date - previous).days == 1:
            current += 1
            longest = max(longest, current)
        else:
            current = 1
    return longest
