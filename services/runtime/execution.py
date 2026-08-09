"""Persisted governed agent/skill/provider runtime with real local adapters."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, ClassVar

from services.runtime.routing import (
    AgentProfile,
    ProviderProfile,
    RuntimeError,
    SkillArtifact,
    SkillRegistry,
    route_provider,
)


class GovernedRuntime:
    """Execute approved immutable skills through persisted provider manifests."""

    _ADAPTERS: ClassVar[
        dict[str, Callable[[dict[str, Any]], dict[str, Any]]]
    ] = {
        "canonical-json-sha256": lambda payload: {
            "sha256": hashlib.sha256(
                json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest()
        },
        "uppercase-text": lambda payload: {
            "text": _required_payload_text(payload).upper()
        },
    }

    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def register_agent(self, agent_id: str, authorities: frozenset[str]) -> None:
        _require_id(agent_id, "agent_id")
        _require_values(authorities, "authorities")
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO runtime_agents VALUES (?, ?)",
                (agent_id, json.dumps(sorted(authorities))),
            )

    def register_skill(
        self, skill_id: str, content: bytes, authorities: frozenset[str]
    ) -> str:
        _require_id(skill_id, "skill_id")
        if not content:
            raise RuntimeError("skill content must not be empty")
        _require_values(authorities, "authorities")
        digest = hashlib.sha256(content).hexdigest()
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO runtime_skills VALUES (?, ?, ?, ?)",
                (skill_id, digest, json.dumps(sorted(authorities)), content),
            )
        return digest

    def register_provider(
        self,
        provider_id: str,
        capabilities: frozenset[str],
        *,
        adapter_kind: str,
        enabled: bool = True,
    ) -> None:
        _require_id(provider_id, "provider_id")
        _require_values(capabilities, "capabilities")
        if adapter_kind not in self._ADAPTERS:
            raise RuntimeError("unknown local adapter kind")
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO runtime_providers VALUES (?, ?, 1, ?, ?)",
                (
                    provider_id,
                    json.dumps(sorted(capabilities)),
                    int(enabled),
                    adapter_kind,
                ),
            )

    def execute(
        self,
        agent_id: str,
        skill_id: str,
        capability: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Validate, route, execute, and persist one governed adapter call."""
        with self._connect() as connection:
            agent_row = connection.execute(
                "SELECT * FROM runtime_agents WHERE agent_id = ?", (agent_id,)
            ).fetchone()
            skill_row = connection.execute(
                "SELECT * FROM runtime_skills WHERE skill_id = ?", (skill_id,)
            ).fetchone()
            provider_rows = connection.execute(
                "SELECT * FROM runtime_providers ORDER BY provider_id"
            ).fetchall()
        if agent_row is None:
            raise RuntimeError("agent is not registered")
        if skill_row is None:
            raise RuntimeError("skill is not approved")
        agent = AgentProfile(
            agent_row["agent_id"], frozenset(json.loads(agent_row["authorities_json"]))
        )
        content = bytes(skill_row["content"])
        authorities = frozenset(json.loads(skill_row["authorities_json"]))
        artifact = SkillArtifact(skill_row["skill_id"], content, authorities)
        registry = SkillRegistry()
        registry.approve(skill_row["skill_id"], skill_row["digest"], authorities)
        providers = tuple(
            ProviderProfile(
                row["provider_id"],
                frozenset(json.loads(row["capabilities_json"])),
                bool(row["deterministic"]),
                bool(row["enabled"]),
            )
            for row in provider_rows
        )
        decision = route_provider(
            agent, artifact, registry, providers, capability=capability
        )
        selected = next(
            row for row in provider_rows if row["provider_id"] == decision.provider_id
        )
        output = self._ADAPTERS[selected["adapter_kind"]](payload)
        canonical_input = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        with self._connect() as connection:
            cursor = connection.execute(
                "INSERT INTO runtime_routes "
                "(agent_id, skill_id, provider_id, capability, input_sha256, "
                "output_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    agent_id,
                    skill_id,
                    decision.provider_id,
                    capability,
                    hashlib.sha256(canonical_input.encode()).hexdigest(),
                    json.dumps(output, sort_keys=True),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            sequence = cursor.lastrowid
        return {
            "sequence": sequence,
            "agent_id": decision.agent_id,
            "skill_id": decision.skill_id,
            "provider_id": decision.provider_id,
            "capability": decision.capability,
            "deterministic_first": decision.deterministic_first,
            "evidence": list(decision.evidence),
            "output": output,
        }

    def routes(self) -> tuple[dict[str, Any], ...]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM runtime_routes ORDER BY sequence"
            ).fetchall()
        return tuple(
            {
                "sequence": row["sequence"],
                "agent_id": row["agent_id"],
                "skill_id": row["skill_id"],
                "provider_id": row["provider_id"],
                "capability": row["capability"],
                "input_sha256": row["input_sha256"],
                "output": json.loads(row["output_json"]),
                "created_at": row["created_at"],
            }
            for row in rows
        )


def _required_payload_text(payload: dict[str, Any]) -> str:
    value = payload.get("text")
    if not isinstance(value, str):
        raise RuntimeError("uppercase adapter requires text")
    return value


def _require_id(value: str, field: str) -> None:
    if not value or value != value.strip():
        raise RuntimeError(f"{field} must be non-blank and trimmed")


def _require_values(values: frozenset[str], field: str) -> None:
    if not values or any(not item or item != item.strip() for item in values):
        raise RuntimeError(f"{field} must contain trimmed values")
