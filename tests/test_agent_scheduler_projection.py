"""Scheduler → Desktop agent projection integration proofs."""

from datetime import datetime, timedelta, timezone
from pathlib import Path

from services.agent_readiness import AgentReadinessProof
from services.agent_readiness_store import AgentReadinessStore
from services.agent_registry import registration_for
from services.control_plane.migrations import migrate_database
from services.runtime import GovernedRuntime
from services.runtime.durable_scheduler import DurableWorkerScheduler

NOW = datetime(2026, 8, 18, 11, 30, tzinfo=timezone.utc)
PLANNER_ID = "ilaios.agent.core.planner.v1"


def _state(tmp_path: Path) -> tuple[Path, DurableWorkerScheduler]:
    database = tmp_path / "state.sqlite3"
    migrate_database(database)
    return database, DurableWorkerScheduler(
        database,
        lease_duration=timedelta(seconds=30),
    )


def test_scheduler_projects_exact_47_registry_agents_offline_before_execution(
    tmp_path: Path,
) -> None:
    _, scheduler = _state(tmp_path)
    state = scheduler.state()
    agents = state["agents"]
    assert state["agent_count"] == 47
    assert isinstance(agents, list)
    assert len(agents) == 47
    assert {item["agent_status"] for item in agents} == {"offline"}
    assert {item["readiness"] for item in agents} == {"registered"}
    assert state["workers"] == []
    assert state["leases"] == []
    assert state["effects"] == []


def test_persisted_runtime_route_becomes_idle_agent_with_real_provider_telemetry(
    tmp_path: Path,
) -> None:
    database, scheduler = _state(tmp_path)
    runtime = GovernedRuntime(database)
    registration = registration_for(PLANNER_ID)
    runtime.register_agent(PLANNER_ID, registration.manifest.capabilities)
    runtime.register_skill(
        "skill-planner-test",
        b"bounded planner test skill",
        frozenset({"workflow.plan"}),
    )
    runtime.register_provider(
        "provider-local-test",
        frozenset({"workflow.plan"}),
        adapter_kind="canonical-json-sha256",
    )
    route = runtime.execute(
        PLANNER_ID,
        "skill-planner-test",
        "workflow.plan",
        {"intent": "bounded test"},
    )
    assert route["sequence"] == 1

    state = scheduler.state()
    agents = state["agents"]
    assert isinstance(agents, list)
    planner = next(item for item in agents if item["agent_id"] == PLANNER_ID)
    assert planner["agent_status"] == "idle"
    assert planner["provider_id"] == "provider-local-test"
    assert planner["current_task"] == "skill-planner-test"
    assert planner["readiness"] == "registered"
    assert len(planner["evidence_digest"]) == 64


def test_append_only_readiness_is_joined_without_turning_offline_agent_active(
    tmp_path: Path,
) -> None:
    database, scheduler = _state(tmp_path)
    verifier_id = registration_for(PLANNER_ID).manifest.verifier_id
    proof = AgentReadinessProof(
        agent_id=PLANNER_ID,
        verifier_id=verifier_id,
        invocation_passed=True,
        skill_passed=True,
        permission_passed=True,
        provider_passed=True,
        output_passed=True,
        independent_verification_passed=True,
        evidence_persisted=True,
        desktop_projection_passed=True,
        regression_e2e_passed=True,
        evidence_digest="a" * 64,
    )
    AgentReadinessStore(database).persist(proof, created_at=NOW)

    state = scheduler.state()
    agents = state["agents"]
    assert isinstance(agents, list)
    planner = next(item for item in agents if item["agent_id"] == PLANNER_ID)
    assert planner["readiness"] == "verified"
    assert planner["agent_status"] == "offline"
    assert planner["readiness_verifier_id"] == verifier_id
    assert "provider_id" not in planner
