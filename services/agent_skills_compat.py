"""Governed compatibility boundary for the open Agent Skills folder format.

This module is intentionally not an execution engine. It parses and exports the
portable Agent Skills surface while preserving ILAIOS as the sole source of
execution authority. Imported scripts and declared tools remain untrusted until
canonical ILAIOS policy/approval/tool-gateway admission authorizes their use.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from types import MappingProxyType
from typing import Mapping

_NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_ALLOWED_TOP_LEVEL = frozenset(
    {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
)
_PORTABLE_DIRS = ("scripts", "references", "assets")


class AgentSkillsCompatibilityError(ValueError):
    """Portable Agent Skills input is malformed or violates the compatibility boundary."""


@dataclass(frozen=True, slots=True)
class AgentSkillMetadata:
    name: str
    description: str
    license: str | None
    compatibility: str | None
    metadata: Mapping[str, str]
    declared_allowed_tools: str | None


@dataclass(frozen=True, slots=True)
class AgentSkillResource:
    relative_path: str
    kind: str
    sha256: str
    size_bytes: int


@dataclass(frozen=True, slots=True)
class ImportedAgentSkill:
    root: Path
    metadata: AgentSkillMetadata
    instructions: str
    resources: tuple[AgentSkillResource, ...]
    package_sha256: str
    trust_state: str = "UNTRUSTED_CANDIDATE"

    @property
    def contains_scripts(self) -> bool:
        return any(resource.kind == "script" for resource in self.resources)

    @property
    def execution_authorized(self) -> bool:
        """Portable metadata can never grant ILAIOS execution authority."""
        return False

    def read_resource(self, relative_path: str, *, allow_scripts: bool = False) -> bytes:
        normalized = _safe_relative_path(relative_path)
        resource = next(
            (item for item in self.resources if item.relative_path == normalized), None
        )
        if resource is None:
            raise AgentSkillsCompatibilityError("resource is not part of the imported package")
        if resource.kind == "script" and not allow_scripts:
            raise AgentSkillsCompatibilityError(
                "imported scripts are untrusted and require governed execution admission"
            )
        target = (self.root / normalized).resolve()
        try:
            target.relative_to(self.root)
        except ValueError as error:
            raise AgentSkillsCompatibilityError("resource escaped the skill root") from error
        return target.read_bytes()


@dataclass(frozen=True, slots=True)
class NativeSkillExport:
    """Minimal ILAIOS-owned data needed to emit a portable Agent Skills surface."""

    ilaios_skill_id: str
    name: str
    description: str
    instructions: str
    license: str | None = None
    compatibility: str | None = None
    metadata: Mapping[str, str] | None = None


def load_agent_skill(root: Path) -> ImportedAgentSkill:
    """Load an Agent Skills folder without granting any execution permissions."""
    resolved = root.resolve()
    skill_file = resolved / "SKILL.md"
    if not resolved.is_dir() or not skill_file.is_file():
        raise AgentSkillsCompatibilityError("Agent Skills package requires SKILL.md")

    text = skill_file.read_text(encoding="utf-8")
    metadata, instructions = _parse_skill_md(text)
    if metadata.name != resolved.name:
        raise AgentSkillsCompatibilityError("Agent Skills name must match directory name")

    resources = _inventory_resources(resolved)
    digest = hashlib.sha256()
    digest.update(text.encode("utf-8"))
    for resource in resources:
        digest.update(resource.relative_path.encode("utf-8"))
        digest.update(resource.sha256.encode("ascii"))

    return ImportedAgentSkill(
        root=resolved,
        metadata=metadata,
        instructions=instructions,
        resources=resources,
        package_sha256=digest.hexdigest(),
    )


def discovery_metadata(root: Path) -> AgentSkillMetadata:
    """Read only discovery metadata; instructions/resources are not returned."""
    resolved = root.resolve()
    skill_file = resolved / "SKILL.md"
    if not resolved.is_dir() or not skill_file.is_file():
        raise AgentSkillsCompatibilityError("Agent Skills package requires SKILL.md")
    metadata, _ = _parse_skill_md(skill_file.read_text(encoding="utf-8"))
    if metadata.name != resolved.name:
        raise AgentSkillsCompatibilityError("Agent Skills name must match directory name")
    return metadata


def render_agent_skill(native: NativeSkillExport) -> str:
    """Render a portable SKILL.md without exporting ILAIOS execution authority."""
    _validate_name(native.name)
    _validate_description(native.description)
    if not native.instructions.strip():
        raise AgentSkillsCompatibilityError("exported instructions must be non-empty")
    if native.compatibility is not None:
        _validate_optional_text("compatibility", native.compatibility, 500)
    if native.license is not None and not native.license.strip():
        raise AgentSkillsCompatibilityError("license must be non-empty when provided")

    metadata = dict(native.metadata or {})
    metadata["ilaios.skill-id"] = native.ilaios_skill_id
    metadata["ilaios.authority"] = "portable-instructions-only"
    for key, value in metadata.items():
        if not isinstance(key, str) or not key.strip() or not isinstance(value, str):
            raise AgentSkillsCompatibilityError("export metadata must map strings to strings")

    lines = ["---", f"name: {_yaml_scalar(native.name)}", f"description: {_yaml_scalar(native.description)}"]
    if native.license is not None:
        lines.append(f"license: {_yaml_scalar(native.license)}")
    if native.compatibility is not None:
        lines.append(f"compatibility: {_yaml_scalar(native.compatibility)}")
    lines.append("metadata:")
    for key in sorted(metadata):
        lines.append(f"  {key}: {_yaml_scalar(metadata[key])}")
    lines.extend(["---", "", native.instructions.strip(), ""])
    return "\n".join(lines)


def export_agent_skill(native: NativeSkillExport, destination_root: Path) -> Path:
    """Create a new portable package containing only SKILL.md.

    Runtime code, permissions, secrets, approvals, evidence records, policy state and
    internal ILAIOS manifests are deliberately not exported by this boundary.
    """
    destination = destination_root.resolve() / native.name
    if destination.exists():
        raise AgentSkillsCompatibilityError("export destination already exists")
    destination.mkdir(parents=True)
    (destination / "SKILL.md").write_text(render_agent_skill(native), encoding="utf-8")
    return destination


def _parse_skill_md(text: str) -> tuple[AgentSkillMetadata, str]:
    if not text.startswith("---\n"):
        raise AgentSkillsCompatibilityError("SKILL.md requires YAML frontmatter")
    marker = text.find("\n---\n", 4)
    if marker < 0:
        raise AgentSkillsCompatibilityError("SKILL.md frontmatter is not closed")
    frontmatter = text[4:marker]
    instructions = text[marker + 5 :]
    document = _parse_frontmatter(frontmatter)

    unknown = set(document) - _ALLOWED_TOP_LEVEL
    if unknown:
        raise AgentSkillsCompatibilityError(
            f"unsupported Agent Skills frontmatter fields: {sorted(unknown)}"
        )

    name = _required_text(document, "name")
    description = _required_text(document, "description")
    _validate_name(name)
    _validate_description(description)

    license_value = _optional_text(document, "license")
    compatibility = _optional_text(document, "compatibility")
    if compatibility is not None:
        _validate_optional_text("compatibility", compatibility, 500)
    allowed_tools = _optional_text(document, "allowed-tools")

    raw_metadata = document.get("metadata", {})
    if not isinstance(raw_metadata, dict) or not all(
        isinstance(key, str) and isinstance(value, str)
        for key, value in raw_metadata.items()
    ):
        raise AgentSkillsCompatibilityError("metadata must map strings to strings")

    return (
        AgentSkillMetadata(
            name=name,
            description=description,
            license=license_value,
            compatibility=compatibility,
            metadata=MappingProxyType(dict(raw_metadata)),
            declared_allowed_tools=allowed_tools,
        ),
        instructions,
    )


def _parse_frontmatter(frontmatter: str) -> dict[str, object]:
    """Parse the conservative subset of YAML used by the Agent Skills spec.

    The compatibility boundary intentionally rejects complex YAML features rather
    than introducing executable/custom tags or a new dependency into Core.
    """
    result: dict[str, object] = {}
    current_map: dict[str, str] | None = None
    for line_number, raw in enumerate(frontmatter.splitlines(), start=1):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if raw.startswith("  "):
            if current_map is None:
                raise AgentSkillsCompatibilityError(
                    f"unexpected nested frontmatter at line {line_number}"
                )
            nested = raw.strip()
            if ":" not in nested:
                raise AgentSkillsCompatibilityError(
                    f"invalid metadata entry at line {line_number}"
                )
            key, value = nested.split(":", 1)
            key = key.strip()
            if not key or key in current_map:
                raise AgentSkillsCompatibilityError("metadata keys must be unique")
            current_map[key] = _decode_scalar(value.strip())
            continue
        if raw[0].isspace() or ":" not in raw:
            raise AgentSkillsCompatibilityError(f"invalid frontmatter at line {line_number}")
        key, value = raw.split(":", 1)
        key = key.strip()
        if not key or key in result:
            raise AgentSkillsCompatibilityError("frontmatter keys must be unique")
        value = value.strip()
        if not value:
            if key != "metadata":
                raise AgentSkillsCompatibilityError(f"{key} must not be empty")
            current_map = {}
            result[key] = current_map
        else:
            current_map = None
            result[key] = _decode_scalar(value)
    return result


def _decode_scalar(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        if value[0] == "'":
            return value[1:-1].replace("''", "'")
        body = value[1:-1]
        return (
            body.replace("\\n", "\n")
            .replace('\\"', '"')
            .replace("\\\\", "\\")
        )
    if value.startswith(("[", "{", "&", "*", "!", "|", ">")):
        raise AgentSkillsCompatibilityError("complex YAML is not accepted at the trust boundary")
    return value


def _inventory_resources(root: Path) -> tuple[AgentSkillResource, ...]:
    resources: list[AgentSkillResource] = []
    for directory in _PORTABLE_DIRS:
        base = root / directory
        if not base.exists():
            continue
        if not base.is_dir():
            raise AgentSkillsCompatibilityError(f"{directory} must be a directory")
        for path in sorted(item for item in base.rglob("*") if item.is_file()):
            resolved = path.resolve()
            try:
                relative = resolved.relative_to(root).as_posix()
            except ValueError as error:
                raise AgentSkillsCompatibilityError("resource escaped the skill root") from error
            payload = resolved.read_bytes()
            kind = "script" if directory == "scripts" else directory[:-1]
            resources.append(
                AgentSkillResource(
                    relative_path=relative,
                    kind=kind,
                    sha256=hashlib.sha256(payload).hexdigest(),
                    size_bytes=len(payload),
                )
            )
    return tuple(resources)


def _safe_relative_path(value: str) -> str:
    path = PurePosixPath(value.replace("\\", "/"))
    if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise AgentSkillsCompatibilityError("resource path must stay inside the skill root")
    return path.as_posix()


def _required_text(document: Mapping[str, object], key: str) -> str:
    value = document.get(key)
    if not isinstance(value, str) or not value.strip():
        raise AgentSkillsCompatibilityError(f"{key} must be a non-empty string")
    return value


def _optional_text(document: Mapping[str, object], key: str) -> str | None:
    value = document.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise AgentSkillsCompatibilityError(f"{key} must be a non-empty string when provided")
    return value


def _validate_name(name: str) -> None:
    if not (1 <= len(name) <= 64) or _NAME.fullmatch(name) is None or "--" in name:
        raise AgentSkillsCompatibilityError("Agent Skills name violates the open format")


def _validate_description(description: str) -> None:
    _validate_optional_text("description", description, 1024)


def _validate_optional_text(label: str, value: str, maximum: int) -> None:
    if not value.strip() or len(value) > maximum:
        raise AgentSkillsCompatibilityError(f"{label} length is invalid")


def _yaml_scalar(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    return f'"{escaped}"'
