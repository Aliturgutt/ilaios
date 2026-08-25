from __future__ import annotations

import pytest

from services.agent_final_closure import (
    AgentFinalClosureError,
    _require_runtime_active_agent_identities,
)
from services.agent_registry import CANONICAL_AGENT_REGISTRY

_PLANNER_AGENT_ID = "ilaios.agent.core.planner.v1"
_ORCHESTRATOR_AGENT_ID = "ilaios.agent.core.orchestrator.v1"


def _other_canonical_agent_id() -> str:
    return next(
        item.manifest.agent_id
        for item in CANONICAL_AGENT_REGISTRY
        if item.manifest.agent_id not in {_PLANNER_AGENT_ID, _ORCHESTRATOR_AGENT_ID}
    )


def test_runtime_active_ids_accept_canonical_planner_orchestrator_subset() -> None:
    active_ids = [_PLANNER_AGENT_ID, _ORCHESTRATOR_AGENT_ID, _other_canonical_agent_id()]
    receipt: dict[str, object] = {
        "runtime_active_count": len(active_ids),
        "runtime_active_agent_ids": active_ids,
    }

    assert _require_runtime_active_agent_identities(receipt) == tuple(active_ids)


def test_runtime_active_ids_reject_noncanonical_or_duplicate_identities() -> None:
    receipt: dict[str, object] = {
        "runtime_active_count": 3,
        "runtime_active_agent_ids": [
            _PLANNER_AGENT_ID,
            _ORCHESTRATOR_AGENT_ID,
            "ilaios.agent.core.not-canonical.v1",
        ],
    }
    with pytest.raises(AgentFinalClosureError, match="non-canonical"):
        _require_runtime_active_agent_identities(receipt)

    receipt = {
        "runtime_active_count": 3,
        "runtime_active_agent_ids": [
            _PLANNER_AGENT_ID,
            _ORCHESTRATOR_AGENT_ID,
            _ORCHESTRATOR_AGENT_ID,
        ],
    }
    with pytest.raises(AgentFinalClosureError, match="duplicate"):
        _require_runtime_active_agent_identities(receipt)


def test_runtime_active_ids_reject_count_mismatch() -> None:
    receipt: dict[str, object] = {
        "runtime_active_count": 3,
        "runtime_active_agent_ids": [_PLANNER_AGENT_ID, _ORCHESTRATOR_AGENT_ID],
    }
    with pytest.raises(AgentFinalClosureError, match="match runtime_active_count"):
        _require_runtime_active_agent_identities(receipt)


def test_runtime_active_ids_require_planner_and_orchestrator() -> None:
    other = _other_canonical_agent_id()
    receipt: dict[str, object] = {
        "runtime_active_count": 2,
        "runtime_active_agent_ids": [_ORCHESTRATOR_AGENT_ID, other],
    }
    with pytest.raises(AgentFinalClosureError, match="Planner"):
        _require_runtime_active_agent_identities(receipt)

    receipt = {
        "runtime_active_count": 2,
        "runtime_active_agent_ids": [_PLANNER_AGENT_ID, other],
    }
    with pytest.raises(AgentFinalClosureError, match="Orchestrator"):
        _require_runtime_active_agent_identities(receipt)
