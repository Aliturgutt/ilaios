"""Truth-preserving canonical agent projection for Control Plane/Desktop."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from typing import Any

from services.agent_registry import CANONICAL_AGENT_REGISTRY


def agent_state_projection(
    routes: Iterable[Mapping[str, Any]],
    readiness: Mapping[str, Mapping[str, object]] | None = None,
) -> dict[str, object]:
    latest: dict[str, Mapping[str, Any]] = {}
    for runtime_route in routes:
        agent_id = runtime_route.get("agent_id")
        if isinstance(agent_id, str):
            latest[agent_id] = runtime_route
    readiness_map: Mapping[str, Mapping[str, object]] = (
        readiness if readiness is not None else {}
    )

    agents: list[dict[str, object]] = []
    for registration in CANONICAL_AGENT_REGISTRY:
        manifest = registration.manifest
        latest_route = latest.get(manifest.agent_id)
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
            "agent_status": "offline" if latest_route is None else "idle",
            "active_tasks": 0,
        }
        readiness_record = readiness_map.get(manifest.agent_id)
        if readiness_record is not None:
            _merge_readiness(record, readiness_record)
        if latest_route is not None:
            _merge_route(record, latest_route)
        agents.append(record)

    return {
        "agent_count": len(agents),
        "agents": agents,
        "source": (
            "canonical-agent-registry+persisted-runtime-routes+"
            "append-only-readiness-evidence"
        ),
    }


def _merge_readiness(
    record: dict[str, object], readiness: Mapping[str, object]
) -> None:
    verifier_id = readiness.get("verifier_id")
    if not isinstance(verifier_id, str) or verifier_id != record.get("verifier_id"):
        return
    record["readiness_verifier_id"] = verifier_id

    allowed_readiness = {"registered", "executable", "verified"}
    value = readiness.get("readiness")
    if isinstance(value, str) and value in allowed_readiness:
        record["readiness"] = value
    for key in (
        "readiness_evidence_id",
        "readiness_evidence_digest",
        "producer_evidence_digest",
        "readiness_updated_at",
    ):
        value = readiness.get(key)
        if isinstance(value, str) and value:
            record[key] = value


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
        for key in (
            "model_id",
            "input_tokens",
            "output_tokens",
            "actual_cost_usd",
            "reserved_cost_usd",
            "latency_ms",
            "response_id",
            "skill_id",
            "skill_sha256",
        ):
            _copy_if_scalar(record, output, key)
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
