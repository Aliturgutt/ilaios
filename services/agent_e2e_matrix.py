"""Evidence-derived 47-agent E2E readiness matrix.

The matrix is a projection, never an authority. Every stage is read from the
latest append-only AgentReadinessProof. Missing evidence remains false and a
missing record remains REGISTERED. P0/P1/P2 phase labels follow the canonical
execution priority agreed for the Desktop rollout.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from services.agent_readiness_store import AgentReadinessStore
from services.agent_registry import CANONICAL_AGENT_REGISTRY, RuntimeReadiness


@dataclass(frozen=True, slots=True)
class AgentE2ERow:
    agent_id: str
    alias: str
    team: str
    phase: str
    invocation_passed: bool
    skill_passed: bool
    permission_passed: bool
    provider_passed: bool
    output_passed: bool
    independent_verification_passed: bool
    evidence_persisted: bool
    desktop_projection_passed: bool
    regression_e2e_passed: bool
    readiness: RuntimeReadiness
    evidence_id: str | None
    evidence_digest: str | None

    @property
    def executable_gate_passed(self) -> bool:
        return all(
            (
                self.invocation_passed,
                self.skill_passed,
                self.permission_passed,
                self.provider_passed,
                self.output_passed,
                self.independent_verification_passed,
                self.evidence_persisted,
                self.desktop_projection_passed,
            )
        )

    @property
    def verified_gate_passed(self) -> bool:
        return self.executable_gate_passed and self.regression_e2e_passed


def agent_e2e_matrix(database_path: Path) -> tuple[AgentE2ERow, ...]:
    store = AgentReadinessStore(database_path)
    latest = {record.agent_id: record for record in store.all_latest()}
    rows: list[AgentE2ERow] = []
    for registration in CANONICAL_AGENT_REGISTRY:
        manifest = registration.manifest
        record = latest.get(manifest.agent_id)
        if record is None:
            rows.append(
                AgentE2ERow(
                    manifest.agent_id,
                    manifest.alias,
                    manifest.team,
                    _phase(manifest.team),
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    RuntimeReadiness.REGISTERED,
                    None,
                    None,
                )
            )
            continue
        proof = record.proof
        rows.append(
            AgentE2ERow(
                manifest.agent_id,
                manifest.alias,
                manifest.team,
                _phase(manifest.team),
                proof.invocation_passed,
                proof.skill_passed,
                proof.permission_passed,
                proof.provider_passed,
                proof.output_passed,
                proof.independent_verification_passed,
                proof.evidence_persisted,
                proof.desktop_projection_passed,
                proof.regression_e2e_passed,
                record.readiness,
                record.evidence_id,
                record.record_digest,
            )
        )
    if len(rows) != 47:
        raise RuntimeError("canonical agent E2E matrix must contain exactly 47 rows")
    return tuple(rows)


def matrix_summary(database_path: Path) -> dict[str, object]:
    rows = agent_e2e_matrix(database_path)
    by_readiness = {
        readiness.value: sum(row.readiness is readiness for row in rows)
        for readiness in RuntimeReadiness
    }
    by_phase = {
        phase: {
            "total": sum(row.phase == phase for row in rows),
            "executable": sum(
                row.phase == phase and row.readiness in {
                    RuntimeReadiness.EXECUTABLE,
                    RuntimeReadiness.VERIFIED,
                }
                for row in rows
            ),
            "verified": sum(
                row.phase == phase and row.readiness is RuntimeReadiness.VERIFIED
                for row in rows
            ),
        }
        for phase in ("P0", "P1", "P2")
    }
    return {
        "total": len(rows),
        "readiness": by_readiness,
        "phases": by_phase,
    }


def _phase(team: str) -> str:
    if team in {"core", "engineering", "security"}:
        return "P0"
    if team in {"web", "media", "intelligence"}:
        return "P1"
    if team in {"operations", "meta"}:
        return "P2"
    raise RuntimeError(f"unknown canonical agent team: {team}")
