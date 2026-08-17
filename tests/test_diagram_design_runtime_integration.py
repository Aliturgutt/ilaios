"""Governed runtime E2E tests for the ILAIOS diagram-design skill."""

from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path
from typing import Any

import pytest

from services.agent_registry import CANONICAL_AGENT_REGISTRY
from services.runtime.diagram_design_adapter import (
    DIAGRAM_DESIGN_ADAPTER_KIND,
    DIAGRAM_DESIGN_AGENT_ID,
    DIAGRAM_DESIGN_CAPABILITY,
    DIAGRAM_DESIGN_PROVIDER_ID,
    DIAGRAM_DESIGN_SKILL_ID,
)
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
        DIAGRAM_DESIGN_AGENT_ID, frozenset({DIAGRAM_DESIGN_CAPABILITY})
    )
    runtime.register_skill(
        DIAGRAM_DESIGN_SKILL_ID,
        b"ILAIOS native diagram-design skill v0.1.0",
        frozenset({DIAGRAM_DESIGN_CAPABILITY}),
    )
    runtime.register_provider(
        DIAGRAM_DESIGN_PROVIDER_ID,
        frozenset({DIAGRAM_DESIGN_CAPABILITY}),
        adapter_kind=DIAGRAM_DESIGN_ADAPTER_KIND,
    )
    return runtime


def _spec() -> dict[str, Any]:
    return {
        "title": "Governed Diagram Runtime",
        "description": "Deterministic direct governed-runtime E2E",
        "kind": "architecture",
        "direction": "LR",
        "width": 1200,
        "height": 720,
        "nodes": [
            {
                "id": "goal",
                "label": "Authenticated Goal",
                "kind": "input",
                "focal": True,
            },
            {
                "id": "runtime",
                "label": "Governed Runtime",
                "kind": "control",
            },
            {
                "id": "artifact",
                "label": "Verified Artifact",
                "kind": "output",
            },
        ],
        "edges": [
            {"source": "goal", "target": "runtime", "label": "admit"},
            {"source": "runtime", "target": "artifact", "label": "render"},
        ],
    }


def test_diagram_design_binds_to_existing_web_asset_agent() -> None:
    registrations = {
        item.manifest.agent_id: item for item in CANONICAL_AGENT_REGISTRY
    }
    asset_agent = registrations[DIAGRAM_DESIGN_AGENT_ID]
    assert DIAGRAM_DESIGN_CAPABILITY in asset_agent.manifest.capabilities
    assert asset_agent.backing_capability == "web-factory"


def test_governed_runtime_renders_svg_and_persists_hash_evidence(
    tmp_path: Path,
) -> None:
    runtime = _configured_runtime(tmp_path)
    result = runtime.execute(
        DIAGRAM_DESIGN_AGENT_ID,
        DIAGRAM_DESIGN_SKILL_ID,
        DIAGRAM_DESIGN_CAPABILITY,
        {"spec": _spec(), "format": "svg"},
    )

    output = result["output"]
    assert result["provider_id"] == DIAGRAM_DESIGN_PROVIDER_ID
    assert result["deterministic_first"] is True
    assert result["skill_id"] == DIAGRAM_DESIGN_SKILL_ID
    assert output["mime_type"] == "image/svg+xml"
    assert output["content"].startswith("<svg ")
    expected_hash = hashlib.sha256(output["content"].encode("utf-8")).hexdigest()
    assert output["artifact_sha256"] == expected_hash
    assert output["svg_sha256"] == expected_hash
    assert len(output["spec_sha256"]) == 64
    assert output["checks"]
    assert output["maturity"] == "IMPLEMENTED"

    route = runtime.routes()[0]
    assert route["skill_id"] == DIAGRAM_DESIGN_SKILL_ID
    assert route["provider_id"] == DIAGRAM_DESIGN_PROVIDER_ID
    assert route["output"]["artifact_sha256"] == expected_hash


def test_governed_runtime_renders_html_with_final_content_hash(tmp_path: Path) -> None:
    runtime = _configured_runtime(tmp_path)
    result = runtime.execute(
        DIAGRAM_DESIGN_AGENT_ID,
        DIAGRAM_DESIGN_SKILL_ID,
        DIAGRAM_DESIGN_CAPABILITY,
        {"spec": _spec(), "format": "html"},
    )

    output = result["output"]
    assert output["mime_type"] == "text/html"
    assert output["content"].startswith("<!doctype html>")
    assert "<svg " in output["content"]
    expected_hash = hashlib.sha256(output["content"].encode("utf-8")).hexdigest()
    assert output["artifact_sha256"] == expected_hash
    assert output["svg_sha256"] != expected_hash


def test_runtime_escapes_user_markup_before_persisting_artifact(tmp_path: Path) -> None:
    runtime = _configured_runtime(tmp_path)
    spec = _spec()
    spec["nodes"][0]["label"] = "User <script>alert(1)</script>"
    result = runtime.execute(
        DIAGRAM_DESIGN_AGENT_ID,
        DIAGRAM_DESIGN_SKILL_ID,
        DIAGRAM_DESIGN_CAPABILITY,
        {"spec": spec, "format": "svg"},
    )
    content = result["output"]["content"]
    assert "<script>" not in content
    assert "&lt;script&gt;" in content


def test_runtime_rejects_authority_shaped_or_unsupported_payload_fields(
    tmp_path: Path,
) -> None:
    runtime = _configured_runtime(tmp_path)
    with pytest.raises(RuntimeError, match="unsupported fields"):
        runtime.execute(
            DIAGRAM_DESIGN_AGENT_ID,
            DIAGRAM_DESIGN_SKILL_ID,
            DIAGRAM_DESIGN_CAPABILITY,
            {"spec": _spec(), "format": "svg", "output_path": "/tmp/escape.svg"},
        )
    with pytest.raises(RuntimeError, match="exactly svg or html"):
        runtime.execute(
            DIAGRAM_DESIGN_AGENT_ID,
            DIAGRAM_DESIGN_SKILL_ID,
            DIAGRAM_DESIGN_CAPABILITY,
            {"spec": _spec(), "format": "png"},
        )


def test_diagram_and_system_design_providers_cannot_cross_route(tmp_path: Path) -> None:
    database = tmp_path / "runtime.sqlite3"
    _runtime_database(database)
    runtime = GovernedRuntime(database)
    runtime.register_agent(
        DIAGRAM_DESIGN_AGENT_ID, frozenset({DIAGRAM_DESIGN_CAPABILITY})
    )
    runtime.register_agent(
        SYSTEM_DESIGN_AGENT_ID, frozenset({SYSTEM_DESIGN_CAPABILITY})
    )
    runtime.register_skill(
        DIAGRAM_DESIGN_SKILL_ID,
        b"ILAIOS native diagram-design skill v0.1.0",
        frozenset({DIAGRAM_DESIGN_CAPABILITY}),
    )
    runtime.register_skill(
        SYSTEM_DESIGN_SKILL_ID,
        b"ILAIOS native system-design skill v0.1.0",
        frozenset({SYSTEM_DESIGN_CAPABILITY}),
    )
    runtime.register_provider(
        DIAGRAM_DESIGN_PROVIDER_ID,
        frozenset({DIAGRAM_DESIGN_CAPABILITY}),
        adapter_kind=DIAGRAM_DESIGN_ADAPTER_KIND,
    )
    runtime.register_provider(
        SYSTEM_DESIGN_PROVIDER_ID,
        frozenset({SYSTEM_DESIGN_CAPABILITY}),
        adapter_kind=SYSTEM_DESIGN_ADAPTER_KIND,
    )

    diagram = runtime.execute(
        DIAGRAM_DESIGN_AGENT_ID,
        DIAGRAM_DESIGN_SKILL_ID,
        DIAGRAM_DESIGN_CAPABILITY,
        {"spec": _spec(), "format": "svg"},
    )
    system = runtime.execute(
        SYSTEM_DESIGN_AGENT_ID,
        SYSTEM_DESIGN_SKILL_ID,
        SYSTEM_DESIGN_CAPABILITY,
        {
            "system_id": "route-isolation",
            "availability_slo": 0.999,
            "capacity": {
                "requests_per_second": 100,
                "read_ratio": 0.8,
                "write_ratio": 0.2,
                "availability_slo": 0.999,
            },
        },
    )

    assert diagram["provider_id"] == DIAGRAM_DESIGN_PROVIDER_ID
    assert system["provider_id"] == SYSTEM_DESIGN_PROVIDER_ID
