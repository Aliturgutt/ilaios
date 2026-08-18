"""Deterministic structural verifier adapter for canonical agent evidence.

This adapter does not replace the IndependentVerifier identity. It is the
first-party deterministic provider used by that identity for structural
readiness evidence. Semantic review may add evidence, but cannot weaken these
checks or self-promote readiness.
"""

from __future__ import annotations

from typing import Any

from services.agent_registry import INDEPENDENT_VERIFIER_ID, registration_for

INDEPENDENT_VERIFIER_PROVIDER_ID = "ilaios.provider.independent-verifier.structural.v1"
INDEPENDENT_VERIFIER_ADAPTER_KIND = "ilaios.runtime.independent-verifier.structural.v1"


def runtime_adapters() -> dict[str, Any]:
    return {INDEPENDENT_VERIFIER_ADAPTER_KIND: execute_structural_verification}


def execute_structural_verification(payload: dict[str, Any]) -> dict[str, Any]:
    required = {
        "producer_agent_id",
        "producer_evidence_digest",
        "recomputed_evidence_digest",
        "persisted_route_sha256",
        "execution_route_sha256",
    }
    if set(payload) != required:
        raise ValueError("structural verifier payload contract is invalid")

    producer_id = _text(payload, "producer_agent_id")
    producer_digest = _sha256(payload, "producer_evidence_digest")
    recomputed_digest = _sha256(payload, "recomputed_evidence_digest")
    persisted_route_digest = _sha256(payload, "persisted_route_sha256")
    execution_route_digest = _sha256(payload, "execution_route_sha256")

    findings: list[str] = []
    if producer_id == INDEPENDENT_VERIFIER_ID:
        findings.append("self_verification_prohibited")
    try:
        registration = registration_for(producer_id)
    except ValueError:
        findings.append("producer_identity_not_canonical")
    else:
        if registration.manifest.verifier_id != INDEPENDENT_VERIFIER_ID:
            findings.append("producer_verifier_relationship_mismatch")
    if producer_digest != recomputed_digest:
        findings.append("producer_evidence_digest_mismatch")
    if persisted_route_digest != execution_route_digest:
        findings.append("persisted_route_mismatch")

    return {
        "verdict": "PASS" if not findings else "FAIL",
        "producer_evidence_digest": producer_digest,
        "findings": findings,
        "structural_verification": True,
    }


def _text(payload: dict[str, Any], field: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{field} must be non-empty and trimmed")
    return value


def _sha256(payload: dict[str, Any], field: str) -> str:
    value = _text(payload, field)
    if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        raise ValueError(f"{field} must be lowercase SHA-256")
    return value
