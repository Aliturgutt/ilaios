from __future__ import annotations

import math

import pytest

from services.agent_final_closure_digest import (
    AgentFinalClosureDigestError,
    compute_agent_final_closure_sha256,
    verify_agent_final_closure_sha256,
)


def _receipt() -> dict[str, object]:
    receipt: dict[str, object] = {
        "agent_workstream": "CLOSED",
        "exact_master_sha": "a" * 40,
        "execution_id": "exec-final-001",
        "job_id": "job-final-001",
        "tenant_id": "tenant-final-001",
        "verified_agent_ids": [
            "ilaios.agent.core.orchestrator.v1",
            "ilaios.agent.core.planner.v1",
        ],
        "provider_tool_receipt_ids": ["receipt-provider-001"],
        "evidence_context_bindings": {
            "receipt-provider-001": {
                "execution_id": "exec-final-001",
                "job_id": "job-final-001",
                "tenant_id": "tenant-final-001",
            }
        },
    }
    receipt["closure_evidence_sha256"] = compute_agent_final_closure_sha256(receipt)
    return receipt


def test_final_closure_digest_accepts_exact_canonical_material() -> None:
    receipt = _receipt()
    verify_agent_final_closure_sha256(receipt)


def test_final_closure_digest_is_order_independent() -> None:
    receipt = _receipt()
    reordered = dict(reversed(list(receipt.items())))
    assert compute_agent_final_closure_sha256(reordered) == receipt["closure_evidence_sha256"]
    verify_agent_final_closure_sha256(reordered)


def test_final_closure_digest_rejects_receipt_tampering() -> None:
    receipt = _receipt()
    receipt["tenant_id"] = "tenant-other-999"
    with pytest.raises(AgentFinalClosureDigestError, match="does not bind"):
        verify_agent_final_closure_sha256(receipt)


def test_final_closure_digest_rejects_arbitrary_valid_shape_digest() -> None:
    receipt = _receipt()
    receipt["closure_evidence_sha256"] = "b" * 64
    with pytest.raises(AgentFinalClosureDigestError, match="does not bind"):
        verify_agent_final_closure_sha256(receipt)


def test_final_closure_digest_rejects_noncanonical_json_values() -> None:
    receipt = _receipt()
    receipt["provider_cost"] = math.nan
    with pytest.raises(AgentFinalClosureDigestError, match="canonical JSON"):
        compute_agent_final_closure_sha256(receipt)
