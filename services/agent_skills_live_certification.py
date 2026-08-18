"""Live production certification for governed external Agent Skills execution.

This harness executes a portable Agent Skills package through the canonical ILAIOS
runtime boundaries and a real zero-cost OpenRouter provider. It also proves that a
high-risk request cannot execute without approval. It is certification code, not a
second runtime or approval bypass.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from services.agent_registry import registration_for
from services.agent_skills_compat import load_agent_skill
from services.agent_skills_runtime import (
    AgentSkillsProductionRuntime,
    ExternalSkillExecutionRequest,
)
from services.cloud import DeploymentProfile, TenantBoundary, TenantPolicy
from services.control_plane.migrations import migrate_database
from services.governance.runtime import GovernedRuntimeGateway
from services.identity import (
    AuthorizationEngine,
    AuthorizationRule,
    IdentityKind,
    Principal,
)
from services.openrouter_agent_catalog import discover_free_openrouter_agent_configuration
from services.runtime import GovernedRuntime
from src.core.evidence_chain import EvidenceChain
from src.core.immutable_context import ExecutionContext
from src.core.tool_gateway import ToolGateway


class AgentSkillsLiveCertificationError(RuntimeError):
    """Live external-skill production certification failed closed."""


_AGENT_ID = "ilaios.agent.core.planner.v1"
_CAPABILITY = "workflow.plan"
_TENANT_ID = "ilaios-agent-skills-live-certification"
_REGION = "eu-west"
_ORIGIN = "https://github.com/Aliturgutt/ilaios.git"


class _ExactHeadValidator:
    """Validate immutable repository identity while allowing detached CI HEAD."""

    def __init__(self, repository_root: Path, revision_sha: str) -> None:
        self._root = repository_root.resolve()
        self._revision_sha = revision_sha

    def validate_git_identity(self) -> Path:
        observed_root = Path(self._git("rev-parse", "--show-toplevel")).resolve()
        observed_head = self._git("rev-parse", "HEAD")
        observed_origin = self._git("remote", "get-url", "origin")
        if observed_root != self._root:
            raise AgentSkillsLiveCertificationError("repository root identity drifted")
        if observed_head != self._revision_sha:
            raise AgentSkillsLiveCertificationError("repository HEAD identity drifted")
        if observed_origin.removesuffix(".git") != _ORIGIN.removesuffix(".git"):
            raise AgentSkillsLiveCertificationError("repository origin identity drifted")
        return observed_root

    def _git(self, *args: str) -> str:
        try:
            completed = subprocess.run(
                ["git", *args],
                cwd=self._root,
                check=True,
                capture_output=True,
                text=True,
                timeout=20,
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            raise AgentSkillsLiveCertificationError("git identity validation failed") from exc
        value = completed.stdout.strip()
        if not value:
            raise AgentSkillsLiveCertificationError("git identity evidence is empty")
        return value


def run_agent_skills_live_certification(
    *,
    repository_root: Path,
    output_dir: Path,
    now: datetime | None = None,
) -> dict[str, object]:
    root = repository_root.resolve()
    if not root.is_dir():
        raise AgentSkillsLiveCertificationError("repository root is unavailable")
    observed_at = now or datetime.now(timezone.utc)
    if observed_at.tzinfo is None:
        raise AgentSkillsLiveCertificationError("certification time must be timezone-aware")

    revision_sha = os.environ.get("GITHUB_SHA", "").strip()
    if len(revision_sha) != 40 or any(
        character not in "0123456789abcdef" for character in revision_sha
    ):
        raise AgentSkillsLiveCertificationError("exact GITHUB_SHA is required")

    configuration = discover_free_openrouter_agent_configuration()
    if configuration is None:
        raise AgentSkillsLiveCertificationError("OPENROUTER_API_KEY is unavailable")
    selection = configuration.adapter.select(_CAPABILITY)
    provider_capabilities = configuration.provider_capabilities.get(selection.provider_id)
    if provider_capabilities is None or _CAPABILITY not in provider_capabilities:
        raise AgentSkillsLiveCertificationError("selected provider lacks required capability")

    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    database = output_dir / "agent-skills-live-runtime.sqlite3"
    migrate_database(database)

    runtime = GovernedRuntime(
        database,
        external_adapters=dict(configuration.adapter.runtime_adapters()),
    )
    manifest = registration_for(_AGENT_ID).manifest
    if _CAPABILITY not in manifest.capabilities:
        raise AgentSkillsLiveCertificationError("canonical planner capability drifted")
    runtime.register_agent(_AGENT_ID, frozenset({_CAPABILITY}))
    runtime.register_provider(
        selection.provider_id,
        provider_capabilities,
        adapter_kind=configuration.adapter.adapter_kind(selection.provider_id),
        deterministic=False,
    )
    governed = GovernedRuntimeGateway(database, runtime, hard_cap_minor=0)

    tenants = TenantBoundary()
    tenants.register(
        TenantPolicy(
            tenant_id=_TENANT_ID,
            region=_REGION,
            profile=DeploymentProfile.SHARED,
            request_quota=4,
            billing_account="agent-skills-live-certification",
        )
    )
    authorization = AuthorizationEngine(
        (
            AuthorizationRule(
                action="skill.execute.external",
                roles=frozenset({"production-certifier"}),
            ),
        )
    )
    principal = Principal(
        principal_id="github-actions-production-certifier",
        tenant_id=_TENANT_ID,
        kind=IdentityKind.HUMAN,
        roles=frozenset({"production-certifier"}),
        attributes=frozenset(),
        authentication_methods=frozenset({"mfa"}),
    )

    context = ExecutionContext(root, "production-certification", revision_sha, _ORIGIN)
    tool_gateway = ToolGateway(context, _ExactHeadValidator(root, revision_sha))
    evidence = EvidenceChain()
    bridge = AgentSkillsProductionRuntime(
        runtime=runtime,
        governed_gateway=governed,
        tool_gateway=tool_gateway,
        authorization=authorization,
        tenants=tenants,
        evidence_chain=evidence,
    )

    with tempfile.TemporaryDirectory(prefix="ilaios-agent-skill-live-") as raw_skill:
        package_root = Path(raw_skill) / "production-plan-probe"
        package_root.mkdir()
        (package_root / "SKILL.md").write_text(
            """---
name: production-plan-probe
description: Produce one concise bounded implementation plan for live ILAIOS external-skill certification.
---
You are a bounded planning skill. Return a concise implementation plan only. Do not claim side effects, deployment, verification, credentials, or approvals.
""",
            encoding="utf-8",
        )
        package = load_agent_skill(package_root)
        instruction_sha256 = hashlib.sha256(
            package.instructions.encode("utf-8")
        ).hexdigest()

        high_risk_request = _request(
            package_root=package_root,
            package_sha256=package.package_sha256,
            principal=principal,
            model_id=selection.model_id,
            observed_at=observed_at,
            request_id=f"agent-skills-live-high:{revision_sha[:16]}",
            risk="high",
        )
        high_admission = bridge.submit(high_risk_request, now=observed_at)
        if high_admission.get("status") != "pending_approval":
            raise AgentSkillsLiveCertificationError(
                "high-risk external skill did not require durable approval"
            )
        try:
            bridge.execute(high_risk_request)
        except PermissionError:
            high_risk_blocked = True
        else:
            raise AgentSkillsLiveCertificationError(
                "high-risk external skill bypassed durable approval"
            )

        live_request = _request(
            package_root=package_root,
            package_sha256=package.package_sha256,
            principal=principal,
            model_id=selection.model_id,
            observed_at=observed_at,
            request_id=f"agent-skills-live-provider:{revision_sha[:16]}",
            risk="low",
        )
        live_admission = bridge.submit(live_request, now=observed_at)
        if live_admission.get("status") != "admitted":
            raise AgentSkillsLiveCertificationError("low-risk live request was not admitted")
        receipt = bridge.execute(live_request)

        if not receipt.admission_proven or receipt.approval_proven:
            raise AgentSkillsLiveCertificationError("low-risk admission evidence is invalid")
        if receipt.provider_id != selection.provider_id:
            raise AgentSkillsLiveCertificationError("provider identity drifted")
        if not evidence.verify_integrity() or len(evidence.get_records()) != 1:
            raise AgentSkillsLiveCertificationError("evidence chain proof is incomplete")
        text = receipt.output.get("text")
        if not isinstance(text, str) or not text.strip():
            raise AgentSkillsLiveCertificationError("real provider returned no usable text")
        if receipt.output.get("actual_cost_usd") != "0":
            raise AgentSkillsLiveCertificationError(
                "live certification observed non-zero provider cost"
            )
        if receipt.output.get("skill_sha256") != instruction_sha256:
            raise AgentSkillsLiveCertificationError(
                "provider did not receive the exact imported skill digest"
            )
        response_id = receipt.output.get("response_id")
        if not isinstance(response_id, str) or not response_id.strip():
            raise AgentSkillsLiveCertificationError("provider response identity is missing")

        certification: dict[str, object] = {
            "status": "VERIFIED",
            "scope": "external-agent-skill-production-runtime",
            "revision_sha": revision_sha,
            "request_id": receipt.request_id,
            "tenant_id": receipt.tenant_id,
            "skill_id": receipt.skill_id,
            "package_sha256": receipt.package_sha256,
            "instruction_sha256": instruction_sha256,
            "capability": receipt.capability,
            "provider_id": receipt.provider_id,
            "model_id": receipt.output.get("model_id"),
            "provider_response_id": response_id,
            "actual_cost_usd": receipt.output.get("actual_cost_usd"),
            "route_sequence": receipt.route_sequence,
            "admission_proven": receipt.admission_proven,
            "approval_required_for_live_request": False,
            "high_risk_blocked_without_approval": high_risk_blocked,
            "tool_gateway_proven": True,
            "evidence_chain_hash": receipt.evidence_chain_hash,
            "evidence_chain_integrity": evidence.verify_integrity(),
            "script_execution_authorized": False,
            "observed_at": observed_at.isoformat(),
        }

    receipt_path = output_dir / "agent-skills-live-receipt.json"
    receipt_path.write_text(
        json.dumps(certification, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return certification


def _request(
    *,
    package_root: Path,
    package_sha256: str,
    principal: Principal,
    model_id: str,
    observed_at: datetime,
    request_id: str,
    risk: str,
) -> ExternalSkillExecutionRequest:
    return ExternalSkillExecutionRequest(
        request_id=request_id,
        principal=principal,
        resource_tenant_id=_TENANT_ID,
        region=_REGION,
        package_root=package_root,
        expected_package_sha256=package_sha256,
        agent_id=_AGENT_ID,
        capability=_CAPABILITY,
        payload={
            "model_id": model_id,
            "prompt": "Plan a safe two-step documentation-only change.",
            "request_id": request_id,
            "tenant_id": _TENANT_ID,
            "scopes": [{"kind": "tenant", "scope_id": _TENANT_ID}],
            "now": observed_at.isoformat(),
            "input_tokens": 4096,
            "max_output_tokens": 256,
        },
        risk=risk,
    )


def main() -> None:
    root = Path.cwd().resolve()
    output = Path(
        os.environ.get(
            "AGENT_SKILLS_LIVE_PROOF_DIR",
            "artifacts/agent-skills-live-proof",
        )
    )
    receipt = run_agent_skills_live_certification(
        repository_root=root,
        output_dir=output,
    )
    print(
        "AGENT_SKILLS_LIVE_CERTIFICATION="
        f"{receipt['status']} provider={receipt['provider_id']} sha={receipt['revision_sha']}"
    )


if __name__ == "__main__":
    main()
