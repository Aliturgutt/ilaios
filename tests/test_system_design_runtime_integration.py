"""Governed runtime integration tests for the ILAIOS system-design skill."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from services.agent_registry import CANONICAL_AGENT_REGISTRY
from services.runtime.execution import GovernedRuntime
from services.runtime.routing import RuntimeError
from services.runtime.system_design_adapter import (
    SYSTEM_DESIGN_ADAPTER_KIND,
    SYSTEM_DESIGN_AGENT_ID,
    SYSTEM_DESIGN_CAPABILITY,
    SYSTEM_DESIGN_PROVIDER_ID,
    SYSTEM_DESIGN_SKILL_ID,
)


def _runtime_database(path: Path) -> None:
    with sqlite3.connect(path) as connection:
        connection.executescript(
            """
            CREATE TABLE runtime_agents (
                agent_id TEXT PRIMARY KEY,
                authorities_json TEXT NOT NULL
            );
            CREATE TABLE runtime_skills (
                skill_id TEXT PRIMARY KEY,
                digest TEXT NOT NULL,
                authorities_json TEXT NOT NULL,
                content BLOB NOT NULL
            );
            CREATE TABLE runtime_providers (
                provider_id TEXT PRIMARY KEY,
                capabilities_json TEXT NOT NULL,
                deterministic INTEGER NOT NULL,
                enabled INTEGER NOT NULL,
                adapter_kind TEXT NOT NULL
            );
            CREATE TABLE runtime_routes (
                sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT NOT NULL,
                skill_id TEXT NOT NULL,
                provider_id TEXT NOT NULL,
                capability TEXT NOT NULL,
                input_sha256 TEXT NOT NULL,
                output_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            """
        )


def _configured_runtime(tmp_path: Path) -> GovernedRuntime:
    database = tmp_path / "runtime.sqlite3"
    _runtime_database(database)
    runtime = GovernedRuntime(database)
    runtime.register_agent(
        SYSTEM_DESIGN_AGENT_ID, frozenset({SYSTEM_DESIGN_CAPABILITY})
    )
    runtime.register_skill(
        SYSTEM_DESIGN_SKILL_ID,
        b"ILAIOS native system-design skill v0.1.0",
        frozenset({SYSTEM_DESIGN_CAPABILITY}),
    )
    runtime.register_provider(
        SYSTEM_DESIGN_PROVIDER_ID,
        frozenset({SYSTEM_DESIGN_CAPABILITY}),
        adapter_kind=SYSTEM_DESIGN_ADAPTER_KIND,
    )
    return runtime


def test_system_design_binds_to_existing_architect_agent() -> None:
    registrations = {
        item.manifest.agent_id: item for item in CANONICAL_AGENT_REGISTRY
    }
    architect = registrations[SYSTEM_DESIGN_AGENT_ID]
    assert SYSTEM_DESIGN_CAPABILITY in architect.manifest.capabilities
    assert architect.backing_capability == "software-factory"


def test_governed_runtime_routes_system_design_without_parallel_authority(
    tmp_path: Path,
) -> None:
    runtime = _configured_runtime(tmp_path)
    result = runtime.execute(
        SYSTEM_DESIGN_AGENT_ID,
        SYSTEM_DESIGN_SKILL_ID,
        SYSTEM_DESIGN_CAPABILITY,
        {
            "system_id": "high-throughput-web",
            "availability_slo": 0.9999,
            "asynchronous_workload_fraction": 0.2,
            "latency_slo_ms": 250,
            "capacity": {
                "concurrent_users": 100_000,
                "requests_per_user_per_second": 0.1,
                "peak_factor": 2,
                "read_ratio": 0.8,
                "write_ratio": 0.2,
                "sustainable_rps_per_instance": 1_000,
                "availability_slo": 0.9999,
            },
        },
    )
    assert result["provider_id"] == SYSTEM_DESIGN_PROVIDER_ID
    assert result["deterministic_first"] is True
    assert result["output"]["capacity"]["peak_rps"] == 20_000
    assert result["output"]["production_scale_verified"] is False
    assert runtime.routes()[0]["skill_id"] == SYSTEM_DESIGN_SKILL_ID


def test_bare_million_user_count_remains_unresolved_through_runtime(
    tmp_path: Path,
) -> None:
    runtime = _configured_runtime(tmp_path)
    result = runtime.execute(
        SYSTEM_DESIGN_AGENT_ID,
        SYSTEM_DESIGN_SKILL_ID,
        SYSTEM_DESIGN_CAPABILITY,
        {
            "system_id": "million-users",
            "availability_slo": 0.999,
            "capacity": {
                "concurrent_users": 1_000_000,
                "availability_slo": 0.999,
            },
        },
    )
    output = result["output"]
    assert output["capacity"]["peak_rps"] is None
    assert any(
        issue["code"] == "AMBIGUOUS_DEMAND"
        for issue in output["capacity"]["issues"]
    )


def test_runtime_rejects_conflicting_design_input(tmp_path: Path) -> None:
    runtime = _configured_runtime(tmp_path)
    with pytest.raises(RuntimeError):
        runtime.execute(
            SYSTEM_DESIGN_AGENT_ID,
            SYSTEM_DESIGN_SKILL_ID,
            SYSTEM_DESIGN_CAPABILITY,
            {
                "system_id": "bad",
                "availability_slo": 0.999,
                "capacity": {
                    "requests_per_second": 100,
                    "availability_slo": 0.99,
                },
            },
        )
