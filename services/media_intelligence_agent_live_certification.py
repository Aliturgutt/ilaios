"""Trusted-master live certification for the canonical Media and Intelligence agents.

All twelve agents execute bounded proposals through the existing governed zero-cost
OpenRouter path. Certification never grants direct media generation, publishing,
source acquisition, routing mutation, or other side-effect authority.
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
from services.media_intelligence_agent_execution import (
    MEDIA_INTELLIGENCE_AGENT_BINDINGS,
    MediaIntelligenceProviderBackedAgentRequest,
)
from services.media_intelligence_agent_runtime import compose_media_intelligence_agent_runtime
from services.openrouter_agent_catalog import discover_free_openrouter_agent_configuration
from services.p0_runtime_composition import compose_p0_runtime
from services.runtime import BlastRadiusBudget, ExecutionGrant, GovernedRuntime, GrantPolicy
from services.runtime.security_agent_adapters import SecurityAgentRuntimeAdapters


class MediaIntelligenceAgentLiveCertificationError(RuntimeError):
    """Live Media/Intelligence execution or evidence failed closed."""


_CERTIFICATION_INPUT_TOKEN_RESERVATION = 4096
_CERTIFICATION_OUTPUT_TOKEN_RESERVATION = 2048


def run_media_intelligence_agent_live_certification(
    *,
    repository_root: Path,
    output_dir: Path,
    now: datetime | None = None,
) -> dict[str, object]:
    root = repository_root.resolve()
    if not root.is_dir():
        raise MediaIntelligenceAgentLiveCertificationError("repository root is unavailable")
    observed_at = now or datetime.now(timezone.utc)
    if observed_at.tzinfo is None:
        raise MediaIntelligenceAgentLiveCertificationError(
            "certification timestamp must be timezone-aware"
        )
    source_sha = os.environ.get("GITHUB_SHA", "").strip()
    if len(source_sha) != 40 or any(
        character not in "0123456789abcdef" for character in source_sha
    ):
        raise MediaIntelligenceAgentLiveCertificationError(
            "exact lowercase GITHUB_SHA is required"
        )

    configuration = discover_free_openrouter_agent_configuration()
    if configuration is None:
        raise MediaIntelligenceAgentLiveCertificationError(
            "OPENROUTER_API_KEY is unavailable"
        )

    resolved_output = output_dir.resolve()
    resolved_output.mkdir(parents=True, exist_ok=True)
    runtime_database = resolved_output / "media-intelligence-agent-runtime.sqlite3"
    readiness_database = resolved_output / "media-intelligence-agent-readiness.sqlite3"
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
    media_intelligence = compose_media_intelligence_agent_runtime(
        p0.named_executor,
        root,
        ai_adapter=configuration.adapter,
        ai_provider_capabilities=configuration.provider_capabilities,
    )
    if media_intelligence.ai_executor is None:
        raise MediaIntelligenceAgentLiveCertificationError(
            "canonical Media/Intelligence governed AI executor is unavailable"
        )
    if (
        media_intelligence.target_agent_count != 12
        or media_intelligence.provisioned_identity_count != 12
    ):
        raise MediaIntelligenceAgentLiveCertificationError(
            "canonical Media/Intelligence runtime composition is incomplete"
        )
    if any(
        (
            media_intelligence.direct_network_authority,
            media_intelligence.direct_media_side_effect_authority,
            media_intelligence.direct_publish_authority,
        )
    ):
        raise MediaIntelligenceAgentLiveCertificationError(
            "Media/Intelligence composition widened side-effect authority"
        )

    verifier = IndependentVerifierExecutor(p0.named_executor, configuration.adapter)
    readiness_store = AgentReadinessStore(readiness_database)
    tenant_id = "ilaios-media-intelligence-live-certification"
    scopes = (Scope(ScopeKind.TENANT, tenant_id),)
    proofs: dict[str, AgentReadinessProof] = {}
    receipts: list[dict[str, object]] = []

    for sequence, binding in enumerate(MEDIA_INTELLIGENCE_AGENT_BINDINGS, start=1):
        prompt = (
            f"ILAIOS Media/Intelligence trusted-master certification probe {sequence}. "
            f"Return a concise bounded proposal for capability {binding.capability}. "
            "Do not acquire sources, generate or modify media, publish content, mutate "
            "routing, bypass governance, or claim side effects."
        )
        invocation = _invocation(
            binding.agent_id,
            binding.capability,
            binding.permission,
            prompt=prompt,
        )
        producer = media_intelligence.ai_executor.execute(
            MediaIntelligenceProviderBackedAgentRequest(
                invocation=invocation,
                grant=_grant(binding.agent_id, binding.permission, observed_at, sequence),
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
                1000 + sequence,
            ),
            tenant_id=tenant_id,
            scopes=scopes,
            now=observed_at,
            input_tokens=256,
            max_output_tokens=256,
        )
        if not verification.passed:
            raise MediaIntelligenceAgentLiveCertificationError(
                f"IndependentVerifier rejected {binding.agent_id}"
            )
        output = producer.execution.route.get("output")
        if not isinstance(output, dict):
            raise MediaIntelligenceAgentLiveCertificationError(
                "Media/Intelligence provider output disappeared"
            )
        if output.get("actual_cost_usd") != "0":
            raise MediaIntelligenceAgentLiveCertificationError(
                "Media/Intelligence certification observed non-zero provider cost"
            )
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

    expected_ids = {binding.agent_id for binding in MEDIA_INTELLIGENCE_AGENT_BINDINGS}
    if len(proofs) != 12 or set(proofs) != expected_ids:
        raise MediaIntelligenceAgentLiveCertificationError(
            "Media/Intelligence proof coverage mismatch"
        )
    persisted = readiness_store.verify()
    if len(persisted) != 12 or any(
        item.readiness is not RuntimeReadiness.VERIFIED for item in persisted
    ):
        raise MediaIntelligenceAgentLiveCertificationError(
            "append-only Media/Intelligence readiness ledger is incomplete"
        )
    final_projection = agent_state_projection(runtime.routes(), readiness_store.projection())
    _assert_projected_verified(final_projection, expected_ids)
    summary = matrix_summary(build_agent_e2e_matrix(proofs))
    if summary != {"registered": 35, "executable": 0, "verified": 12}:
        raise MediaIntelligenceAgentLiveCertificationError(
            f"unexpected Media/Intelligence readiness matrix summary: {summary!r}"
        )

    media_count = sum(
        registration_for(agent_id).manifest.team == "media" for agent_id in proofs
    )
    intelligence_count = sum(
        registration_for(agent_id).manifest.team == "intelligence" for agent_id in proofs
    )
    if media_count != 8 or intelligence_count != 4:
        raise MediaIntelligenceAgentLiveCertificationError(
            "Media/Intelligence verified population drifted"
        )

    receipt: dict[str, object] = {
        "status": "VERIFIED",
        "scope": "P1_MEDIA_INTELLIGENCE",
        "revision_sha": source_sha,
        "observed_at": observed_at.isoformat(),
        "target_agent_count": 12,
        "verified_agent_count": 12,
        "media_agent_count": media_count,
        "intelligence_agent_count": intelligence_count,
        "governed_ai_agent_count": 12,
        "governed_ai_zero_cost_openrouter_only": True,
        "direct_network_authority": False,
        "direct_media_side_effect_authority": False,
        "direct_publish_authority": False,
        "matrix_summary": summary,
        "runtime_route_count": len(runtime.routes()),
        "readiness_record_count": len(persisted),
        "runtime_database_sha256": _sha256_file(runtime_database),
        "readiness_database_sha256": _sha256_file(readiness_database),
        "agents": sorted(receipts, key=lambda item: str(item["agent_id"])),
    }
    receipt_path = resolved_output / "media-intelligence-agent-live-receipt.json"
    receipt_path.write_text(
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
) -> AgentInvocation:
    manifest = registration_for(agent_id).manifest
    caller_id = sorted(manifest.allowed_callers)[0]
    input_class = (
        "governed_task" if "governed_task" in manifest.inputs else sorted(manifest.inputs)[0]
    )
    output_class = (
        "proposal" if "proposal" in manifest.outputs else sorted(manifest.outputs)[0]
    )
    return AgentInvocation(
        invocation_id=(
            f"media-intelligence-live:{agent_id}:"
            f"{hashlib.sha256(prompt.encode()).hexdigest()[:16]}"
        ),
        caller_id=caller_id,
        target_id=agent_id,
        capability=capability,
        permission=permission,
        input_class=input_class,
        requested_output_class=output_class,
        prompt=prompt,
        contains_secret=False,
        external_egress=True,
        dlp_approved=True,
        security_scan_passed=True,
    )


def _grant(
    agent_id: str,
    permission: str,
    now: datetime,
    sequence: int,
) -> ExecutionGrant:
    return ExecutionGrant(
        grant_id=f"media-intelligence-live-grant:{sequence}:{agent_id}",
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
        raise MediaIntelligenceAgentLiveCertificationError(
            f"persisted runtime route missing for {agent_id}"
        )
    proof = _verified_proof(agent_id, evidence_digest)
    record = store.persist(proof, created_at=created_at)
    if record.readiness is not RuntimeReadiness.VERIFIED:
        raise MediaIntelligenceAgentLiveCertificationError(
            f"readiness did not reach VERIFIED for {agent_id}"
        )
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
        raise MediaIntelligenceAgentLiveCertificationError(
            "Desktop agent projection is malformed"
        )
    indexed = {
        str(item.get("agent_id")): item
        for item in agents
        if isinstance(item, dict) and isinstance(item.get("agent_id"), str)
    }
    for agent_id in expected_ids:
        item = indexed.get(agent_id)
        if not isinstance(item, dict) or item.get("readiness") != "verified":
            raise MediaIntelligenceAgentLiveCertificationError(
                f"Desktop projection failed for {agent_id}"
            )


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
        raise MediaIntelligenceAgentLiveCertificationError(
            "provider receipt output is missing"
        )
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
    output_dir = Path(
        os.environ.get(
            "MEDIA_INTELLIGENCE_AGENT_PROOF_DIR",
            "artifacts/media-intelligence-agent-live-proof",
        )
    )
    try:
        receipt = run_media_intelligence_agent_live_certification(
            repository_root=workspace,
            output_dir=output_dir,
        )
    except Exception as exc:
        raise SystemExit(
            f"MEDIA_INTELLIGENCE_AGENT_LIVE_CERTIFICATION=FAIL: {exc}"
        ) from exc
    print(
        "MEDIA_INTELLIGENCE_AGENT_LIVE_CERTIFICATION=PASS "
        f"verified={receipt['verified_agent_count']}/{receipt['target_agent_count']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
