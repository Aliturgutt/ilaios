from __future__ import annotations

from pathlib import Path

import pytest

from services.agent_skills_compat import (
    AgentSkillsCompatibilityError,
    NativeSkillExport,
    discovery_metadata,
    export_agent_skill,
    load_agent_skill,
    render_agent_skill,
)


def _write_skill(root: Path, name: str = "example-skill") -> Path:
    skill_root = root / name
    skill_root.mkdir()
    (skill_root / "SKILL.md").write_text(
        """---
name: example-skill
description: "Analyzes example inputs. Use for example analysis tasks."
license: Apache-2.0
compatibility: "Portable instructions only"
metadata:
  author: "ilaios-test"
  version: "1.0"
allowed-tools: "Read Bash(git:*)"
---

Follow the bounded example workflow.
""",
        encoding="utf-8",
    )
    return skill_root


def test_discovery_reads_metadata_without_granting_authority(tmp_path: Path) -> None:
    root = _write_skill(tmp_path)

    metadata = discovery_metadata(root)

    assert metadata.name == "example-skill"
    assert metadata.metadata["author"] == "ilaios-test"
    assert metadata.declared_allowed_tools == "Read Bash(git:*)"


def test_import_is_untrusted_and_scripts_fail_closed(tmp_path: Path) -> None:
    root = _write_skill(tmp_path)
    scripts = root / "scripts"
    scripts.mkdir()
    (scripts / "run.py").write_text("print('not executed')\n", encoding="utf-8")
    references = root / "references"
    references.mkdir()
    (references / "REFERENCE.md").write_text("Reference only.\n", encoding="utf-8")

    imported = load_agent_skill(root)

    assert imported.trust_state == "UNTRUSTED_CANDIDATE"
    assert imported.execution_authorized is False
    assert imported.contains_scripts is True
    assert imported.package_sha256
    assert imported.read_resource("references/REFERENCE.md") == b"Reference only.\n"
    with pytest.raises(AgentSkillsCompatibilityError, match="governed execution admission"):
        imported.read_resource("scripts/run.py")
    assert imported.read_resource("scripts/run.py", allow_scripts=True) == b"print('not executed')\n"


def test_import_rejects_directory_name_mismatch(tmp_path: Path) -> None:
    root = _write_skill(tmp_path, name="different-folder")

    with pytest.raises(AgentSkillsCompatibilityError, match="match directory"):
        load_agent_skill(root)


def test_import_rejects_invalid_open_format_name(tmp_path: Path) -> None:
    root = tmp_path / "bad--skill"
    root.mkdir()
    (root / "SKILL.md").write_text(
        "---\nname: bad--skill\ndescription: invalid name\n---\nbody\n",
        encoding="utf-8",
    )

    with pytest.raises(AgentSkillsCompatibilityError, match="violates the open format"):
        load_agent_skill(root)


def test_import_rejects_unknown_frontmatter_at_trust_boundary(tmp_path: Path) -> None:
    root = tmp_path / "example-skill"
    root.mkdir()
    (root / "SKILL.md").write_text(
        "---\nname: example-skill\ndescription: valid description\nprivileged: true\n---\nbody\n",
        encoding="utf-8",
    )

    with pytest.raises(AgentSkillsCompatibilityError, match="unsupported"):
        load_agent_skill(root)


def test_import_rejects_complex_yaml_features(tmp_path: Path) -> None:
    root = tmp_path / "example-skill"
    root.mkdir()
    (root / "SKILL.md").write_text(
        "---\nname: example-skill\ndescription: valid description\nmetadata:\n  unsafe: !tag payload\n---\nbody\n",
        encoding="utf-8",
    )

    with pytest.raises(AgentSkillsCompatibilityError, match="complex YAML"):
        load_agent_skill(root)


def test_resource_path_traversal_is_rejected(tmp_path: Path) -> None:
    root = _write_skill(tmp_path)
    assets = root / "assets"
    assets.mkdir()
    (assets / "template.txt").write_text("safe\n", encoding="utf-8")
    imported = load_agent_skill(root)

    with pytest.raises(AgentSkillsCompatibilityError, match="inside the skill root"):
        imported.read_resource("../secret.txt")


def test_render_export_adds_ilaios_portability_metadata_without_tool_grant() -> None:
    rendered = render_agent_skill(
        NativeSkillExport(
            ilaios_skill_id="ilaios.skill.example.v1",
            name="example-skill",
            description="Performs bounded example analysis. Use for example tasks.",
            instructions="Do bounded analysis and return evidence.",
            license="Proprietary",
            metadata={"version": "1.0"},
        )
    )

    assert "name: \"example-skill\"" in rendered
    assert "ilaios.skill-id: \"ilaios.skill.example.v1\"" in rendered
    assert "ilaios.authority: \"portable-instructions-only\"" in rendered
    assert "allowed-tools:" not in rendered


def test_export_round_trip_preserves_portable_surface(tmp_path: Path) -> None:
    destination = export_agent_skill(
        NativeSkillExport(
            ilaios_skill_id="ilaios.skill.example.v1",
            name="example-skill",
            description="Performs bounded example analysis. Use for example tasks.",
            instructions="Do bounded analysis and return evidence.",
            compatibility="Requires an Agent Skills compatible client.",
        ),
        tmp_path,
    )

    imported = load_agent_skill(destination)

    assert imported.metadata.name == "example-skill"
    assert imported.metadata.metadata["ilaios.skill-id"] == "ilaios.skill.example.v1"
    assert imported.metadata.metadata["ilaios.authority"] == "portable-instructions-only"
    assert imported.instructions.strip() == "Do bounded analysis and return evidence."
    assert imported.execution_authorized is False


def test_export_refuses_overwrite(tmp_path: Path) -> None:
    native = NativeSkillExport(
        ilaios_skill_id="ilaios.skill.example.v1",
        name="example-skill",
        description="Performs bounded example analysis. Use for example tasks.",
        instructions="Do bounded analysis.",
    )
    export_agent_skill(native, tmp_path)

    with pytest.raises(AgentSkillsCompatibilityError, match="already exists"):
        export_agent_skill(native, tmp_path)
