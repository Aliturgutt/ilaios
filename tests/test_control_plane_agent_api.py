from pathlib import Path

import pytest

from services.agent_registry import registration_for
from services.control_plane.agent_api import canonical_agent_state, handle_agent_command
from services.control_plane.migrations import migrate_database
from services.runtime import GovernedRuntime

AGENT_ID = "ilaios.agent.security.codesec.v1"


def _runtime(tmp_path: Path) -> GovernedRuntime:
    database = tmp_path / "runtime.sqlite3"
    migrate_database(database)
    return GovernedRuntime(database)


def test_agent_state_is_registry_derived_and_reports_runtime_registration(
    tmp_path: Path,
) -> None:
    runtime = _runtime(tmp_path)
    manifest = registration_for(AGENT_ID).manifest
    runtime.ensure_agent(AGENT_ID, manifest.capabilities)

    state = canonical_agent_state(runtime)
    agents = state["agents"]
    assert isinstance(agents, list)
    selected = next(item for item in agents if item["agent_id"] == AGENT_ID)
    assert selected["alias"] == manifest.alias
    assert selected["capabilities"] == sorted(manifest.capabilities)
    assert selected["permissions"] == sorted(manifest.permissions)
    assert selected["registered"] is True
    assert selected["authority_matches_canonical"] is True
    assert state["registered_count"] == 1
    assert state["authority_drift_count"] == 0


def test_agent_state_exposes_authority_drift_instead_of_masking_it(
    tmp_path: Path,
) -> None:
    runtime = _runtime(tmp_path)
    runtime.register_agent(AGENT_ID, frozenset({"noncanonical.authority"}))

    state = canonical_agent_state(runtime)
    agents = state["agents"]
    assert isinstance(agents, list)
    selected = next(item for item in agents if item["agent_id"] == AGENT_ID)
    assert selected["registered"] is True
    assert selected["authority_matches_canonical"] is False
    assert state["authority_drift_count"] == 1


def test_agent_provision_command_is_idempotent_and_server_resolves_authority(
    tmp_path: Path,
) -> None:
    runtime = _runtime(tmp_path)

    first = handle_agent_command(
        runtime,
        {"operation": "provision", "agent_id": AGENT_ID},
    )
    second = handle_agent_command(
        runtime,
        {"operation": "provision", "agent_id": AGENT_ID},
    )

    assert first == {"agent_id": AGENT_ID, "registered": True, "created": True}
    assert second == {"agent_id": AGENT_ID, "registered": True, "created": False}
    assert runtime.agents()[0]["authorities"] == sorted(
        registration_for(AGENT_ID).manifest.capabilities
    )


def test_agent_command_rejects_caller_supplied_authority(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    fields = (
        "authorities",
        "capabilities",
        "permissions",
        "allowed_callers",
        "allowed_targets",
    )

    for field in fields:
        with pytest.raises(ValueError, match="server-resolved"):
            handle_agent_command(
                runtime,
                {"operation": "provision", "agent_id": AGENT_ID, field: ["admin"]},
            )
        assert runtime.agents() == ()


def test_agent_command_rejects_unknown_identity_and_unexpected_fields(
    tmp_path: Path,
) -> None:
    runtime = _runtime(tmp_path)

    with pytest.raises(ValueError, match="unknown canonical agent identity"):
        handle_agent_command(
            runtime,
            {
                "operation": "provision",
                "agent_id": "ilaios.agent.unregistered.user-defined.v1",
            },
        )
    with pytest.raises(ValueError, match="unsupported fields"):
        handle_agent_command(
            runtime,
            {"operation": "provision", "agent_id": AGENT_ID, "role": "owner"},
        )

    assert runtime.agents() == ()
