"""Fail-closed control-plane projection and commands for canonical agents."""

from __future__ import annotations

from typing import Any

from services.agent_projection import agent_state_projection
from services.agent_readiness_store import AgentReadinessStore
from services.agent_registry import CANONICAL_AGENT_REGISTRY
from services.named_agent_executor import (
    NamedAgentExecutionError,
    provision_canonical_agent,
)
from services.runtime import GovernedRuntime


_FORBIDDEN_CALLER_AUTHORITY_FIELDS = frozenset(
    {"authorities", "capabilities", "permissions", "allowed_callers", "allowed_targets"}
)


def canonical_agent_state(
    runtime: GovernedRuntime,
    readiness_store: AgentReadinessStore | None = None,
) -> dict[str, object]:
    """Project canonical identity, registration, runtime routes and readiness truth.

    The normal Desktop HTTP path remains read-only: when no readiness store is
    injected explicitly, an existing sibling ``agent-readiness.sqlite3`` is
    opened. A GET request never creates the evidence database.
    """
    persisted: dict[str, frozenset[str]] = {}
    for item in runtime.agents():
        agent_id = item.get("agent_id")
        raw_authorities = item.get("authorities")
        if not isinstance(agent_id, str) or not agent_id:
            raise ValueError("persisted runtime agent identity projection is malformed")
        if not isinstance(raw_authorities, list):
            raise ValueError("persisted runtime agent authority projection is malformed")
        authorities: list[str] = []
        for value in raw_authorities:
            if not isinstance(value, str) or not value or value != value.strip():
                raise ValueError("persisted runtime agent authority projection is malformed")
            authorities.append(value)
        if not authorities:
            raise ValueError("persisted runtime agent authority projection is malformed")
        persisted[agent_id] = frozenset(authorities)

    resolved_store = readiness_store
    if resolved_store is None:
        readiness_path = runtime.database_path.with_name("agent-readiness.sqlite3")
        if readiness_path.is_file():
            resolved_store = AgentReadinessStore(readiness_path)
    readiness_projection = (
        resolved_store.projection() if resolved_store is not None else {}
    )
    runtime_projection = agent_state_projection(runtime.routes(), readiness_projection)
    raw_agents = runtime_projection.get("agents")
    if not isinstance(raw_agents, list):
        raise ValueError("runtime agent projection is malformed")
    runtime_by_id: dict[str, dict[str, object]] = {}
    for item in raw_agents:
        if not isinstance(item, dict):
            continue
        agent_id = item.get("agent_id")
        if not isinstance(agent_id, str):
            continue
        typed_item: dict[str, object] = {}
        for key, value in item.items():
            if isinstance(key, str):
                typed_item[key] = value
        runtime_by_id[agent_id] = typed_item

    agents: list[dict[str, object]] = []
    registered_count = 0
    drift_count = 0
    readiness_counts: dict[str, int] = {
        "registered": 0,
        "executable": 0,
        "verified": 0,
    }
    for registration in CANONICAL_AGENT_REGISTRY:
        manifest = registration.manifest
        runtime_authorities = persisted.get(manifest.agent_id)
        registered = runtime_authorities is not None
        authority_matches = (
            runtime_authorities == manifest.capabilities if registered else True
        )
        if registered:
            registered_count += 1
        if not authority_matches:
            drift_count += 1
        observed = runtime_by_id.get(manifest.agent_id, {})
        readiness = observed.get("readiness", registration.readiness.value)
        if not isinstance(readiness, str) or readiness not in readiness_counts:
            raise ValueError("agent readiness projection is malformed")
        readiness_counts[readiness] += 1
        row: dict[str, object] = {
            "agent_id": manifest.agent_id,
            "alias": manifest.alias,
            "role": manifest.role,
            "team": manifest.team,
            "capabilities": sorted(manifest.capabilities),
            "permissions": sorted(manifest.permissions),
            "readiness": readiness,
            "backing_capability": registration.backing_capability,
            "registered": registered,
            "authority_matches_canonical": authority_matches,
        }
        for key in (
            "agent_status",
            "active_tasks",
            "current_task",
            "current_task_detail",
            "provider_id",
            "model_id",
            "input_tokens",
            "output_tokens",
            "token_usage",
            "actual_cost_usd",
            "reserved_cost_usd",
            "latency_ms",
            "last_activity",
            "evidence_digest",
            "readiness_evidence_id",
            "readiness_evidence_digest",
            "producer_evidence_digest",
            "readiness_updated_at",
            "readiness_verifier_id",
            "health",
        ):
            if key in observed:
                row[key] = observed[key]
        agents.append(row)
    return {
        "agents": agents,
        "canonical_count": len(CANONICAL_AGENT_REGISTRY),
        "registered_count": registered_count,
        "authority_drift_count": drift_count,
        "readiness_counts": readiness_counts,
        "source": "canonical-registry+runtime-routes+append-only-readiness-evidence",
    }


def handle_agent_command(
    runtime: GovernedRuntime, payload: dict[str, Any]
) -> dict[str, object]:
    """Execute a bounded registry-backed agent command.

    Caller-supplied authority is explicitly rejected. Provisioning derives the
    capability set from the canonical Agent Registry only.
    """
    forbidden = _FORBIDDEN_CALLER_AUTHORITY_FIELDS.intersection(payload)
    if forbidden:
        raise ValueError("agent authority is server-resolved from the canonical registry")
    unexpected = set(payload) - {"operation", "agent_id"}
    if unexpected:
        raise ValueError("agent command contains unsupported fields")
    operation = payload.get("operation")
    agent_id = payload.get("agent_id")
    if not isinstance(operation, str) or not operation:
        raise TypeError("operation must be a string")
    if operation != "provision":
        raise ValueError("unknown agent operation")
    if not isinstance(agent_id, str) or not agent_id or agent_id != agent_id.strip():
        raise TypeError("agent_id must be a non-blank trimmed string")
    try:
        created = provision_canonical_agent(runtime, agent_id)
    except NamedAgentExecutionError as exc:
        raise ValueError(str(exc)) from exc
    return {"agent_id": agent_id, "registered": True, "created": created}
