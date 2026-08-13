"""Fail closed when a legacy product identity appears outside reviewed provenance."""

from __future__ import annotations

import re
from pathlib import Path

from services.agent_registry import CANONICAL_AGENT_REGISTRY
from services.capability_registry import CAPABILITIES

ROOT = Path(__file__).resolve().parents[1]
LEGACY = re.compile(r"\b(?:hermes|ilakos|ilaten)\b", re.IGNORECASE)
TEXT_SUFFIXES = {
    ".csv", ".json", ".md", ".py", ".toml", ".txt", ".yaml", ".yml"
}

# Every entry is evidence-reviewed. A new file is UNKNOWN and therefore fails CI.
# Categories intentionally match the governance audit vocabulary.
ALLOWLIST: dict[str, tuple[str, str]] = {
    "apps/website/package-lock.json": (
        "THIRD_PARTY", "npm lock data for hermes-parser and hermes-estree"
    ),
    "dev/openclaw/": ("HISTORICAL", "controlled migration plans and decision evidence"),
    "docs/archive/": ("HISTORICAL", "archived pre-ILAIOS source material"),
    "docs/core/evidence_chain.md": ("HISTORICAL", "source-era Core specification"),
    "docs/governance/AGENT_ORGANIZATION.md": (
        "COMPATIBILITY", "lineage columns for canonical ILAIOS agents"
    ),
    "docs/governance/CAPABILITY_MATRIX.md": (
        "COMPATIBILITY", "lineage columns for canonical ILAIOS capabilities"
    ),
    "docs/governance/IP_LICENSE_PROVENANCE_AUDIT.md": (
        "HISTORICAL", "the controlling classification record"
    ),
    "docs/governance/RELEASE_VERSION_POLICY.md": (
        "HISTORICAL", "migration version history"
    ),
    "docs/governance/REPOSITORY_AUDIT_2026-08-11.md": (
        "HISTORICAL", "dated repository audit"
    ),
    "docs/governance/post_v1_dependency_graph.yaml": (
        "COMPATIBILITY", "lineage metadata for canonical capability dependencies"
    ),
    "docs/migration/": ("HISTORICAL", "migration matrices, reports, and registers"),
    "docs/platform/IDENTITY_MIGRATION.md": (
        "HISTORICAL", "bounded identity-migration record"
    ),
    "docs/platform/MIGRATION_BASELINE.md": (
        "HISTORICAL", "immutable pre-migration baseline"
    ),
    "docs/security/SECURITY_FACTORY.md": (
        "HISTORICAL", "explicit inherited-lineage statement"
    ),
    "docs/video_automation/": (
        "HISTORICAL", "source architecture labeled provenance-only"
    ),
    "evidence/migration/": ("HISTORICAL", "generated migration evidence"),
    "evidence/video_automation/": ("HISTORICAL", "source-era acceptance evidence"),
    "services/agent_registry.py": (
        "COMPATIBILITY", "read-only legacy_sources metadata"
    ),
    "services/capability_registry.py": (
        "COMPATIBILITY", "read-only legacy_sources metadata"
    ),
    "tests/": ("COMPATIBILITY", "regression assertions for lineage and canonical identity"),
    "tools/migration_audit.py": (
        "HISTORICAL", "deterministic ILATEN migration-evidence generator"
    ),
}


def _category(relative: str) -> tuple[str, str] | None:
    exact = ALLOWLIST.get(relative)
    if exact is not None:
        return exact
    matches = [value for prefix, value in ALLOWLIST.items() if prefix.endswith("/") and relative.startswith(prefix)]
    assert len(matches) <= 1, f"ambiguous legacy allowlist: {relative}"
    return matches[0] if matches else None


def _legacy_files() -> set[str]:
    found: set[str] = set()
    ignored_roots = {".git", ".mypy_cache", ".pytest_cache", ".ruff_cache", "__pycache__"}
    for path in ROOT.rglob("*"):
        if not path.is_file() or any(part in ignored_roots for part in path.parts):
            continue
        relative = path.relative_to(ROOT).as_posix()
        if LEGACY.search(relative):
            found.add(relative)
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if LEGACY.search(content):
            found.add(relative)
    return found


def test_active_capability_and_agent_namespaces_are_canonical() -> None:
    assert CAPABILITIES and CANONICAL_AGENT_REGISTRY
    assert all(item.capability_id.startswith("ilaios.capability.") for item in CAPABILITIES)
    assert all(item.manifest.agent_id.startswith("ilaios.agent.") for item in CANONICAL_AGENT_REGISTRY)
    assert all(not LEGACY.search(item.capability_id) for item in CAPABILITIES)
    assert all(not LEGACY.search(item.manifest.agent_id) for item in CANONICAL_AGENT_REGISTRY)
    assert all(not LEGACY.search(item.manifest.alias) for item in CANONICAL_AGENT_REGISTRY)


def test_current_public_identity_is_ilaios_only() -> None:
    for relative in ("README.md", "GOVERNANCE.md", "PROJECT_STATUS.md", "POST_CORE_ROADMAP.md"):
        path = ROOT / relative
        if not path.exists():
            continue
        content = path.read_text(encoding="utf-8")
        assert "ILAIOS" in content
        assert not LEGACY.search(content), f"active public identity leak: {relative}"


def test_repository_legacy_inventory_is_fully_classified() -> None:
    legacy_files = _legacy_files()
    unknown = sorted(relative for relative in legacy_files if _category(relative) is None)
    assert not unknown, "UNKNOWN legacy occurrences:\n" + "\n".join(unknown)
    assert all(_category(relative)[0] in {  # type: ignore[index]
        "COMPATIBILITY", "HISTORICAL", "LEGAL_ATTRIBUTION", "THIRD_PARTY"
    } for relative in legacy_files)


def test_every_allowlist_entry_has_a_documented_justification() -> None:
    assert all(category and justification for category, justification in ALLOWLIST.values())
    audit = (ROOT / "docs/governance/IP_LICENSE_PROVENANCE_AUDIT.md").read_text(encoding="utf-8")
    for prefix, (category, _) in ALLOWLIST.items():
        assert f"`{prefix}`" in audit, f"allowlist entry missing from audit: {prefix}"
        assert category in audit
    assert "UNKNOWN identity occurrences | 0" in audit
    assert "No parallel Core/runtime/registry was created" in audit
