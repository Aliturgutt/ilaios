from __future__ import annotations

from pathlib import Path

from services.agent_execution_evidence import durable_route_projection
from services.control_plane.migrations import migrate_database
from services.runtime.execution import GovernedRuntime


def test_external_adapter_uses_same_runtime_and_cannot_replace_local_adapter(tmp_path: Path) -> None:
    database = tmp_path / "control.sqlite3"
    migrate_database(database)

    def adapter(payload: dict[str, object]) -> dict[str, object]:
        skill = payload["_ilaios_skill"]
        assert isinstance(skill, dict)
        return {"ok": True, "skill_sha256": skill["sha256"]}

    runtime = GovernedRuntime(
        database,
        external_adapters={"test.external": adapter},
    )
    runtime.ensure_agent("ilaios.agent.test", frozenset({"test.run"}))
    digest = runtime.ensure_skill(
        "test-skill", b"bounded test instructions\n", frozenset({"test.run"})
    )
    runtime.ensure_provider(
        "test-provider",
        frozenset({"test.run"}),
        adapter_kind="test.external",
        deterministic=False,
    )
    result = runtime.execute(
        "ilaios.agent.test",
        "test-skill",
        "test.run",
        {"value": 1},
        preferred_provider_id="test-provider",
    )
    persisted = runtime.routes()[0]
    assert result["provider_id"] == "test-provider"
    assert result["output"] == {"ok": True, "skill_sha256": digest}
    assert persisted["provider_id"] == "test-provider"
    assert isinstance(result["input_sha256"], str)
    assert len(result["input_sha256"]) == 64
    assert isinstance(result["created_at"], str)
    assert durable_route_projection(result) == durable_route_projection(persisted)


def test_durable_route_projection_ignores_transient_routing_explanation() -> None:
    durable = {
        "sequence": 1,
        "agent_id": "ilaios.agent.test",
        "skill_id": "test-skill",
        "provider_id": "test-provider",
        "capability": "test.run",
        "input_sha256": "a" * 64,
        "output": {"ok": True},
        "created_at": "2026-08-18T00:00:00+00:00",
    }
    immediate = {
        **durable,
        "deterministic_first": False,
        "evidence": ["provider=test-provider"],
    }
    assert durable_route_projection(immediate) == durable
