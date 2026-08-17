"""Contract and provenance checks for the native system-design skill."""

from __future__ import annotations

import json
from pathlib import Path


_SKILL_ROOT = Path("skills/ilaios-system-design")


def test_skill_has_expected_owned_artifacts() -> None:
    expected = {
        "SKILL.md",
        "manifest.json",
        "rules/scalability.md",
        "rules/availability.md",
        "rules/caching.md",
        "rules/load-balancing.md",
        "rules/rate-limiting.md",
        "rules/queues.md",
        "rules/database-scaling.md",
        "rules/resiliency.md",
        "rules/security.md",
        "rules/observability.md",
        "schemas/architecture.schema.json",
        "schemas/capacity.schema.json",
        "templates/system-design.md",
        "templates/scaling-plan.md",
    }
    actual = {
        str(path.relative_to(_SKILL_ROOT))
        for path in _SKILL_ROOT.rglob("*")
        if path.is_file()
    }
    assert actual == expected


def test_skill_declares_clean_room_provenance_and_no_side_effects() -> None:
    skill = (_SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
    assert "Clean-room provenance" in skill
    assert "side_effects:** `none`" in skill
    assert "does not provision infrastructure" in skill
    assert "one million users" in skill


def test_architecture_schema_is_renderer_neutral_except_schema_contract() -> None:
    schema = json.loads(
        (_SKILL_ROOT / "schemas/architecture.schema.json").read_text(encoding="utf-8")
    )
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    required = set(schema["required"])
    assert {"nodes", "edges", "decisions", "risks", "diagram_contract"} <= required
    diagram = schema["properties"]["diagram_contract"]["properties"]
    assert diagram["consumer_skill"]["const"] == "ilaios-diagram-design"
    assert diagram["coupling"]["const"] == "schema_only"


def test_service_graph_schema_does_not_forbid_cycles() -> None:
    schema_text = (
        _SKILL_ROOT / "schemas/architecture.schema.json"
    ).read_text(encoding="utf-8")
    skill_text = (_SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
    assert "acyclic" not in schema_text.casefold()
    assert "execution\nDAG, which must remain acyclic" in skill_text
