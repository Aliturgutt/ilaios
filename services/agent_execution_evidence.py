"""Canonical durable digest truth for persisted named-agent execution evidence."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any

from services.named_agent_executor import NamedAgentExecution

_DURABLE_ROUTE_FIELDS = (
    "sequence",
    "agent_id",
    "skill_id",
    "provider_id",
    "capability",
    "input_sha256",
    "output",
    "created_at",
)


class AgentExecutionEvidenceError(ValueError):
    """Runtime route cannot be proven from durable evidence fields."""


def durable_route_projection(route: Mapping[str, Any]) -> dict[str, object]:
    """Return the exact runtime-route material that survives DB round-trip."""
    missing = [field for field in _DURABLE_ROUTE_FIELDS if field not in route]
    if missing:
        raise AgentExecutionEvidenceError(
            f"durable runtime route is missing fields: {','.join(missing)}"
        )
    sequence = route["sequence"]
    if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence <= 0:
        raise AgentExecutionEvidenceError("durable route sequence is invalid")
    identity_fields: dict[str, str] = {}
    for field in ("agent_id", "skill_id", "provider_id", "capability", "created_at"):
        value = route[field]
        if not isinstance(value, str) or not value or value != value.strip():
            raise AgentExecutionEvidenceError(f"durable route {field} is invalid")
        identity_fields[field] = value
    input_sha256 = route["input_sha256"]
    if (
        not isinstance(input_sha256, str)
        or len(input_sha256) != 64
        or any(character not in "0123456789abcdef" for character in input_sha256)
    ):
        raise AgentExecutionEvidenceError("durable route input digest is invalid")
    output = route["output"]
    if not isinstance(output, dict):
        raise AgentExecutionEvidenceError("durable route output is invalid")
    return {
        "sequence": sequence,
        "agent_id": identity_fields["agent_id"],
        "skill_id": identity_fields["skill_id"],
        "provider_id": identity_fields["provider_id"],
        "capability": identity_fields["capability"],
        "input_sha256": input_sha256,
        "output": output,
        "created_at": identity_fields["created_at"],
    }


def durable_route_digest(route: Mapping[str, Any]) -> str:
    projection = durable_route_projection(route)
    return hashlib.sha256(
        json.dumps(
            projection,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ).encode()
    ).hexdigest()


def execution_evidence_digest(execution: NamedAgentExecution) -> str:
    """Hash admitted identity plus the exact DB-round-trippable runtime route."""
    material = {
        "invocation_id": execution.admission.invocation_id,
        "agent_id": execution.admission.agent_id,
        "verifier_id": execution.admission.verifier_id,
        "route": durable_route_projection(execution.route),
    }
    return hashlib.sha256(
        json.dumps(material, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()
