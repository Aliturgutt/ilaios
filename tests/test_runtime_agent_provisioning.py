from pathlib import Path

import pytest

from services.agent_registry import registration_for
from services.control_plane.migrations import migrate_database
from services.named_agent_executor import NamedAgentExecutionError, NamedAgentExecutor
from services.runtime import GovernedRuntime, GrantPolicy
from services.runtime.routing import RuntimeError

AGENT_ID = "ilaios.agent.security.codesec.v1"


def _runtime(tmp_path: Path) -> GovernedRuntime:
    database = tmp_path / "runtime.sqlite3"
    migrate_database(database)
    return GovernedRuntime(database)


def test_ensure_agent_is_idempotent_and_projects_persisted_authority(
    tmp_path: Path,
) -> None:
    runtime = _runtime(tmp_path)
    authorities = frozenset({"security.sast", "security.secret-scan"})

    assert runtime.ensure_agent(AGENT_ID, authorities) is True
    assert runtime.ensure_agent(AGENT_ID, authorities) is False
    assert runtime.agents() == (
        {
            "agent_id": AGENT_ID,
            "authorities": ["security.sast", "security.secret-scan"],
        },
    )


def test_ensure_agent_fails_closed_on_authority_drift(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    runtime.ensure_agent(AGENT_ID, frozenset({"security.sast"}))

    with pytest.raises(
        RuntimeError,
        match="registered agent authorities differ from canonical provisioning",
    ):
        runtime.ensure_agent(
            AGENT_ID,
            frozenset({"security.sast", "security.secret-scan"}),
        )


def test_named_executor_provisions_only_canonical_manifest_capabilities(
    tmp_path: Path,
) -> None:
    runtime = _runtime(tmp_path)
    executor = NamedAgentExecutor(runtime, GrantPolicy())
    expected = sorted(registration_for(AGENT_ID).manifest.capabilities)

    assert executor.provision_agent(AGENT_ID) is True
    assert executor.provision_agent(AGENT_ID) is False
    assert runtime.agents() == (
        {"agent_id": AGENT_ID, "authorities": expected},
    )


def test_named_executor_rejects_noncanonical_identity(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    executor = NamedAgentExecutor(runtime, GrantPolicy())

    with pytest.raises(
        NamedAgentExecutionError,
        match="unknown canonical agent identity",
    ):
        executor.provision_agent("ilaios.agent.unregistered.user-defined.v1")

    assert runtime.agents() == ()
