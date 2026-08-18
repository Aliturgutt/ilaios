"""Truth-preserving canonical agent projection for Control Plane/Desktop.

The projection never turns registry presence into runtime activity or VERIFIED
maturity. It joins stable identity metadata with the latest persisted runtime
route, when one exists, so UI consumers can show real provider/model/usage and
evidence without inventing telemetry.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from typing import Any

from services.agent_registry import CANONICAL_AGENT_REGISTRY


def agent_state_projection(
    routes: Iterable[Mapping[str, Any]],
) -> dict[str, object]:
    latest: dict[str, Mapping[str, Any]] = {}
    for route in routes:
        agent_id = route.get("agent_id")
        if isinstance(agent_id, str):
            latest[agent_id] = route

    agents: list[dict[str, object]] = []
    for registration in CANONICAL_AGENT_REGISTRY:
        manifest = registration.manifest
        route = latest.get(manifest.agent_id)
        record: dict[str, object] = {
            "agent_id": manifest.agent_id,
            "agent_name": manifest.alias,
            "role": manifest.role,
            "team": manifest.team,
            "capabilities": sorted(manifest.capabilities),
            "permissions": sorted(manifest.permissions),
            "readiness": registration.readiness.value,
            "verifier_id": manifest.verifier_id,
            "backing_capability": registration.backing_capability,
            "agent_status": "registered" if route is None else "idle",
            "active_tasks": 0,
        }
        if route is not None:
            _merge_route(record, route)
        agents.append(record)

    return {
        "agent_count": len(agents),
        "agents": agents,
        "source": "canonical-agent-registry+persisted-runtime-routes",
    }


def _merge_route(record: dict[str, object], route: Mapping[str, Any]) -> None:
    sequence = route.get("sequence")
    skill_id = route.get("skill_id")
    provider_id = route.get("provider_id")
    capability = route.get("capability")
    created_at = route.get("created_at")
    output = route.get("output")

    if isinstance(sequence, int):
        record["route_sequence"] = sequence
    if isinstance(skill_id, str):
        record["current_task"] = skill_id
    if isinstance(provider_id, str):
        record["provider_id"] = provider_id
    if isinstance(capability, str):
        record["current_task_detail"] = capability
    if isinstance(created_at, str):
        record["last_activity"] = created_at
    if isinstance(output, Mapping):
        _copy_if_scalar(record, output, "model_id")
        _copy_if_scalar(record, output, "input_tokens")
        _copy_if_scalar(record, output, "output_tokens")
        _copy_if_scalar(record, output, "actual_cost_usd")
        _copy_if_scalar(record, output, "reserved_cost_usd")
        _copy_if_scalar(record, output, "latency_ms")
        _copy_if_scalar(record, output, "response_id")
        input_tokens = output.get("input_tokens")
        output_tokens = output.get("output_tokens")
        if isinstance(input_tokens, int) and isinstance(output_tokens, int):
            record["token_usage"] = input_tokens + output_tokens

    material = json.dumps(
        {
            "agent_id": record["agent_id"],
            "sequence": sequence,
            "skill_id": skill_id,
            "provider_id": provider_id,
            "capability": capability,
            "output": output,
        },
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode()
    record["evidence_digest"] = hashlib.sha256(material).hexdigest()
    record["health"] = "observed-route"


def _copy_if_scalar(
    target: dict[str, object], source: Mapping[str, Any], key: str
) -> None:
    value = source.get(key)
    if isinstance(value, (str, int, float, bool)):
        target[key] = value
