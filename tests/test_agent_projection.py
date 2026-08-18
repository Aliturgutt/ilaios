"""Truth-boundary tests for canonical agent projection consumed by Desktop."""

from services.agent_projection import agent_state_projection


def test_projection_exposes_exact_registry_without_claiming_runtime_activity() -> None:
    projection = agent_state_projection(())
    agents = projection["agents"]
    assert projection["agent_count"] == 47
    assert isinstance(agents, list)
    assert len(agents) == 47
    assert {item["readiness"] for item in agents} == {"registered"}
    assert {item["agent_status"] for item in agents} == {"registered"}
    assert all("provider_id" not in item for item in agents)
    assert all("evidence_digest" not in item for item in agents)


def test_projection_joins_only_observed_runtime_provider_and_usage_evidence() -> None:
    projection = agent_state_projection(
        (
            {
                "sequence": 7,
                "agent_id": "ilaios.agent.core.planner.v1",
                "skill_id": "ilaios.skill.core.planning.v1",
                "provider_id": "provider-b",
                "capability": "workflow.plan",
                "input_sha256": "a" * 64,
                "output": {
                    "model_id": "model-b",
                    "provider_id": "provider-b",
                    "input_tokens": 24,
                    "output_tokens": 18,
                    "actual_cost_usd": "0.00006",
                    "reserved_cost_usd": "0.000288",
                    "latency_ms": 125,
                    "response_id": "response-b",
                },
                "created_at": "2026-08-18T09:00:00+00:00",
            },
        )
    )
    agents = projection["agents"]
    assert isinstance(agents, list)
    planner = next(
        item for item in agents if item["agent_id"] == "ilaios.agent.core.planner.v1"
    )
    assert planner["readiness"] == "registered"
    assert planner["agent_status"] == "idle"
    assert planner["current_task"] == "ilaios.skill.core.planning.v1"
    assert planner["provider_id"] == "provider-b"
    assert planner["model_id"] == "model-b"
    assert planner["token_usage"] == 42
    assert planner["actual_cost_usd"] == "0.00006"
    assert planner["latency_ms"] == 125
    assert len(planner["evidence_digest"]) == 64


def test_unknown_runtime_identity_never_mints_a_desktop_agent() -> None:
    projection = agent_state_projection(
        (
            {
                "sequence": 1,
                "agent_id": "external.agent.untrusted",
                "skill_id": "unknown",
                "provider_id": "unknown",
                "capability": "unknown",
                "output": {},
                "created_at": "2026-08-18T09:00:00+00:00",
            },
        )
    )
    agents = projection["agents"]
    assert isinstance(agents, list)
    assert len(agents) == 47
    assert all(item["agent_id"] != "external.agent.untrusted" for item in agents)
