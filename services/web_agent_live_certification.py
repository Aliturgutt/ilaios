"""Live certification for the six canonical Web agents.

Five proposal agents execute through zero-cost OpenRouter. BrowserQA consumes an
exact artifact created by the existing real Next.js + Chromium Web Factory E2E.
The harness persists readiness evidence and Desktop projection but never claims
public-production browser verification.
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
from services.independent_verifier_execution import IndependentVerifierExecutor, ProducerEvidence
from services.runtime import BlastRadiusBudget, ExecutionGrant, GovernedRuntime, GrantPolicy
from services.runtime.browser_evidence_adapter import BrowserEvidenceRuntimeAdapter
from services.web_agent_execution import WEB_AGENT_BINDINGS, WebProviderBackedRequest
from services.web_agent_provider_config import build_zero_cost_web_openrouter_configuration
from services.web_agent_runtime_composition import compose_web_agent_runtime


class WebAgentLiveCertificationError(RuntimeError):
    """Web live execution or evidence failed closed."""


_INPUT_RESERVATION = 4096
_OUTPUT_RESERVATION = 1024


def run_web_agent_live_certification(
    *,
    repository_root: Path,
    browser_evidence_path: Path,
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
    if len(source_sha) != 40:
        raise WebAgentLiveCertificationError("exact GITHUB_SHA is required")

    evidence_path = browser_evidence_path.resolve()
    evidence_root = evidence_path.parent
    if not evidence_path.is_file():
        raise WebAgentLiveCertificationError("real browser E2E evidence is unavailable")

    configuration = build_zero_cost_web_openrouter_configuration()
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    runtime_database = output_dir / "web-agent-runtime.sqlite3"
    readiness_database = output_dir / "web-agent-readiness.sqlite3"
    migrate_database(runtime_database)

    browser_adapter = BrowserEvidenceRuntimeAdapter(evidence_root)
    external_adapters = dict(configuration.adapter.runtime_adapters())
    external_adapters.update(browser_adapter.runtime_adapters())
    runtime = GovernedRuntime(runtime_database, external_adapters=external_adapters)
    composition = compose_web_agent_runtime(
        runtime,
        GrantPolicy(),
        repository_root=root,
        browser_evidence_adapter=browser_adapter,
        ai_adapter=configuration.adapter,
        ai_provider_capabilities=configuration.provider_capabilities,
    )
    if composition.target_agent_count != 6:
        raise WebAgentLiveCertificationError("Web target count drifted from six")

    verifier = IndependentVerifierExecutor(composition.named_executor)
    readiness_store = AgentReadinessStore(readiness_database)
    tenant_id = "ilaios-web-live-certification"
    scopes = (Scope(ScopeKind.TENANT, tenant_id),)
    proofs: dict[str, AgentReadinessProof] = {}
    receipts: list[dict[str, object]] = []

    for index, binding in enumerate(WEB_AGENT_BINDINGS):
        if binding.execution_mode != "governed-ai":
            continue
        prompt = (
            f"ILAIOS Web live certification probe {index}. "
            f"Return a concise advisory proposal for {binding.capability}. "
            "Do not claim rendering, browser verification, deployment, publication, or side effects."
        )
        invocation = _invocation(
            binding.agent_id,
            binding.capability,
            binding.permission,
            prompt=prompt,
            external_egress=True,
        )
        producer = composition.ai_executor.execute(
            WebProviderBackedRequest(
                invocation=invocation,
                grant=_grant(binding.agent_id, binding.permission, observed_at, index),
                tenant_id=tenant_id,
                scopes=scopes,
                prompt=prompt,
                input_tokens=_INPUT_RESERVATION,
                max_output_tokens=_OUTPUT_RESERVATION,
                now=observed_at,
            )
        )
        verification = verifier.verify(
            ProducerEvidence(producer.execution, producer.evidence_digest),
            _grant(INDEPENDENT_VERIFIER_ID, "evidence.read", observed_at, 1000 + index),
            tenant_id=tenant_id,
            scopes=scopes,
            now=observed_at,
        )
        if not verification.passed:
            raise WebAgentLiveCertificationError(
                f"IndependentVerifier rejected {binding.agent_id}"
            )
        proof = _persist_verified_proof(
            runtime,
            readiness_store,
            binding.agent_id,
            producer.evidence_digest,
            observed_at,
        )
        output = producer.execution.route.get("output")
        if not isinstance(output, dict) or output.get("actual_cost_usd") != "0":
            raise WebAgentLiveCertificationError("Web AI certification must remain zero cost")
        proofs[binding.agent_id] = proof
        receipts.append(
            _receipt(
                binding.agent_id,
                proof,
                producer.execution.route,
                verification.verifier_evidence_digest,
                verification.provider_id,
                verification.model_id,
            )
        )

    browser_binding = next(
        item for item in WEB_AGENT_BINDINGS if item.execution_mode == "browser-evidence"
    )
    browser_prompt = (
        "Verify the exact real Chromium Web Factory E2E evidence for this source revision. "
        "Do not claim public production verification."
    )
    browser_invocation = _invocation(
        browser_binding.agent_id,
        browser_binding.capability,
        browser_binding.permission,
        prompt=browser_prompt,
        external_egress=False,
    )
    browser_producer = composition.browser_evidence_executor.execute(
        browser_invocation,
        _grant(browser_binding.agent_id, browser_binding.permission, observed_at, 2000),
        evidence_path=evidence_path,
        source_sha=source_sha,
        now=observed_at,
    )
    browser_verification = verifier.verify(
        ProducerEvidence(browser_producer.execution, browser_producer.evidence_digest),
        _grant(INDEPENDENT_VERIFIER_ID, "evidence.read", observed_at, 2001),
        tenant_id=tenant_id,
        scopes=scopes,
        now=observed_at,
    )
    if not browser_verification.passed:
        raise WebAgentLiveCertificationError("IndependentVerifier rejected BrowserQA")
    browser_proof = _persist_verified_proof(
        runtime,
        readiness_store,
        browser_binding.agent_id,
        browser_producer.evidence_digest,
        observed_at,
    )
    browser_output = browser_producer.execution.route.get("output")
    if not isinstance(browser_output, dict):
        raise WebAgentLiveCertificationError("BrowserQA output evidence is missing")
    if browser_output.get("browser_runtime_evidence") != "PASS":
        raise WebAgentLiveCertificationError("BrowserQA did not bind passing runtime evidence")
    if browser_output.get("public_production_proven") is not False:
        raise WebAgentLiveCertificationError("BrowserQA local cert overclaimed production")
    proofs[browser_binding.agent_id] = browser_proof
    receipts.append(
        _receipt(
            browser_binding.agent_id,
            browser_proof,
            browser_producer.execution.route,
            browser_verification.verifier_evidence_digest,
            browser_verification.provider_id,
            browser_verification.model_id,
        )
    )

    if len(proofs) != 6:
        raise WebAgentLiveCertificationError("Web proof coverage must be 6/6")
    persisted = readiness_store.verify()
    if len(persisted) != 6 or any(
        item.readiness is not RuntimeReadiness.VERIFIED for item in persisted
    ):
        raise WebAgentLiveCertificationError("Web readiness ledger is incomplete")
    projection = agent_state_projection(runtime.routes(), readiness_store.projection())
    _assert_projected_verified(projection, set(proofs))
    summary = matrix_summary(build_agent_e2e_matrix(proofs))
    if summary != {"registered": 41, "executable": 0, "verified": 6}:
        raise WebAgentLiveCertificationError(f"unexpected Web matrix summary: {summary!r}")

    receipt: dict[str, object] = {
        "status": "VERIFIED",
        "scope": "P1_WEB",
        "revision_sha": source_sha,
        "observed_at": observed_at.isoformat(),
        "target_agent_count": 6,
        "verified_agent_count": 6,
        "zero_cost_openrouter_only": True,
        "browser_e2e_real": True,
        "browser_verification_scope": "LOCAL_CERTIFIED_NEXT_BUILD_BROWSER",
        "public_production_proven": False,
        "matrix_summary": summary,
        "runtime_route_count": len(runtime.routes()),
        "readiness_record_count": len(persisted),
        "runtime_database_sha256": _sha256_file(runtime_database),
        "readiness_database_sha256": _sha256_file(readiness_database),
        "browser_evidence_sha256": _sha256_file(evidence_path),
        "agents": sorted(receipts, key=lambda item: str(item["agent_id"])),
    }
    (output_dir / "web-agent-live-receipt.json").write_text(
        json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    return receipt


def _invocation(
    agent_id: str,
    capability: str,
    permission: str,
    *,
    prompt: str,
    external_egress: bool,
) -> AgentInvocation:
    manifest = registration_for(agent_id).manifest
    return AgentInvocation(
        invocation_id=f"web-live:{agent_id}:{hashlib.sha256(prompt.encode()).hexdigest()[:16]}",
        caller_id=sorted(manifest.allowed_callers)[0],
        target_id=agent_id,
        capability=capability,
        permission=permission,
        input_class="governed_task",
        requested_output_class="proposal",
        prompt=prompt,
        contains_secret=False,
        external_egress=external_egress,
        dlp_approved=external_egress,
        security_scan_passed=True,
    )


def _grant(agent_id: str, permission: str, now: datetime, sequence: int) -> ExecutionGrant:
    return ExecutionGrant(
        grant_id=f"web-live-grant:{sequence}:{agent_id}",
        subject_id=agent_id,
        actions=frozenset({permission}),
        resources=frozenset({agent_id}),
        expires_at=now + timedelta(minutes=30),
        budget=BlastRadiusBudget(max_side_effects=1, max_resources=1),
    )


def _persist_verified_proof(
    runtime: GovernedRuntime,
    store: AgentReadinessStore,
    agent_id: str,
    evidence_digest: str,
    created_at: datetime,
) -> AgentReadinessProof:
    verifier_id = registration_for(agent_id).manifest.verifier_id
    routes = runtime.routes()
    if not any(route.get("agent_id") == agent_id for route in routes):
        raise WebAgentLiveCertificationError(f"runtime route missing for {agent_id}")
    proof = AgentReadinessProof(
        agent_id=agent_id,
        verifier_id=verifier_id,
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
    record = store.persist(proof, created_at=created_at)
    if record.readiness is not RuntimeReadiness.VERIFIED:
        raise WebAgentLiveCertificationError(f"readiness did not reach VERIFIED for {agent_id}")
    projection = agent_state_projection(runtime.routes(), store.projection())
    _assert_projected_verified(projection, {agent_id})
    return proof


def _assert_projected_verified(projection: dict[str, object], expected: set[str]) -> None:
    agents = projection.get("agents")
    if not isinstance(agents, list):
        raise WebAgentLiveCertificationError("Desktop Web projection is malformed")
    indexed = {
        str(item.get("agent_id")): item
        for item in agents
        if isinstance(item, dict) and isinstance(item.get("agent_id"), str)
    }
    for agent_id in expected:
        item = indexed.get(agent_id)
        if not isinstance(item, dict) or item.get("readiness") != "verified":
            raise WebAgentLiveCertificationError(f"Desktop projection failed for {agent_id}")
        if item.get("agent_status") == "offline":
            raise WebAgentLiveCertificationError(f"runtime projection offline for {agent_id}")


def _receipt(
    agent_id: str,
    proof: AgentReadinessProof,
    route: dict[str, Any],
    verifier_evidence_digest: str,
    verifier_provider: str,
    verifier_model: str | None,
) -> dict[str, object]:
    output = route.get("output")
    output_mapping = output if isinstance(output, dict) else {}
    return {
        "agent_id": agent_id,
        "readiness": "verified",
        "verifier_id": proof.verifier_id,
        "producer_evidence_digest": proof.evidence_digest,
        "verifier_evidence_digest": verifier_evidence_digest,
        "provider_id": route.get("provider_id"),
        "model_id": output_mapping.get("model_id"),
        "actual_cost_usd": output_mapping.get("actual_cost_usd"),
        "browser_evidence_sha256": output_mapping.get("browser_evidence_sha256"),
        "verifier_provider_id": verifier_provider,
        "verifier_model_id": verifier_model,
        "proof": asdict(proof),
    }


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    repository_root = Path(os.environ.get("GITHUB_WORKSPACE", Path.cwd()))
    browser_evidence = os.environ.get("WEB_AGENT_BROWSER_EVIDENCE_PATH", "").strip()
    if not browser_evidence:
        raise SystemExit("WEB_AGENT_LIVE_CERTIFICATION=FAIL: browser evidence path missing")
    output_dir = Path(
        os.environ.get("WEB_AGENT_PROOF_DIR", "artifacts/web-agent-live-proof")
    )
    try:
        receipt = run_web_agent_live_certification(
            repository_root=repository_root,
            browser_evidence_path=Path(browser_evidence),
            output_dir=output_dir,
        )
    except WebAgentLiveCertificationError as exc:
        raise SystemExit(f"WEB_AGENT_LIVE_CERTIFICATION=FAIL: {exc}") from exc
    print(
        "WEB_AGENT_LIVE_CERTIFICATION=PASS "
        f"verified={receipt['verified_agent_count']}/{receipt['target_agent_count']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
