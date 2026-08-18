"""Fail-closed control-plane projection and commands for canonical agents."""

from __future__ import annotations

from typing import Any

from services.agent_registry import CANONICAL_AGENT_REGISTRY
from services.named_agent_executor import (
    NamedAgentExecutionError,
    provision_canonical_agent,
)
from services.runtime import GovernedRuntime


_FORBIDDEN_CALLER_AUTHORITY_FIELDS = frozenset(
    {"authorities", "capabilities", "permissions", "allowed_callers", "allowed_targets"}
)


def canonical_agent_state(runtime: GovernedRuntime) -> dict[str, object]:
    """Project canonical agent identity plus persisted runtime registration state."""
    persisted: dict[str, frozenset[str]] = {}
    for item in runtime.agents():
        agent_id = item.get("agent_id")
        raw_authorities = item.get("authorities")
        if not isinstance(agent_id, str) or not agent_id:
            raise ValueError("persisted runtime agent identity projection is malformed")
        if not isinstance(raw_authorities, list) or any(
            not isinstance(value, str) for value in raw_authorities
        ):
            raise ValueError("persisted runtime agent authority projection is malformed")
        persisted[agent_id] = frozenset(raw_authorities)

    agents: list[dict[str, object]] = []
    registered_count = 0
    drift_count = 0
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
        agents.append(
            {
                "agent_id": manifest.agent_id,
                "alias": manifest.alias,
                "role": manifest.role,
                "team": manifest.team,
                "capabilities": sorted(manifest.capabilities),
                "permissions": sorted(manifest.permissions),
                "readiness": registration.readiness.value,
                "backing_capability": registration.backing_capability,
                "registered": registered,
                "authority_matches_canonical": authority_matches,
            }
        )
    return {
        "agents": agents,
        "canonical_count": len(CANONICAL_AGENT_REGISTRY),
        "registered_count": registered_count,
        "authority_drift_count": drift_count,
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
