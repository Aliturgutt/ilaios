from __future__ import annotations

import json
from pathlib import Path
from typing import cast

CAPABILITY_ROOT = Path(__file__).resolve().parents[1] / "tools" / "code-intelligence"
EXPECTED_OPERATIONS = (
    "ci-repository-index",
    "ci-symbol-search",
    "ci-call-graph",
    "ci-dependency-analysis",
    "ci-impact-analysis",
    "ci-architecture-map",
    "ci-route-analysis",
    "ci-dead-code-candidates",
    "ci-coverage-check",
)


def _json(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    assert all(isinstance(key, str) for key in value)
    return cast(dict[str, object], value)


def test_manifest_and_request_schema_share_exact_operation_catalog() -> None:
    manifest = _json(CAPABILITY_ROOT / "manifest.json")
    request_schema = _json(CAPABILITY_ROOT / "schemas" / "request.schema.json")
    properties = request_schema["properties"]
    assert isinstance(properties, dict)
    operation = properties["operation"]
    assert isinstance(operation, dict)

    assert manifest["operations"] == list(EXPECTED_OPERATIONS)
    assert operation["enum"] == list(EXPECTED_OPERATIONS)


def test_manifest_references_existing_machine_readable_schemas() -> None:
    manifest = _json(CAPABILITY_ROOT / "manifest.json")
    schemas = manifest["schemas"]
    assert isinstance(schemas, dict)

    for relative in schemas.values():
        assert isinstance(relative, str)
        document = _json(CAPABILITY_ROOT / relative)
        assert document["$schema"] == "https://json-schema.org/draft/2020-12/schema"


def test_provenance_declares_first_party_clean_room_boundary() -> None:
    provenance = (CAPABILITY_ROOT / "PROVENANCE.md").read_text(encoding="utf-8")

    for marker in (
        "FIRST-PARTY ILAIOS IMPLEMENTATION",
        "INDEPENDENTLY AUTHORED",
        "CODE/TEXT IMPORTED = NONE",
        "RUNTIME DEPENDENCY ON `codebase-memory-mcp` = NONE",
    ):
        assert marker in provenance


def test_capability_is_read_only_and_has_no_external_runtime_dependencies() -> None:
    manifest = _json(CAPABILITY_ROOT / "manifest.json")

    assert manifest["mode"] == "read_only"
    assert manifest["external_runtime_dependencies"] == []
    forbidden = manifest["forbidden_actions"]
    assert isinstance(forbidden, list)
    assert "production_mutation" in forbidden
    assert "automatic_dead_code_deletion" in forbidden
    assert "unbounded_graph_query" in forbidden
