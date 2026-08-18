"""Read-only, fail-closed usage intelligence over authoritative ILAIOS projections.

This module does not authorize work, meter billing, admit evidence, or expose
prompt/output content. It derives bounded usage summaries only from existing
runtime-route metadata, allow-listed numeric/provider diagnostics, governance
state, and verified-evidence counts.
"""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date, datetime, timezone


class UsageIntelligenceError(ValueError):
    """Authoritative usage source data cannot be projected safely."""


@dataclass(frozen=True, slots=True)
class _RouteMetadata:
    agent_id: str
    skill_id: str
    provider_id: str
    capability: str
    created_at: datetime
    model_id: str | None
    input_tokens: int | None
    output_tokens: int | None
    latency_ms: int | None


def project_usage_stats(
    routes: Iterable[Mapping[str, object]],
    governance_state: Mapping[str, object],
    *,
    evidence_count: int | None = None,
) -> dict[str, object]:
    """Build a privacy-minimized local usage projection.

    Scope is intentionally the authenticated local control-plane instance.
    Provider diagnostics are projected only when explicit allow-listed fields
    are present in authoritative runtime output; unavailable data is never
    inferred.
    """

    if evidence_count is not None and (
        isinstance(evidence_count, bool) or evidence_count < 0
    ):
        raise UsageIntelligenceError("evidence_count must be non-negative")

    normalized_routes = tuple(_route_metadata(route) for route in routes)
    timestamps = tuple(item.created_at for item in normalized_routes)
    dates = tuple(sorted({stamp.date() for stamp in timestamps}))

    providers = Counter(item.provider_id for item in normalized_routes)
    skills = Counter(item.skill_id for item in normalized_routes)
    capabilities = Counter(item.capability for item in normalized_routes)
    agents = Counter(item.agent_id for item in normalized_routes)
    hours = Counter(stamp.hour for stamp in timestamps)
    activity = Counter(stamp.date().isoformat() for stamp in timestamps)
    models = Counter(
        item.model_id for item in normalized_routes if item.model_id is not None
    )

    token_rows = tuple(
        item
        for item in normalized_routes
        if item.input_tokens is not None and item.output_tokens is not None
    )
    latency_rows = tuple(
        item.latency_ms for item in normalized_routes if item.latency_ms is not None
    )
    token_usage = _token_usage(token_rows)
    latency = _latency_summary(latency_rows)
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
        "latest_activity_at": max(timestamps).isoformat() if timestamps else None,
        "peak_execution_hour_utc": _peak_hour(hours),
        "activity_by_date": _count_rows(activity),
        "provider_distribution": _count_rows(providers),
        "skill_distribution": _count_rows(skills),
        "capability_distribution": _count_rows(capabilities),
        "model_distribution": _count_rows(models),
        "governance_status_counts": _count_rows(status_counts),
        "token_usage": token_usage,
        "latency": latency,
        "verified_evidence_count": evidence_count,
        "costs": cost_projection,
        "coverage": {
            "runtime_routes": "authoritative_route_metadata",
            "governance": "authoritative_governance_state",
            "evidence": (
                "verified_evidence_count" if evidence_count is not None else "unavailable"
            ),
            "costs": cost_projection["coverage"],
            "tokens": (
                "authoritative_provider_output_partial" if token_rows else "unavailable"
            ),
            "latency": (
                "authoritative_provider_output_partial" if latency_rows else "unavailable"
            ),
            "models": (
                "authoritative_provider_output_partial" if models else "unavailable"
            ),
        },
    }


def _route_metadata(route: Mapping[str, object]) -> _RouteMetadata:
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

    raw_output = route.get("output")
    if raw_output is None:
        output: Mapping[str, object] = {}
    elif isinstance(raw_output, Mapping):
        output = raw_output
    else:
        raise UsageIntelligenceError("runtime route output is malformed")

    model_id = _optional_trimmed_text(output, "model_id")
    input_tokens = _optional_nonnegative_int(output, "input_tokens")
    output_tokens = _optional_nonnegative_int(output, "output_tokens")
    if (input_tokens is None) != (output_tokens is None):
        raise UsageIntelligenceError("runtime route token usage is incomplete")
    latency_ms = _optional_nonnegative_int(output, "latency_ms")

    return _RouteMetadata(
        values["agent_id"],
        values["skill_id"],
        values["provider_id"],
        values["capability"],
        created_at.astimezone(timezone.utc),
        model_id,
        input_tokens,
        output_tokens,
        latency_ms,
    )


def _optional_trimmed_text(output: Mapping[str, object], field: str) -> str | None:
    raw = output.get(field)
    if raw is None:
        return None
    if not isinstance(raw, str) or not raw or raw != raw.strip():
        raise UsageIntelligenceError(f"runtime route {field} is malformed")
    return raw


def _optional_nonnegative_int(output: Mapping[str, object], field: str) -> int | None:
    raw = output.get(field)
    if raw is None:
        return None
    if isinstance(raw, bool) or not isinstance(raw, int) or raw < 0:
        raise UsageIntelligenceError(f"runtime route {field} is malformed")
    return raw


def _token_usage(rows: tuple[_RouteMetadata, ...]) -> dict[str, object] | None:
    if not rows:
        return None
    input_tokens = sum(item.input_tokens or 0 for item in rows)
    output_tokens = sum(item.output_tokens or 0 for item in rows)
    return {
        "route_count": len(rows),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
    }


def _latency_summary(values: tuple[int, ...]) -> dict[str, object] | None:
    if not values:
        return None
    return {
        "sample_count": len(values),
        "average_ms": round(sum(values) / len(values), 2),
        "min_ms": min(values),
        "max_ms": max(values),
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


def _count_rows(counter: Mapping[str, int]) -> list[dict[str, object]]:
    items = sorted(counter.items(), key=lambda item: (-item[1], item[0]))
    return [{"key": key, "count": count} for key, count in items]


def _peak_hour(hours: Mapping[int, int]) -> int | None:
    if not hours:
        return None
    maximum = max(hours.values())
    return min(hour for hour, count in hours.items() if count == maximum)


def _latest_streak_days(dates: tuple[date, ...]) -> int:
    if not dates:
        return 0
    streak = 1
    for index in range(len(dates) - 1, 0, -1):
        if (dates[index] - dates[index - 1]).days != 1:
            break
        streak += 1
    return streak


def _longest_streak_days(dates: tuple[date, ...]) -> int:
    if not dates:
        return 0
    longest = current = 1
    for previous, current_date in zip(dates, dates[1:], strict=False):
        if (current_date - previous).days == 1:
            current += 1
            longest = max(longest, current)
        else:
            current = 1
    return longest
