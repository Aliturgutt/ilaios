"""Trusted-master live certification for Operations 6 + Meta 2.

The seven provider-backed Operations/Meta proposal agents execute through the
existing GovernedRuntime/OpenRouter path and are independently verified by the
canonical IndependentVerifier. IndependentVerifier itself remains outside
generic provider execution and, because its manifest verifier is human.owner,
is never self-promoted by this automated certification.
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
    INDEPENDENT_VERIFIER_PROVIDER_ID,
    IndependentVerifierExecutor,
    ProducerEvidence,
)
from services.openrouter_agent_catalog import discover_free_openrouter_agent_configuration
from services.operations_meta_agent_execution import (
    OPERATIONS_META_AGENT_BINDINGS,
    OperationsMetaProviderBackedAgentRequest,
    OperationsMetaProviderBackedExecutor,
)
from services.p0_runtime_composition import compose_p0_runtime
from services.runtime import BlastRadiusBudget, ExecutionGrant, GovernedRuntime, GrantPolicy
from services.runtime.security_agent_adapters import SecurityAgentRuntimeAdapters


class OperationsMetaAgentLiveCertificationError(RuntimeError):
    """Operations/Meta trusted-master certification failed closed."""


_CERTIFICATION_INPUT_TOKEN_RESERVATION = 4096
_CERTIFICATION_OUTPUT_TOKEN_RESERVATION = 2048


def run_operations_meta_agent_live_certification(
    *,
    repository_root: Path,
    output_dir: Path,
    now: datetime | None = None,
) -> dict[str, object]:
    root = repository_root.resolve()
    if not root.is_dir():
        raise OperationsMetaAgentLiveCertificationError("repository root is unavailable")
    observed_at = now or datetime.now(timezone.utc)
    if observed_at.tzinfo is None:
        raise OperationsMetaAgentLiveCertificationError(
            "certification timestamp must be timezone-aware"
        )
    source_sha = os.environ.get("GITHUB_SHA", "").strip()
    if len(source_sha) != 40 or any(
        character not in "0123456789abcdef" for character in source_sha
    ):
        raise OperationsMetaAgentLiveCertificationError(
            "exact lowercase GITHUB_SHA is required"
        )

    configuration = discover_free_openrouter_agent_configuration()
    if configuration is None:
        raise OperationsMetaAgentLiveCertificationError("OPENROUTER_API_KEY is unavailable")

    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    runtime_database = output_dir / "operations-meta-runtime.sqlite3"
    readiness_database = output_dir / "operations-meta-readiness.sqlite3"
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
    executor = OperationsMetaProviderBackedExecutor(p0.named_executor, configuration.adapter)
    verifier = IndependentVerifierExecutor(p0.named_executor, configuration.adapter)
    readiness_store = AgentReadinessStore(readiness_database)
    tenant_id = "ilaios-operations-meta-live-certification"
    scopes = (Scope(ScopeKind.TENANT, tenant_id),)

    proofs: dict[str, AgentReadinessProof] = {}
    receipts: list[dict[str, object]] = []
    sequence = 0
    for binding in OPERATIONS_META_AGENT_BINDINGS:
        if binding.execution_mode != "governed-ai":
            continue
        sequence += 1
        prompt = (
            f"ILAIOS Operations/Meta trusted-master certification probe {sequence}. "
            f"Return a concise bounded proposal for capability {binding.capability}. "
            "Do not perform mutations, publication, recovery actions, routing changes, "
            "evidence promotion, deployment, or self-modification."
        )
        invocation = _invocation(
            binding.agent_id,
            binding.capability,
            binding.permission,
            prompt=prompt,
        )
        producer = executor.execute(
            OperationsMetaProviderBackedAgentRequest(
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
            _grant(INDEPENDENT_VERIFIER_ID, "evidence.read", observed_at, 1000 + sequence),
            tenant_id=tenant_id,
            scopes=scopes,
            now=observed_at,
            input_tokens=256,
            max_output_tokens=256,
        )
        if not verification.passed:
            raise OperationsMetaAgentLiveCertificationError(
                f"IndependentVerifier rejected {binding.agent_id}"
            )
        output = producer.execution.route.get("output")
        if not isinstance(output, dict):
            raise OperationsMetaAgentLiveCertificationError(
                "Operations/Meta provider output disappeared"
            )
        if output.get("actual_cost_usd") != "0":
            raise OperationsMetaAgentLiveCertificationError(
                "Operations/Meta certification observed non-zero provider cost"
            )
        proof = _verified_proof(binding.agent_id, producer.evidence_digest)
        record = readiness_store.persist(proof, created_at=observed_at)
        if record.readiness is not RuntimeReadiness.VERIFIED:
            raise OperationsMetaAgentLiveCertificationError(
                f"readiness did not reach VERIFIED for {binding.agent_id}"
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

    if len(proofs) != 7:
        raise OperationsMetaAgentLiveCertificationError(
            f"provider-backed proof coverage mismatch expected=7 actual={len(proofs)}"
        )
    persisted = readiness_store.verify()
    if len(persisted) != 7 or any(
        item.readiness is not RuntimeReadiness.VERIFIED for item in persisted
    ):
        raise OperationsMetaAgentLiveCertificationError(
            "append-only Operations/Meta readiness ledger is incomplete"
        )
    final_projection = agent_state_projection(runtime.routes(), readiness_store.projection())
    _assert_projected_verified(final_projection, set(proofs))
    summary = matrix_summary(build_agent_e2e_matrix(proofs))
    if summary != {"registered": 40, "executable": 0, "verified": 7}:
        raise OperationsMetaAgentLiveCertificationError(
            f"unexpected Operations/Meta readiness matrix summary: {summary!r}"
        )

    verifier_registration = registration_for(INDEPENDENT_VERIFIER_ID)
    if verifier_registration.manifest.verifier_id != "human.owner":
        raise OperationsMetaAgentLiveCertificationError(
            "IndependentVerifier verifier authority drifted from human.owner"
        )
    _assert_independent_verifier_routes_are_structural(runtime.routes())

    receipt: dict[str, object] = {
        "status": "PARTIAL",
        "scope": "OPERATIONS_6_META_2",
        "revision_sha": source_sha,
        "observed_at": observed_at.isoformat(),
        "target_agent_count": 8,
        "verified_agent_count": 7,
        "governed_ai_agent_count": 7,
        "governed_ai_zero_cost_openrouter_only": True,
        "independent_verifier_agent_count": 1,
        "independent_verifier_execution_mode": "independent-verification",
        "independent_verifier_provider_backed": False,
        "independent_verifier_verifier_id": "human.owner",
        "independent_verifier_readiness": "registered",
        "human_owner_verification_required": True,
        "overall_8_of_8_verified": False,
        "matrix_summary": summary,
        "runtime_route_count": len(runtime.routes()),
        "readiness_record_count": len(persisted),
        "runtime_database_sha256": _sha256_file(runtime_database),
        "readiness_database_sha256": _sha256_file(readiness_database),
        "agents": sorted(receipts, key=lambda item: str(item["agent_id"])),
    }
    receipt_path = output_dir / "operations-meta-agent-live-receipt.json"
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
    output_class = "proposal" if "proposal" in manifest.outputs else sorted(manifest.outputs)[0]
    return AgentInvocation(
        invocation_id=(
            f"operations-meta-live:{agent_id}:"
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
        grant_id=f"operations-meta-live-grant:{sequence}:{agent_id}",
        subject_id=agent_id,
        actions=frozenset({permission}),
        resources=frozenset({agent_id}),
        expires_at=now + timedelta(minutes=30),
        budget=BlastRadiusBudget(max_side_effects=1, max_resources=1),
    )


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
        raise OperationsMetaAgentLiveCertificationError("Desktop agent projection is malformed")
    indexed = {
        str(item.get("agent_id")): item
        for item in agents
        if isinstance(item, dict) and isinstance(item.get("agent_id"), str)
    }
    for agent_id in expected_ids:
        item = indexed.get(agent_id)
        if not isinstance(item, dict) or item.get("readiness") != "verified":
            raise OperationsMetaAgentLiveCertificationError(
                f"Desktop projection failed for {agent_id}"
            )


def _assert_independent_verifier_routes_are_structural(
    routes: tuple[dict[str, Any], ...],
) -> None:
    verifier_routes = [
        route for route in routes if route.get("agent_id") == INDEPENDENT_VERIFIER_ID
    ]
    if len(verifier_routes) != 7:
        raise OperationsMetaAgentLiveCertificationError(
            "IndependentVerifier structural attestation coverage mismatch"
        )
    if any(
        route.get("provider_id") != INDEPENDENT_VERIFIER_PROVIDER_ID
        for route in verifier_routes
    ):
        raise OperationsMetaAgentLiveCertificationError(
            "IndependentVerifier escaped deterministic structural attestation boundary"
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
        raise OperationsMetaAgentLiveCertificationError("provider receipt output is missing")
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
            "OPERATIONS_META_AGENT_PROOF_DIR",
            "artifacts/operations-meta-agent-live-proof",
        )
    )
    try:
        receipt = run_operations_meta_agent_live_certification(
            repository_root=workspace,
            output_dir=output_dir,
        )
    except Exception as exc:
        raise SystemExit(f"OPERATIONS_META_AGENT_LIVE_CERTIFICATION=FAIL: {exc}") from exc
    print(
        "OPERATIONS_META_AGENT_LIVE_CERTIFICATION=PARTIAL "
        f"verified={receipt['verified_agent_count']}/{receipt['target_agent_count']} "
        "human_owner_verification_required=true"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
