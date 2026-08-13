"""Prevent legacy product identities from returning to active ILAIOS surfaces."""

from __future__ import annotations

import re
from pathlib import Path

from services.agent_registry import CANONICAL_CANONICAL_AGENT_REGISTRY
from services.capability_registry import CAPABILITIES

ROOT = Path(__file__).resolve().parents[1]
LEGACY = re.compile(r"\b(?:hermes|ilakos|ilaten)\b", re.IGNORECASE)
HISTORICAL_PREFIXES = (
    "dev/openclaw/migration_input/",
    "docs/migration/",
    "evidence/migration/",
)
COMPATIBILITY_FILES = {
    "services/agent_registry.py",
    "services/capability_registry.py",
}
CURRENT_PUBLIC_FILES = (
    "README.md",
    "GOVERNANCE.md",
    "PROJECT_STATUS.md",
    "POST_CORE_ROADMAP.md",
)


def test_active_capability_and_agent_namespaces_are_canonical() -> None:
    assert CAPABILITIES
    assert CANONICAL_AGENT_REGISTRY
    assert all(item.capability_id.startswith("ilaios.capability.") for item in CAPABILITIES)
    assert all(item.manifest.agent_id.startswith("ilaios.agent.") for item in CANONICAL_AGENT_REGISTRY)
    assert all(not LEGACY.search(item.capability_id) for item in CAPABILITIES)
    assert all(not LEGACY.search(item.manifest.agent_id) for item in CANONICAL_AGENT_REGISTRY)
    assert all(not LEGACY.search(item.manifest.alias) for item in CANONICAL_AGENT_REGISTRY)


def test_current_public_identity_is_ilaios_only() -> None:
    for relative in CURRENT_PUBLIC_FILES:
        path = ROOT / relative
        if not path.exists():
            continue
        content = path.read_text(encoding="utf-8")
        assert "ILAIOS" in content
        assert not LEGACY.search(content), f"active public identity leak: {relative}"


def test_active_source_paths_do_not_use_legacy_identity() -> None:
    for root_name in ("src", "services", "packages"):
        root = ROOT / root_name
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.is_dir():
                continue
            relative = path.relative_to(ROOT).as_posix()
            assert not LEGACY.search(relative), f"legacy active path: {relative}"
            if relative in COMPATIBILITY_FILES:
                continue
            if path.suffix in {".py", ".json", ".yaml", ".yml", ".toml"}:
                content = path.read_text(encoding="utf-8")
                assert not LEGACY.search(content), f"legacy active identifier: {relative}"


def test_historical_allowlist_is_explicit_and_labeled() -> None:
    assert HISTORICAL_PREFIXES == (
        "dev/openclaw/migration_input/",
        "docs/migration/",
        "evidence/migration/",
    )
    audit = (ROOT / "docs/governance/IP_LICENSE_PROVENANCE_AUDIT.md").read_text(
        encoding="utf-8"
    )
    for prefix in HISTORICAL_PREFIXES:
        assert prefix in audit
    for path in COMPATIBILITY_FILES:
        assert path in audit
    assert "UNKNOWN identity occurrences | 0" in audit
    assert "No parallel Core/runtime/registry was created" in audit
