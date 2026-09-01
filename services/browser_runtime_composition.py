"""Additive composition for ILAIOS BrowserQA skills and governed browser tool."""
from __future__ import annotations

from pathlib import Path

from services.agent_registry import registration_for
from services.agent_skills_compat import discovery_metadata
from services.governance.runtime import GovernedRuntimeGateway
from services.named_agent_executor import NamedAgentExecutor
from services.runtime.browser_tool_adapter import (
    BROWSER_AGENT_ID,
    BROWSER_AUTOMATION_SKILL_ID,
    BROWSER_CAPABILITY,
    BrowserEgressBoundary,
    build_browser_tool_gateway,
)
from services.web_factory_skills import WEB_FACTORY_BROWSER_SKILL_IDS
from src.core.audit_engine import AuditEngine
from src.core.tool_gateway import ToolGateway


def ensure_web_factory_browser_skills(
    executor: NamedAgentExecutor, repository_root: Path
) -> dict[str, str]:
    registration = registration_for(BROWSER_AGENT_ID)
    if BROWSER_CAPABILITY not in registration.manifest.capabilities:
        raise ValueError("BrowserQA canonical capability drifted")
    if "authorized-site.read" not in registration.manifest.permissions:
        raise ValueError("BrowserQA read permission drifted")
    executor.ensure_agent(BROWSER_AGENT_ID)
    root = repository_root.resolve() / "tools" / "web-factory" / "browser-skills"
    digests: dict[str, str] = {}
    for skill_id in WEB_FACTORY_BROWSER_SKILL_IDS:
        package = root / skill_id
        metadata = discovery_metadata(package)
        if metadata.name != skill_id:
            raise ValueError("browser skill package identity drifted")
        instructions = (package / "SKILL.md").read_bytes()
        digests[skill_id] = executor.ensure_skill(
            skill_id, instructions, frozenset({BROWSER_CAPABILITY})
        )
    if BROWSER_AUTOMATION_SKILL_ID not in digests:
        raise ValueError("browser automation skill is not provisioned")
    return digests


def compose_browser_runtime(
    executor: NamedAgentExecutor,
    repository_root: Path,
    gateway: ToolGateway,
    governance: GovernedRuntimeGateway,
    governance_database_path: Path,
    allowed_origins: frozenset[str],
    egress: BrowserEgressBoundary,
    audit: AuditEngine,
    evidence_root: Path,
    *,
    executable: str = "playwright-cli",
    timeout_seconds: int = 60,
) -> dict[str, object]:
    """Compose browser support without replacing Core/Factory/runtime authorities."""
    digests = ensure_web_factory_browser_skills(executor, repository_root)
    build_browser_tool_gateway(
        gateway,
        governance,
        governance_database_path,
        allowed_origins,
        egress,
        audit,
        evidence_root,
        executable=executable,
        timeout_seconds=timeout_seconds,
    )
    return {
        "agent_id": BROWSER_AGENT_ID,
        "capability": BROWSER_CAPABILITY,
        "skill_digests": digests,
        "tool": "browser.playwright-cli",
        "egress_boundary_required": True,
        "state_changing_actions_enabled": True,
        "state_changing_actions_require_approval": True,
        "text_entry_actions_enabled": False,
    }
