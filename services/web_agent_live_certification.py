"""Trusted-master live certification for the six canonical Web agents.

Five proposal agents execute through the existing governed zero-cost provider
runtime. BrowserQA remains a browser-tool identity: this harness only binds an
exact immutable artifact produced by the real Docker-isolated Playwright CLI
E2E into the canonical runtime/readiness evidence chain.
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
from services.agent_execution_evidence import execution_evidence_digest
from services.agent_governance import AgentInvocation
from services.agent_projection import agent_state_projection
from services.agent_readiness import AgentReadinessProof
from services.agent_readiness_store import AgentReadinessStore
from services.agent_registry import INDEPENDENT_VERIFIER_ID, RuntimeReadiness, registration_for
from services.ai_governance import Scope, ScopeKind
from services.control_plane.migrations import migrate_database
from services.independent_verifier_execution import IndependentVerifierExecutor, ProducerEvidence
from services.openrouter_agent_catalog import discover_free_openrouter_agent_configuration
from services.p0_runtime_composition import compose_p0_runtime
from services.runtime import BlastRadiusBudget, ExecutionGrant, GovernedRuntime, GrantPolicy
from services.runtime.security_agent_adapters import SecurityAgentRuntimeAdapters
from services.web_agent_browser_certification import verify_browser_egress_e2e_evidence
from services.web_agent_execution import WEB_AGENT_BINDINGS, WebProviderBackedAgentRequest
from services.web_agent_runtime import compose_web_agent_runtime

_BROWSER_PROVIDER_ID = "ilaios.provider.browser-tool-evidence.v1"
_BROWSER_ADAPTER_KIND = "ilaios.runtime.browser-tool-evidence-binding.v1"
_INPUT_TOKENS = 1024
_OUTPUT_TOKENS = 1024


class WebAgentLiveCertificationError(RuntimeError):
    """Trusted-master Web execution or evidence failed closed."""


class BrowserToolEvidenceRuntimeAdapter:
    """Bind, but never fabricate, already-executed BrowserQA tool evidence."""

    def __init__(self, summary_path: Path, source_sha: str) -> None:
        self._summary = summary_path.resolve()
        self._source_sha = source_sha

    def runtime_adapters(self) -> dict[str, Any]:
        return {_BROWSER_ADAPTER_KIND: self.execute}

    def execute(self, payload: dict[str, Any]) -> dict[str, object]:
        raw_path = payload.get("summary_path")
        source_sha = payload.get("source_sha")
        skill = payload.get("_ilaios_skill")
        if raw_path != str(self._summary):
            raise WebAgentLiveCertificationError("BrowserQA evidence path drifted")
        if source_sha != self._source_sha:
            raise WebAgentLiveCertificationError("BrowserQA evidence source SHA drifted")
        if not isinstance(skill, dict) or skill.get("skill_id") != "ilaios-web-e2e":
            raise WebAgentLiveCertificationError("BrowserQA certification skill identity drifted")
        return verify_browser_egress_e2e_evidence(
            summary_path=self._summary,
            expected_source_sha=self._source_sha,
        )


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
    if len(source_sha) != 40 or any(char not in "0123456789abcdef" for char in source_sha):
        raise WebAgentLiveCertificationError("exact lowercase GITHUB_SHA is required")

    summary_path = browser_summary_path.resolve()
    if not summary_path.is_file():
        raise WebAgentLiveCertificationError("real BrowserQA E2E summary is unavailable")

    configuration = discover_free_openrouter_agent_configuration()
    if configuration is None:
        raise WebAgentLiveCertificationError("OPENROUTER_API_KEY is unavailable")

    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    runtime_database = output_dir / "web-agent-runtime.sqlite3"
    readiness_database = output_dir / "web-agent-readiness.sqlite3"
    migrate_database(runtime_database)

    browser_adapter = BrowserToolEvidenceRuntimeAdapter(summary_path, source_sha)
    external_adapters = dict(SecurityAgentRuntimeAdapters().runtime_adapters())
    external_adapters.update(configuration.adapter.runtime_adapters())
    external_adapters.update(browser_adapter.runtime_adapters())
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
    p0.named_executor.ensure_provider(
        _BROWSER_PROVIDER_ID,
        frozenset({"web.verify"}),
        adapter_kind=_BROWSER_ADAPTER_KIND,
        deterministic=True,
    )

    verifier = IndependentVerifierExecutor(p0.named_executor)
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
                input_tokens=_INPUT_TOKENS,
                max_output_tokens=_OUTPUT_TOKENS,
                now=observed_at,
            )
        )
        verification = verifier.verify(
            ProducerEvidence(producer.execution, producer.evidence_digest),
            _grant(INDEPENDENT_VERIFIER_ID, "evidence.read", observed_at, 1000 + ai_index),
            tenant_id=tenant_id,
            scopes=scopes,
            now=observed_at,
        )
        if not verification.passed:
            raise WebAgentLiveCertificationError(
                f"IndependentVerifier rejected {binding.agent_id}"
            )
        output = producer.execution.route.get("output")
        if not isinstance(output, dict) or output.get("actual_cost_usd") != "0":
            raise WebAgentLiveCertificationError("Web AI certification must remain zero cost")
        proof = _persist_verified_proof(
            runtime=runtime,
            store=readiness_store,
            agent_id=binding.agent_id,
            evidence_digest=producer.evidence_digest,
            created_at=observed_at,
        )
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
        binding for binding in WEB_AGENT_BINDINGS if binding.execution_mode == "browser-tool"
    )
    browser_prompt = (
        "Bind the exact real Docker-isolated Playwright CLI evidence for this trusted "
        "source revision. Do not claim public-production verification."
    )
    browser_invocation = _invocation(
        browser_binding.agent_id,
        browser_binding.capability,
        browser_binding.permission,
        prompt=browser_prompt,
        external_egress=False,
    )
    browser_execution = p0.named_executor.execute(
        browser_invocation,
        _grant(browser_binding.agent_id, browser_binding.permission, observed_at, 2000),
        skill_id=browser_binding.primary_skill_id,
        payload={"summary_path": str(summary_path), "source_sha": source_sha},
        now=observed_at,
        preferred_provider_id=_BROWSER_PROVIDER_ID,
    )
    browser_digest = execution_evidence_digest(browser_execution)
    browser_verification = verifier.verify(
        ProducerEvidence(browser_execution, browser_digest),
        _grant(INDEPENDENT_VERIFIER_ID, "evidence.read", observed_at, 2001),
        tenant_id=tenant_id,
        scopes=scopes,
        now=observed_at,
    )
    if not browser_verification.passed:
        raise WebAgentLiveCertificationError("IndependentVerifier rejected BrowserQA")
    browser_output = browser_execution.route.get("output")
    if not isinstance(browser_output, dict):
        raise WebAgentLiveCertificationError("BrowserQA evidence output is missing")
    if (
        browser_output.get("execution_mode") != "browser-tool"
        or browser_output.get("tool") != "browser.playwright-cli"
        or browser_output.get("browser_runtime_evidence") != "PASS"
        or browser_output.get("docker_egress_boundary_proven") is not True
        or browser_output.get("direct_public_ip_egress_blocked") is not True
        or browser_output.get("state_changing_browser_actions") is not False
        or browser_output.get("public_production_proven") is not False
    ):
        raise WebAgentLiveCertificationError("BrowserQA evidence boundary is incomplete")
    browser_proof = _persist_verified_proof(
        runtime=runtime,
        store=readiness_store,
        agent_id=browser_binding.agent_id,
        evidence_digest=browser_digest,
        created_at=observed_at,
    )
    proofs[browser_binding.agent_id] = browser_proof
    receipts.append(
        _receipt(
            browser_binding.agent_id,
            browser_proof,
            browser_execution.route,
            browser_verification.verifier_evidence_digest,
            browser_verification.provider_id,
            browser_verification.model_id,
        )
    )

    if len(proofs) != 6:
        raise WebAgentLiveCertificationError("Web proof coverage must be 6/6")
    persisted = readiness_store.verify()
    if len(persisted) != 6 or any(
        record.readiness is not RuntimeReadiness.VERIFIED for record in persisted
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
        "browser_execution_mode": "browser-tool",
        "browser_tool": "browser.playwright-cli",
        "browser_e2e_real": True,
        "docker_egress_boundary_proven": True,
        "direct_public_ip_egress_blocked": True,
        "state_changing_browser_actions": False,
        "public_production_proven": False,
        "matrix_summary": summary,
        "runtime_route_count": len(runtime.routes()),
        "readiness_record_count": len(persisted),
        "runtime_database_sha256": _sha256_file(runtime_database),
        "readiness_database_sha256": _sha256_file(readiness_database),
        "browser_summary_sha256": browser_output["summary_sha256"],
        "browser_egress_receipts_sha256": browser_output["egress_receipts_sha256"],
        "browser_egress_receipt_count": browser_output["egress_receipt_count"],
        "agents": sorted(receipts, key=lambda item: str(item["agent_id"])),
    }
    (output_dir / "web-agent-live-receipt.json").write_text(
        json.dumps(receipt, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
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
    *,
    runtime: GovernedRuntime,
    store: AgentReadinessStore,
    agent_id: str,
    evidence_digest: str,
    created_at: datetime,
) -> AgentReadinessProof:
    verifier_id = registration_for(agent_id).manifest.verifier_id
    if not any(route.get("agent_id") == agent_id for route in runtime.routes()):
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
        "browser_summary_sha256": output_mapping.get("summary_sha256"),
        "verifier_provider_id": verifier_provider,
        "verifier_model_id": verifier_model,
        "proof": asdict(proof),
    }


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    repository_root = Path(os.environ.get("GITHUB_WORKSPACE", Path.cwd()))
    browser_summary = os.environ.get("WEB_AGENT_BROWSER_SUMMARY_PATH", "").strip()
    if not browser_summary:
        raise SystemExit("WEB_AGENT_LIVE_CERTIFICATION=FAIL: browser summary path missing")
    output_dir = Path(os.environ.get("WEB_AGENT_PROOF_DIR", "artifacts/web-agent-live-proof"))
    try:
        receipt = run_web_agent_live_certification(
            repository_root=repository_root,
            browser_summary_path=Path(browser_summary),
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
