from __future__ import annotations

from services.agent_e2e_matrix import build_agent_e2e_matrix, matrix_summary
from services.agent_readiness import EXPECTED_AGENT_COUNT, audit_agent_registry
from services.agent_registry import CANONICAL_AGENT_REGISTRY


def test_canonical_agent_population_is_exact_and_static_readiness_is_not_promoted() -> None:
    audit_agent_registry()
    assert EXPECTED_AGENT_COUNT == 47
    assert len(CANONICAL_AGENT_REGISTRY) == 47
    rows = build_agent_e2e_matrix({})
    assert matrix_summary(rows) == {
        "registered": 47,
        "executable": 0,
        "verified": 0,
    }


def test_matrix_has_exact_team_population() -> None:
    rows = build_agent_e2e_matrix({})
    counts: dict[str, int] = {}
    for row in rows:
        team = str(row["team"])
        counts[team] = counts.get(team, 0) + 1
    assert counts == {
        "core": 5,
        "engineering": 10,
        "security": 6,
        "web": 6,
        "media": 8,
        "intelligence": 4,
        "operations": 6,
        "meta": 2,
    }
