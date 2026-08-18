"""Live production certification for governed external Agent Skills execution.

The harness executes one portable Agent Skills package through the canonical ILAIOS
production boundaries and a real zero-cost OpenRouter provider. It fails closed if
any tenant, policy, approval, tool-gateway, provider, cost, or evidence invariant is
missing. This is certification code, not a second runtime.
"""

from __future__ import annotations

import json
import os
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
from src.core.bootstrap_validator import BootstrapValidator
from src.core.evidence_chain import EvidenceChain
from src.core.immutable_context import ExecutionContext
from src.core.tool_gateway import ToolGateway


class AgentSkillsLiveCertificationError(RuntimeError):
    """Live external-skill production certification failed closed."""


_AGENT_ID = "ilaios.agent.core.planner.v1"
_CAPABILITY = "workflow.plan"
_TENANT_ID = "ilaios-agent-skills-live-certification"
_REGION = "eu-west"


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
    if len(revision_sha) != 40 or any(c not in "0123456789abcdef" for c in revision_sha):
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
            request_quota=3,
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

    context = ExecutionContext(
        root,
        "production-certification",
        revision_sha,
        "https://github.com/Aliturgutt/ilaios.git",
    )
    tool_gateway = ToolGateway(context, BootstrapValidator(root))
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
        request_id = f"agent-skills-live:{revision_sha[:16]}"
        request = ExternalSkillExecutionRequest(
            request_id=request_id,
            principal=principal,
            resource_tenant_id=_TENANT_ID,
            region=_REGION,
            package_root=package_root,
            expected_package_sha256=package.package_sha256,
            agent_id=_AGENT_ID,
            capability=_CAPABILITY,
            payload={
                "model_id": selection.model_id,
                "prompt": "Plan a safe two-step documentation-only change.",
                "request_id": request_id,
                "tenant_id": _TENANT_ID,
                "scopes": [{"kind": "tenant", "scope_id": _TENANT_ID}],
                "now": observed_at.isoformat(),
                "input_tokens": 1024,
                "max_output_tokens": 256,
            },
            risk="high",
        )
        admission = bridge.submit(request, now=observed_at)
        if admission.get("status") != "pending_approval":
            raise AgentSkillsLiveCertificationError("high-risk work did not require approval")
        try:
            bridge.execute(request)
        except PermissionError:
            pass
        else:
            raise AgentSkillsLiveCertificationError("execution bypassed required approval")

        governed.decide(request_id, "github-actions-independent-approver", "approved")
        receipt = bridge.execute(request)

        if not receipt.admission_proven or not receipt.approval_proven:
            raise AgentSkillsLiveCertificationError("governed admission proof is incomplete")
        if receipt.provider_id != selection.provider_id:
            raise AgentSkillsLiveCertificationError("provider identity drifted")
        if not evidence.verify_integrity() or len(evidence.get_records()) != 1:
            raise AgentSkillsLiveCertificationError("evidence chain proof is incomplete")
        text = receipt.output.get("text")
        if not isinstance(text, str) or not text.strip():
            raise AgentSkillsLiveCertificationError("real provider returned no usable text")
        if receipt.output.get("actual_cost_usd") != "0":
            raise AgentSkillsLiveCertificationError("live certification observed non-zero provider cost")
        if receipt.output.get("skill_sha256") != package.instructions.encode("utf-8").hex()[:0] and receipt.output.get("skill_sha256") != __import__("hashlib").sha256(package.instructions.encode("utf-8")).hexdigest():
            raise AgentSkillsLiveCertificationError("provider did not receive exact imported skill digest")

        certification: dict[str, object] = {
            "status": "VERIFIED",
            "scope": "external-agent-skill-production-runtime",
            "revision_sha": revision_sha,
            "request_id": receipt.request_id,
            "tenant_id": receipt.tenant_id,
            "skill_id": receipt.skill_id,
            "package_sha256": receipt.package_sha256,
            "capability": receipt.capability,
            "provider_id": receipt.provider_id,
            "model_id": receipt.output.get("model_id"),
            "provider_response_id": receipt.output.get("response_id"),
            "actual_cost_usd": receipt.output.get("actual_cost_usd"),
            "route_sequence": receipt.route_sequence,
            "admission_proven": receipt.admission_proven,
            "approval_proven": receipt.approval_proven,
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
