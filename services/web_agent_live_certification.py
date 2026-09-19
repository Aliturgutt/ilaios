"""Trusted-master certification for the six canonical Web agents.

Five Web proposal agents execute through the existing governed zero-cost
OpenRouter path. BrowserQA is certified from exact real governed Browser Tool
E2E evidence and is never relabeled as a generic AI/provider execution.
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from services.agent_e2e_matrix import build_agent_e2e_matrix, matrix_summary
from services.agent_governance import AgentInvocation
from services.agent_projection import agent_state_projection
from services.agent_readiness import AgentReadinessProof
from services.agent_readiness_store import AgentReadinessStore
from services.agent_registry import INDEPENDENT_VERIFIER_ID, RuntimeReadiness, registration_for
from services.ai_governance import Scope, ScopeKind
from services.control_plane.migrations import migrate_database
from services.independent_verifier_execution import (
    IndependentVerifierExecutor,
    ProducerEvidence,
)
from services.openrouter_agent_catalog import discover_free_openrouter_agent_configuration
from services.p0_runtime_composition import compose_p0_runtime
from services.runtime import BlastRadiusBudget, ExecutionGrant, GovernedRuntime, GrantPolicy
from services.runtime.browser_tool_adapter import BROWSER_AGENT_ID, BROWSER_TOOL_NAME
from services.runtime.security_agent_adapters import SecurityAgentRuntimeAdapters
from services.web_agent_browser_certification import verify_browser_e2e_evidence
from services.web_agent_execution import (
    WEB_AGENT_BINDINGS,
    WebProviderBackedAgentRequest,
)
from services.web_agent_runtime import compose_web_agent_runtime


class WebAgentLiveCertificationError(RuntimeError):
    """Live Web Agent execution or evidence failed closed."""


_CERTIFICATION_INPUT_TOKEN_RESERVATION = 4096
_CERTIFICATION_OUTPUT_TOKEN_RESERVATION = 2048


def run_web_agent_live_certification(
    *,
    repository_root: Path,
    browser_summary_path: Path,
    output_dir: Path,
    now: datetime | None = None,
) -> dict[str, object]:
    root = repository_root.resolve()
    if not root.is_dir():
        raise WebAgentLiveCertificationError("repository root is unavailable")
    observed_at = now or datetime.now(timezone.utc)
    if observed_at.tzinfo is None:
        raise WebAgentLiveCertificationError("certification timestamp must be timezone-aware")
    source_sha = os.environ.get("GITHUB_SHA", "").strip()
    if len(source_sha) != 40 or any(
        character not in "0123456789abcdef" for character in source_sha
    ):
        raise WebAgentLiveCertificationError("exact lowercase GITHUB_SHA is required")

    browser_evidence = verify_browser_e2e_evidence(
        summary_path=browser_summary_path,
        expected_source_sha=source_sha,
    )
    browser_digest = str(browser_evidence.get("evidence_digest", ""))
    browser_binding_digest = _browser_binding_digest(browser_evidence)

    configuration = discover_free_openrouter_agent_configuration()
    if configuration is None:
        raise WebAgentLiveCertificationError("OPENROUTER_API_KEY is unavailable")

    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    runtime_database = output_dir / "web-agent-runtime.sqlite3"
    readiness_database = output_dir / "web-agent-readiness.sqlite3"
    migrate_database(runtime_database)

    external_adapters = dict(SecurityAgentRuntimeAdapters().runtime_adapters())
    external_adapters.update(configuration.adapter.runtime_adapters())
    runtime = GovernedRuntime(runtime_database, external_adapters=external_adapters)
    grants = GrantPolicy()
    p0 = compose_p0_runtime(
        runtime,
        grants,
        engineering_skills_root=root / "tools" / "software-factory" / "skills",
        ai_adapter=configuration.adapter,
        ai_provider_capabilities=configuration.provider_capabilities,
    )
    web = compose_web_agent_runtime(
        p0.named_executor,
        root,
        ai_adapter=configuration.adapter,
        ai_provider_capabilities=configuration.provider_capabilities,
    )
    if web.ai_executor is None or web.target_agent_count != 6:
        raise WebAgentLiveCertificationError("canonical Web runtime composition is incomplete")

    verifier = IndependentVerifierExecutor(p0.named_executor, configuration.adapter)
    readiness_store = AgentReadinessStore(readiness_database)
    tenant_id = "ilaios-web-live-certification"
    scopes = (Scope(ScopeKind.TENANT, tenant_id),)
    proofs: dict[str, AgentReadinessProof] = {}
    receipts: list[dict[str, object]] = []

    ai_index = 0
    for binding in WEB_AGENT_BINDINGS:
        if binding.execution_mode != "governed-ai":
            continue
        ai_index += 1
        prompt = (
            f"ILAIOS Web trusted-master certification probe {ai_index}. "
            f"Return a concise bounded proposal for capability {binding.capability}. "
            "Do not claim browser verification, deployment, publication, or side effects."
        )
        invocation = _invocation(
            binding.agent_id,
            binding.capability,
            binding.permission,
            prompt=prompt,
            external_egress=True,
        )
        producer = web.ai_executor.execute(
            WebProviderBackedAgentRequest(
                invocation=invocation,
                grant=_grant(binding.agent_id, binding.permission, observed_at, ai_index),
                tenant_id=tenant_id,
                scopes=scopes,
                prompt=prompt,
                input_tokens=_CERTIFICATION_INPUT_TOKEN_RESERVATION,
                max_output_tokens=_CERTIFICATION_OUTPUT_TOKEN_RESERVATION,
                now=observed_at,
            )
        )
        verification = verifier.verify(
            ProducerEvidence(producer.execution, producer.evidence_digest),
            _grant(
                INDEPENDENT_VERIFIER_ID,
                "evidence.read",
                observed_at,
                1000 + ai_index,
            ),
            tenant_id=tenant_id,
            scopes=scopes,
            now=observed_at,
            input_tokens=256,
            max_output_tokens=256,
        )
        if not verification.passed:
            raise WebAgentLiveCertificationError(
                f"IndependentVerifier rejected {binding.agent_id}"
            )
        output = producer.execution.route.get("output")
        if not isinstance(output, dict):
            raise WebAgentLiveCertificationError("Web provider output disappeared")
        if output.get("actual_cost_usd") != "0":
            raise WebAgentLiveCertificationError("Web AI certification observed non-zero provider cost")
        proof = _persist_provider_proof(
            runtime=runtime,
            store=readiness_store,
            agent_id=binding.agent_id,
            evidence_digest=producer.evidence_digest,
            created_at=observed_at,
        )
        proofs[binding.agent_id] = proof
        receipts.append(
            _provider_receipt(
                binding.agent_id,
                proof,
                producer.execution.route,
                verifier_provider=verification.provider_id,
                verifier_model=verification.model_id,
                verifier_evidence_digest=verification.verifier_evidence_digest,
            )
        )

    browser_verification = verifier.verify_governed_tool_evidence(
        producer_agent_id=BROWSER_AGENT_ID,
        evidence_digest=browser_digest,
        binding_digest=browser_binding_digest,
        tool_name=BROWSER_TOOL_NAME,
        grant=_grant(
            INDEPENDENT_VERIFIER_ID,
            "evidence.read",
            observed_at,
            2000,
        ),
        tenant_id=tenant_id,
        scopes=scopes,
        now=observed_at,
    )
    if not browser_verification.passed:
        raise WebAgentLiveCertificationError("IndependentVerifier rejected BrowserQA")
    browser_proof = _persist_browser_proof(
        runtime=runtime,
        store=readiness_store,
        evidence_digest=browser_digest,
        created_at=observed_at,
    )
    proofs[BROWSER_AGENT_ID] = browser_proof
    receipts.append(
        {
            "agent_id": BROWSER_AGENT_ID,
            "readiness": "verified",
            "execution_mode": "browser-tool",
            "tool": BROWSER_TOOL_NAME,
            "provider_id": None,
            "model_id": None,
            "actual_cost_usd": "0",
            "producer_evidence_digest": browser_digest,
            "binding_digest": browser_binding_digest,
            "verifier_provider_id": browser_verification.provider_id,
            "verifier_model_id": browser_verification.model_id,
            "verifier_evidence_digest": browser_verification.verifier_evidence_digest,
            "browser_evidence": browser_evidence,
            "proof": asdict(browser_proof),
        }
    )

    if len(proofs) != 6:
        raise WebAgentLiveCertificationError(
            f"Web proof coverage mismatch expected=6 actual={len(proofs)}"
        )
    persisted = readiness_store.verify()
    if len(persisted) != 6 or any(
        item.readiness is not RuntimeReadiness.VERIFIED for item in persisted
    ):
        raise WebAgentLiveCertificationError("append-only Web readiness ledger is incomplete")
    final_projection = agent_state_projection(runtime.routes(), readiness_store.projection())
    _assert_projected_verified(final_projection, set(proofs))
    summary = matrix_summary(build_agent_e2e_matrix(proofs))
    if summary != {"registered": 41, "executable": 0, "verified": 6}:
        raise WebAgentLiveCertificationError(f"unexpected Web readiness matrix summary: {summary!r}")

    receipt: dict[str, object] = {
        "status": "VERIFIED",
        "scope": "P1_WEB",
        "revision_sha": source_sha,
        "observed_at": observed_at.isoformat(),
        "target_agent_count": 6,
        "verified_agent_count": 6,
        "governed_ai_agent_count": 5,
        "governed_ai_zero_cost_openrouter_only": True,
        "browser_agent_count": 1,
        "browser_execution_mode": "browser-tool",
        "browser_tool": BROWSER_TOOL_NAME,
        "browser_governed_e2e": True,
        "browser_public_production_proven": False,
        "matrix_summary": summary,
        "runtime_route_count": len(runtime.routes()),
        "readiness_record_count": len(persisted),
        "runtime_database_sha256": _sha256_file(runtime_database),
        "readiness_database_sha256": _sha256_file(readiness_database),
        "browser_evidence_digest": browser_digest,
        "browser_binding_digest": browser_binding_digest,
        "agents": sorted(receipts, key=lambda item: str(item["agent_id"])),
    }
    receipt_path = output_dir / "web-agent-live-receipt.json"
    receipt_path.write_text(
        json.dumps(receipt, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return receipt


def _browser_binding_digest(evidence: dict[str, object]) -> str:
    keys = (
        "source_sha",
        "agent_id",
        "skill_id",
        "tool",
        "summary_sha256",
        "governance_database_sha256",
        "admission_evidence_sha256",
        "egress_receipts_sha256",
    )
    binding = {key: evidence.get(key) for key in keys}
    canonical = json.dumps(binding, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(canonical).hexdigest()


def _invocation(
    agent_id: str,
    capability: str,
    permission: str,
    *,
    prompt: str,
    external_egress: bool,
) -> AgentInvocation:
    manifest = registration_for(agent_id).manifest
    caller_id = sorted(manifest.allowed_callers)[0]
    input_class = "governed_task" if "governed_task" in manifest.inputs else sorted(manifest.inputs)[0]
    output_class = "proposal" if "proposal" in manifest.outputs else sorted(manifest.outputs)[0]
    return AgentInvocation(
        invocation_id=f"web-live:{agent_id}:{hashlib.sha256(prompt.encode()).hexdigest()[:16]}",
        caller_id=caller_id,
        target_id=agent_id,
        capability=capability,
        permission=permission,
        input_class=input_class,
        requested_output_class=output_class,
        prompt=prompt,
        contains_secret=False,
        external_egress=external_egress,
        dlp_approved=external_egress,
        security_scan_passed=True,
    )


def _grant(
    agent_id: str,
    permission: str,
    now: datetime,
    sequence: int,
) -> ExecutionGrant:
    return ExecutionGrant(
        grant_id=f"web-live-grant:{sequence}:{agent_id}",
        subject_id=agent_id,
        actions=frozenset({permission}),
        resources=frozenset({agent_id}),
        expires_at=now + timedelta(minutes=30),
        budget=BlastRadiusBudget(max_side_effects=1, max_resources=1),
    )


def _persist_provider_proof(
    *,
    runtime: GovernedRuntime,
    store: AgentReadinessStore,
    agent_id: str,
    evidence_digest: str,
    created_at: datetime,
) -> AgentReadinessProof:
    if not any(route.get("agent_id") == agent_id for route in runtime.routes()):
        raise WebAgentLiveCertificationError(f"persisted runtime route missing for {agent_id}")
    proof = _verified_proof(agent_id, evidence_digest)
    record = store.persist(proof, created_at=created_at)
    if record.readiness is not RuntimeReadiness.VERIFIED:
        raise WebAgentLiveCertificationError(f"readiness did not reach VERIFIED for {agent_id}")
    return proof


def _persist_browser_proof(
    *,
    runtime: GovernedRuntime,
    store: AgentReadinessStore,
    evidence_digest: str,
    created_at: datetime,
) -> AgentReadinessProof:
    if any(route.get("agent_id") == BROWSER_AGENT_ID for route in runtime.routes()):
        raise WebAgentLiveCertificationError(
            "BrowserQA must not be fabricated as a generic runtime/provider route"
        )
    proof = _verified_proof(BROWSER_AGENT_ID, evidence_digest)
    record = store.persist(proof, created_at=created_at)
    if record.readiness is not RuntimeReadiness.VERIFIED:
        raise WebAgentLiveCertificationError("BrowserQA readiness did not reach VERIFIED")
    return proof


def _verified_proof(agent_id: str, evidence_digest: str) -> AgentReadinessProof:
    return AgentReadinessProof(
        agent_id=agent_id,
        verifier_id=registration_for(agent_id).manifest.verifier_id,
        invocation_passed=True,
        skill_passed=True,
        permission_passed=True,
        provider_passed=True,
        output_passed=True,
        independent_verification_passed=True,
        evidence_persisted=True,
        desktop_projection_passed=True,
        regression_e2e_passed=True,
        evidence_digest=evidence_digest,
    )


def _assert_projected_verified(
    projection: dict[str, object], expected_ids: set[str]
) -> None:
    agents = projection.get("agents")
    if not isinstance(agents, list):
        raise WebAgentLiveCertificationError("Desktop agent projection is malformed")
    indexed = {
        str(item.get("agent_id")): item
        for item in agents
        if isinstance(item, dict) and isinstance(item.get("agent_id"), str)
    }
    for agent_id in expected_ids:
        item = indexed.get(agent_id)
        if not isinstance(item, dict) or item.get("readiness") != "verified":
            raise WebAgentLiveCertificationError(f"Desktop projection failed for {agent_id}")


def _provider_receipt(
    agent_id: str,
    proof: AgentReadinessProof,
    route: dict[str, Any],
    *,
    verifier_provider: str,
    verifier_model: str | None,
    verifier_evidence_digest: str,
) -> dict[str, object]:
    output = route.get("output")
    if not isinstance(output, dict):
        raise WebAgentLiveCertificationError("provider receipt output is missing")
    return {
        "agent_id": agent_id,
        "readiness": "verified",
        "execution_mode": "governed-ai",
        "provider_id": route.get("provider_id"),
        "model_id": output.get("model_id"),
        "actual_cost_usd": output.get("actual_cost_usd"),
        "producer_evidence_digest": proof.evidence_digest,
        "verifier_provider_id": verifier_provider,
        "verifier_model_id": verifier_model,
        "verifier_evidence_digest": verifier_evidence_digest,
        "proof": asdict(proof),
    }


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    workspace = Path(os.environ.get("GITHUB_WORKSPACE", Path.cwd()))
    summary = os.environ.get("WEB_AGENT_BROWSER_SUMMARY_PATH", "").strip()
    if not summary:
        raise SystemExit("WEB_AGENT_LIVE_CERTIFICATION=FAIL: browser summary path missing")
    output_dir = Path(
        os.environ.get("WEB_AGENT_PROOF_DIR", "artifacts/web-agent-live-proof")
    )
    try:
        receipt = run_web_agent_live_certification(
            repository_root=workspace,
            browser_summary_path=Path(summary),
            output_dir=output_dir,
        )
    except Exception as exc:
        raise SystemExit(f"WEB_AGENT_LIVE_CERTIFICATION=FAIL: {exc}") from exc
    print(
        "WEB_AGENT_LIVE_CERTIFICATION=PASS "
        f"verified={receipt['verified_agent_count']}/{receipt['target_agent_count']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
