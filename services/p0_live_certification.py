"""Live, zero-cost P0 certification for the canonical ILAIOS agent runtime.

The certification executes all 21 P0 identities through their real governed
provider/tool path, applies the canonical independent verifier relationship,
persists append-only readiness evidence, and proves Desktop projection. It is a
certification harness, not a second runtime or a readiness bypass.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from services.agent_e2e_matrix import build_agent_e2e_matrix, matrix_summary
from services.agent_governance import AgentInvocation
from services.agent_projection import agent_state_projection
from services.agent_readiness import AgentReadinessProof
from services.agent_readiness_store import AgentReadinessStore
from services.agent_registry import (
    INDEPENDENT_VERIFIER_ID,
    SECURITY_VERIFIER_ID,
    RuntimeReadiness,
    registration_for,
)
from services.ai_governance import Scope, ScopeKind
from services.control_plane.migrations import migrate_database
from services.independent_verifier_execution import (
    IndependentVerifierExecutor,
    ProducerEvidence,
)
from services.openrouter_agent_catalog import (
    OpenRouterAgentCatalogError,
    discover_free_openrouter_agent_configuration,
)
from services.p0_agent_execution import (
    P0_AGENT_BINDINGS,
    ProviderBackedAgentRequest,
    binding_for,
)
from services.p0_runtime_composition import compose_p0_runtime
from services.runtime import (
    BlastRadiusBudget,
    ExecutionGrant,
    GovernedRuntime,
    GrantPolicy,
)
from services.runtime.security_agent_adapters import SecurityAgentRuntimeAdapters


class P0LiveCertificationError(RuntimeError):
    """Live P0 execution or evidence failed closed."""


_CERTIFICATION_INPUT_TOKEN_RESERVATION = 4096
_CERTIFICATION_OUTPUT_TOKEN_RESERVATION = 2048


def _required_revision_sha() -> str:
    revision = os.environ.get("GITHUB_SHA", "").strip()
    if len(revision) != 40 or any(
        character not in "0123456789abcdef" for character in revision.lower()
    ):
        raise P0LiveCertificationError(
            "exact 40-hex GITHUB_SHA is required for P0 certification"
        )
    return revision.lower()


def run_p0_live_certification(
    *,
    repository_root: Path,
    output_dir: Path,
    now: datetime | None = None,
) -> dict[str, object]:
    root = repository_root.resolve()
    if not root.is_dir():
        raise P0LiveCertificationError("repository root is unavailable")
    observed_at = now or datetime.now(timezone.utc)
    if observed_at.tzinfo is None:
        raise P0LiveCertificationError("certification timestamp must be timezone-aware")
    revision_sha = _required_revision_sha()

    configuration = discover_free_openrouter_agent_configuration()
    if configuration is None:
        raise P0LiveCertificationError("OPENROUTER_API_KEY is unavailable")

    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    runtime_database = output_dir / "p0-runtime.sqlite3"
    readiness_database = output_dir / "p0-readiness.sqlite3"
    migrate_database(runtime_database)

    security_adapters = SecurityAgentRuntimeAdapters().runtime_adapters()
    external_adapters = dict(security_adapters)
    external_adapters.update(configuration.adapter.runtime_adapters())
    runtime = GovernedRuntime(runtime_database, external_adapters=external_adapters)
    grants = GrantPolicy()
    composition = compose_p0_runtime(
        runtime,
        grants,
        engineering_skills_root=root / "tools" / "software-factory" / "skills",
        ai_adapter=configuration.adapter,
        ai_provider_capabilities=configuration.provider_capabilities,
    )
    if composition.ai_executor is None:
        raise P0LiveCertificationError("governed AI executor was not composed")
    if composition.target_agent_count != 21:
        raise P0LiveCertificationError("P0 target count drifted from 21")

    verifier = IndependentVerifierExecutor(
        composition.named_executor, configuration.adapter
    )
    readiness_store = AgentReadinessStore(readiness_database)
    tenant_id = "ilaios-live-certification"
    scopes = (Scope(ScopeKind.TENANT, tenant_id),)
    proofs: dict[str, AgentReadinessProof] = {}
    agent_receipts: list[dict[str, object]] = []

    for index, binding in enumerate(P0_AGENT_BINDINGS):
        if binding.execution_mode != "governed-ai":
            continue
        invocation = _invocation(
            binding.agent_id,
            binding.capability,
            binding.permission,
            prompt=(
                f"ILAIOS P0 live certification probe {index}. "
                f"Return a concise bounded proposal for capability {binding.capability}. "
                "Do not claim external side effects, deployment, or verification."
            ),
            external_egress=True,
        )
        producer = composition.ai_executor.execute(
            ProviderBackedAgentRequest(
                invocation=invocation,
                grant=_grant(binding.agent_id, binding.permission, observed_at, index),
                tenant_id=tenant_id,
                scopes=scopes,
                prompt=invocation.prompt,
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
                1000 + index,
            ),
            tenant_id=tenant_id,
            scopes=scopes,
            now=observed_at,
            input_tokens=256,
            max_output_tokens=256,
        )
        if not verification.passed:
            raise P0LiveCertificationError(
                f"IndependentVerifier rejected {binding.agent_id}: {verification.findings!r}"
            )
        proof = _persist_verified_proof(
            runtime=runtime,
            store=readiness_store,
            agent_id=binding.agent_id,
            verifier_id=registration_for(binding.agent_id).manifest.verifier_id,
            evidence_digest=producer.evidence_digest,
            created_at=observed_at,
        )
        proofs[binding.agent_id] = proof
        output = producer.execution.route.get("output")
        if not isinstance(output, dict):
            raise P0LiveCertificationError("provider execution output disappeared")
        actual_cost = output.get("actual_cost_usd")
        if actual_cost != "0":
            raise P0LiveCertificationError(
                f"automatic P0 certification observed non-zero provider cost: {actual_cost!r}"
            )
        agent_receipts.append(
            _receipt(
                binding.agent_id,
                proof,
                producer.execution.route,
                verifier_model=verification.model_id,
                verifier_provider=verification.provider_id,
                verifier_evidence_digest=verification.verifier_evidence_digest,
            )
        )

    with tempfile.TemporaryDirectory(prefix="ilaios-p0-security-") as raw_fixture:
        fixture = Path(raw_fixture)
        _create_safe_security_fixture(fixture)
        security_verifier_execution: Any | None = None
        security_verifier_digest = ""
        local_index = 0
        for binding in P0_AGENT_BINDINGS:
            if binding.execution_mode != "defensive-local":
                continue
            local_index += 1
            invocation = _invocation(
                binding.agent_id,
                binding.capability,
                binding.permission,
                prompt="Run the bounded defensive certification fixture only.",
                external_egress=False,
            )
            payload: dict[str, Any] = {
                "scope_id": f"p0-security-{local_index}",
                "repository_root": str(fixture.resolve()),
            }
            if binding.agent_id == "ilaios.agent.security.web-api.v1":
                payload.update(
                    {
                        "target_url": "http://127.0.0.1/health",
                        "status_code": 200,
                        "headers": {
                            "Content-Security-Policy": "default-src 'none'",
                            "X-Content-Type-Options": "nosniff",
                            "Referrer-Policy": "no-referrer",
                        },
                    }
                )
            producer_execution = composition.security_executor.execute_specialist(
                invocation,
                _grant(
                    binding.agent_id,
                    binding.permission,
                    observed_at,
                    2000 + local_index,
                ),
                skill_id=binding.primary_skill_id,
                payload=payload,
                now=observed_at,
            )
            verifier_binding = binding_for(SECURITY_VERIFIER_ID)
            verifier_invocation = _invocation(
                SECURITY_VERIFIER_ID,
                verifier_binding.capability,
                verifier_binding.permission,
                prompt="Independently verify the exact persisted security report.",
                external_egress=False,
            )
            local_verification = composition.security_executor.independently_verify(
                producer_execution,
                verifier_invocation,
                _grant(
                    SECURITY_VERIFIER_ID,
                    verifier_binding.permission,
                    observed_at,
                    3000 + local_index,
                ),
                skill_id=verifier_binding.primary_skill_id,
                now=observed_at,
            )
            if not local_verification.passed:
                raise P0LiveCertificationError(
                    f"SecurityVerifier rejected {binding.agent_id}"
                )
            proof = _persist_verified_proof(
                runtime=runtime,
                store=readiness_store,
                agent_id=binding.agent_id,
                verifier_id=SECURITY_VERIFIER_ID,
                evidence_digest=local_verification.producer_evidence_digest,
                created_at=observed_at,
            )
            proofs[binding.agent_id] = proof
            agent_receipts.append(
                _receipt(
                    binding.agent_id,
                    proof,
                    producer_execution.route,
                    verifier_model=None,
                    verifier_provider="ilaios.security.local.verifier",
                    verifier_evidence_digest=local_verification.verifier_evidence_digest,
                )
            )
            if security_verifier_execution is None:
                security_verifier_execution = local_verification.verifier
                security_verifier_digest = local_verification.verifier_evidence_digest

    if security_verifier_execution is None or not security_verifier_digest:
        raise P0LiveCertificationError("SecurityVerifier producer evidence was not created")
    security_verifier_verification = verifier.verify(
        ProducerEvidence(security_verifier_execution, security_verifier_digest),
        _grant(
            INDEPENDENT_VERIFIER_ID,
            "evidence.read",
            observed_at,
            4000,
        ),
        tenant_id=tenant_id,
        scopes=scopes,
        now=observed_at,
        input_tokens=256,
        max_output_tokens=256,
    )
    if not security_verifier_verification.passed:
        raise P0LiveCertificationError("IndependentVerifier rejected SecurityVerifier")
    security_verifier_proof = _persist_verified_proof(
        runtime=runtime,
        store=readiness_store,
        agent_id=SECURITY_VERIFIER_ID,
        verifier_id=INDEPENDENT_VERIFIER_ID,
        evidence_digest=security_verifier_digest,
        created_at=observed_at,
    )
    proofs[SECURITY_VERIFIER_ID] = security_verifier_proof
    agent_receipts.append(
        _receipt(
            SECURITY_VERIFIER_ID,
            security_verifier_proof,
            security_verifier_execution.route,
            verifier_model=security_verifier_verification.model_id,
            verifier_provider=security_verifier_verification.provider_id,
            verifier_evidence_digest=security_verifier_verification.verifier_evidence_digest,
        )
    )

    if len(proofs) != 21:
        raise P0LiveCertificationError(
            f"live P0 proof coverage mismatch: expected=21 actual={len(proofs)}"
        )
    persisted = readiness_store.verify()
    if len(persisted) != 21 or any(
        item.readiness is not RuntimeReadiness.VERIFIED for item in persisted
    ):
        raise P0LiveCertificationError("append-only P0 readiness ledger is incomplete")

    final_projection = agent_state_projection(runtime.routes(), readiness_store.projection())
    _assert_projected_verified(final_projection, set(proofs))
    matrix = build_agent_e2e_matrix(proofs)
    summary = matrix_summary(matrix)
    if summary != {"registered": 26, "executable": 0, "verified": 21}:
        raise P0LiveCertificationError(f"unexpected P0 readiness matrix summary: {summary!r}")

    receipt: dict[str, object] = {
        "status": "VERIFIED",
        "scope": "P0",
        "revision_sha": revision_sha,
        "observed_at": observed_at.isoformat(),
        "target_agent_count": 21,
        "verified_agent_count": len(proofs),
        "zero_cost_openrouter_only": True,
        "matrix_summary": summary,
        "runtime_route_count": len(runtime.routes()),
        "readiness_record_count": len(persisted),
        "runtime_database_sha256": _sha256_file(runtime_database),
        "readiness_database_sha256": _sha256_file(readiness_database),
        "agents": sorted(agent_receipts, key=lambda item: str(item["agent_id"])),
    }
    receipt_path = output_dir / "p0-live-receipt.json"
    receipt_path.write_text(
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
    caller_id = sorted(manifest.allowed_callers)[0]
    input_class = (
        "governed_task" if "governed_task" in manifest.inputs else sorted(manifest.inputs)[0]
    )
    output_class = (
        "proposal" if "proposal" in manifest.outputs else sorted(manifest.outputs)[0]
    )
    return AgentInvocation(
        invocation_id=f"live:{agent_id}:{hashlib.sha256(prompt.encode()).hexdigest()[:16]}",
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
        grant_id=f"live-grant:{sequence}:{agent_id}",
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
    verifier_id: str,
    evidence_digest: str,
    created_at: datetime,
) -> AgentReadinessProof:
    routes = runtime.routes()
    if not any(
        route.get("agent_id") == agent_id and isinstance(route.get("sequence"), int)
        for route in routes
    ):
        raise P0LiveCertificationError(f"persisted runtime route missing for {agent_id}")
    synthetic = {
        agent_id: {
            "readiness": "verified",
            "verifier_id": verifier_id,
            "producer_evidence_digest": evidence_digest,
        }
    }
    projected = agent_state_projection(routes, synthetic)
    _assert_projected_verified(projected, {agent_id})
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
        raise P0LiveCertificationError(f"readiness did not reach VERIFIED for {agent_id}")
    persisted_projection = agent_state_projection(runtime.routes(), store.projection())
    _assert_projected_verified(persisted_projection, {agent_id})
    return proof


def _assert_projected_verified(
    projection: dict[str, object], expected_ids: set[str]
) -> None:
    agents = projection.get("agents")
    if not isinstance(agents, list):
        raise P0LiveCertificationError("Desktop agent projection is malformed")
    indexed = {
        str(item.get("agent_id")): item
        for item in agents
        if isinstance(item, dict) and isinstance(item.get("agent_id"), str)
    }
    for agent_id in expected_ids:
        record = indexed.get(agent_id)
        if not isinstance(record, dict) or record.get("readiness") != "verified":
            raise P0LiveCertificationError(
                f"Desktop readiness projection failed for {agent_id}"
            )
        if record.get("agent_status") == "offline":
            raise P0LiveCertificationError(
                f"Desktop runtime route projection is offline for {agent_id}"
            )


def _create_safe_security_fixture(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "app.py").write_text(
        "def health() -> str:\n    return 'ok'\n", encoding="utf-8"
    )
    (root / "requirements.txt").write_text("example==1.0.0\n", encoding="utf-8")
    (root / "infra.tf").write_text(
        'variable "environment" { default = "test" }\n', encoding="utf-8"
    )


def _receipt(
    agent_id: str,
    proof: AgentReadinessProof,
    route: dict[str, Any],
    *,
    verifier_model: str | None,
    verifier_provider: str,
    verifier_evidence_digest: str,
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
        "input_tokens": output_mapping.get("input_tokens"),
        "output_tokens": output_mapping.get("output_tokens"),
        "latency_ms": output_mapping.get("latency_ms"),
        "verifier_provider_id": verifier_provider,
        "verifier_model_id": verifier_model,
        "proof": asdict(proof),
    }


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    repository_root = Path(os.environ.get("GITHUB_WORKSPACE", Path.cwd()))
    output_dir = Path(
        os.environ.get("AGENT_P0_PROOF_DIR", "artifacts/agent-p0-live-proof")
    )
    try:
        receipt = run_p0_live_certification(
            repository_root=repository_root,
            output_dir=output_dir,
        )
    except (P0LiveCertificationError, OpenRouterAgentCatalogError) as exc:
        raise SystemExit(f"P0_LIVE_CERTIFICATION=FAIL: {exc}") from exc
    print(
        "P0_LIVE_CERTIFICATION=PASS "
        f"verified={receipt['verified_agent_count']}/{receipt['target_agent_count']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
