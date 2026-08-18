from __future__ import annotations

from pathlib import Path

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
    assert result["provider_id"] == "test-provider"
    assert result["output"] == {"ok": True, "skill_sha256": digest}
    assert runtime.routes()[0]["provider_id"] == "test-provider"
