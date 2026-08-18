"""Restart/idempotency proofs for canonical runtime provisioning."""

from pathlib import Path

import pytest

from services.control_plane.migrations import migrate_database
from services.runtime import GovernedRuntime
from services.runtime.routing import RuntimeError


def _runtime(tmp_path: Path) -> GovernedRuntime:
    database = tmp_path / "runtime.sqlite3"
    migrate_database(database)
    return GovernedRuntime(database)


def test_ensure_agent_is_idempotent_and_rejects_authority_drift(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    runtime.ensure_agent("agent-a", frozenset({"capability.a"}))
    runtime.ensure_agent("agent-a", frozenset({"capability.a"}))
    with pytest.raises(RuntimeError, match="authorities drifted"):
        runtime.ensure_agent("agent-a", frozenset({"capability.b"}))


def test_ensure_skill_is_idempotent_and_rejects_content_or_authority_drift(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    digest = runtime.ensure_skill(
        "skill-a",
        b"immutable instructions",
        frozenset({"capability.a"}),
    )
    assert runtime.ensure_skill(
        "skill-a",
        b"immutable instructions",
        frozenset({"capability.a"}),
    ) == digest
    with pytest.raises(RuntimeError, match="skill drifted"):
        runtime.ensure_skill(
            "skill-a",
            b"changed instructions",
            frozenset({"capability.a"}),
        )
    with pytest.raises(RuntimeError, match="skill drifted"):
        runtime.ensure_skill(
            "skill-a",
            b"immutable instructions",
            frozenset({"capability.b"}),
        )


def test_ensure_provider_is_idempotent_and_rejects_configuration_drift(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    runtime.ensure_provider(
        "provider-a",
        frozenset({"capability.a"}),
        adapter_kind="canonical-json-sha256",
        deterministic=True,
    )
    runtime.ensure_provider(
        "provider-a",
        frozenset({"capability.a"}),
        adapter_kind="canonical-json-sha256",
        deterministic=True,
    )
    with pytest.raises(RuntimeError, match="configuration drifted"):
        runtime.ensure_provider(
            "provider-a",
            frozenset({"capability.b"}),
            adapter_kind="canonical-json-sha256",
            deterministic=True,
        )
