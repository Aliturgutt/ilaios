import json

import pytest

from services.usage_intelligence import (
    UsageIntelligenceError,
    project_usage_stats,
)


def _route(
    created_at: str,
    *,
    provider: str = "provider-a",
    skill: str = "skill-a",
    capability: str = "web.generate",
    agent: str = "agent-a",
) -> dict[str, object]:
    return {
        "sequence": 1,
        "agent_id": agent,
        "skill_id": skill,
        "provider_id": provider,
        "capability": capability,
        "input_sha256": "0" * 64,
        "created_at": created_at,
        "output": {"sensitive_payload": "must-not-project"},
    }


def _governance() -> dict[str, object]:
    return {
        "work": [
            {"request_id": "r1", "requester_id": "alice", "status": "executed"},
            {"request_id": "r2", "requester_id": "bob", "status": "executed"},
            {"request_id": "r3", "requester_id": "alice", "status": "failed"},
        ],
        "costs": {
            "currency": "USD",
            "coverage": "explicit_currency_only",
            "records": [{"request_id": "r1", "amount_usd": 1.25}],
            "total_cost_usd": 1.25,
        },
    }


def test_usage_projection_is_deterministic_and_authority_scoped() -> None:
    routes = [
        _route("2026-08-15T10:00:00+00:00"),
        _route("2026-08-16T10:30:00+00:00", provider="provider-b"),
        _route("2026-08-16T12:00:00+00:00", skill="skill-b"),
        _route(
            "2026-08-18T10:15:00+00:00",
            provider="provider-b",
            capability="video.generate",
        ),
    ]

    first = project_usage_stats(routes, _governance(), evidence_count=7)
    second = project_usage_stats(reversed(routes), _governance(), evidence_count=7)

    assert first == second
    assert first["schema_version"] == "ilaios.usage-stats.v1"
    assert first["scope"] == "local_authenticated_control_plane"
    assert first["route_count"] == 4
    assert first["active_days"] == 3
    assert first["latest_streak_days"] == 1
    assert first["longest_streak_days"] == 2
    assert first["peak_execution_hour_utc"] == 10
    assert first["verified_evidence_count"] == 7
    assert first["provider_distribution"] == [
        {"key": "provider-a", "count": 2},
        {"key": "provider-b", "count": 2},
    ]
    assert first["governance_status_counts"] == [
        {"key": "executed", "count": 2},
        {"key": "failed", "count": 1},
    ]
    assert first["costs"] == {
        "coverage": "explicit_currency_only",
        "currency": "USD",
        "total_cost": 1.25,
        "record_count": 1,
    }


def test_usage_projection_does_not_invent_unavailable_metrics_or_leak_payloads() -> None:
    stats = project_usage_stats(
        [_route("2026-08-18T10:00:00+00:00")],
        _governance(),
        evidence_count=1,
    )
    coverage = stats["coverage"]
    assert isinstance(coverage, dict)
    assert coverage["tokens"] == "unavailable"
    assert coverage["latency"] == "unavailable"
    assert coverage["models"] == "unavailable"
    encoded = json.dumps(stats, sort_keys=True)
    assert "must-not-project" not in encoded
    assert "alice" not in encoded
    assert "bob" not in encoded


def test_malformed_authoritative_route_fails_closed() -> None:
    malformed_routes = (
        _route("2026-08-18T10:00:00"),
        _route("not-a-time"),
        {"agent_id": "agent-a"},
        {**_route("2026-08-18T10:00:00+00:00"), "provider_id": ""},
    )
    for route in malformed_routes:
        with pytest.raises(UsageIntelligenceError):
            project_usage_stats([route], _governance(), evidence_count=0)


def test_non_explicit_currency_cost_projection_fails_closed() -> None:
    governance = _governance()
    governance["costs"] = {
        "currency": "credits",
        "coverage": "estimated",
        "total_cost_usd": 1.0,
    }
    with pytest.raises(UsageIntelligenceError, match="explicit USD"):
        project_usage_stats([], governance, evidence_count=0)


def test_empty_sources_remain_truthfully_empty() -> None:
    stats = project_usage_stats([], {}, evidence_count=0)
    assert stats["route_count"] == 0
    assert stats["active_days"] == 0
    assert stats["latest_streak_days"] == 0
    assert stats["longest_streak_days"] == 0
    assert stats["latest_activity_at"] is None
    assert stats["peak_execution_hour_utc"] is None
    assert stats["provider_distribution"] == []
    assert stats["costs"] == {
        "coverage": "unavailable",
        "currency": None,
        "total_cost": None,
    }
