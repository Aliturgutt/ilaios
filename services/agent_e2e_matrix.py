"""Evidence-derived 47-agent E2E readiness matrix.

The matrix never mutates canonical registry readiness. It projects effective
readiness from persisted proofs so missing evidence remains visible.
"""

from __future__ import annotations

from dataclasses import asdict

from services.agent_readiness import AgentReadinessProof, effective_readiness
from services.agent_registry import CANONICAL_AGENT_REGISTRY


def build_agent_e2e_matrix(
    proofs: dict[str, AgentReadinessProof],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for registration in CANONICAL_AGENT_REGISTRY:
        agent_id = registration.manifest.agent_id
        proof = proofs.get(agent_id)
        readiness = registration.readiness
        proof_payload: dict[str, object] | None = None
        if proof is not None:
            readiness = effective_readiness(proof)
            proof_payload = asdict(proof)
        rows.append(
            {
                "agent_id": agent_id,
                "alias": registration.manifest.alias,
                "team": registration.manifest.team,
                "role": registration.manifest.role,
                "backing_capability": registration.backing_capability,
                "verifier_id": registration.manifest.verifier_id,
                "readiness": readiness.value,
                "proof": proof_payload,
            }
        )
    return rows


def matrix_summary(rows: list[dict[str, object]]) -> dict[str, int]:
    counts = {"registered": 0, "executable": 0, "verified": 0}
    for row in rows:
        readiness = str(row["readiness"])
        if readiness not in counts:
            raise ValueError(f"unexpected readiness: {readiness}")
        counts[readiness] += 1
    if sum(counts.values()) != 47:
        raise ValueError("canonical readiness matrix must contain exactly 47 agents")
    return counts
