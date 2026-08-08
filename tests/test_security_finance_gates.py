"""Security, HITL, and financial gate tests for PLATFORM.P13."""

from __future__ import annotations

from pathlib import Path

import pytest

from services.governance import (
    FinancialLedger,
    GateError,
    HumanApprovalStore,
    PricingRegistry,
    SecretVault,
    SecurityFinanceGate,
    WorkRequest,
    redact_sensitive,
)


class RecordingKms:
    def encrypt(self, plaintext: bytes, *, context: str) -> bytes:
        return context.encode() + b"|" + plaintext[::-1]

    def decrypt(self, ciphertext: bytes, *, context: str) -> bytes:
        prefix, value = ciphertext.split(b"|", 1)
        assert prefix.decode() == context
        return value[::-1]


def _gate(
    tmp_path: Path, cap: int = 100
) -> tuple[SecurityFinanceGate, HumanApprovalStore, FinancialLedger]:
    approvals = HumanApprovalStore(tmp_path / "approvals.sqlite3")
    ledger = FinancialLedger(tmp_path / "ledger.sqlite3", hard_cap_minor=cap)
    gate = SecurityFinanceGate(approvals, PricingRegistry({"compute": 10}), ledger)
    return gate, approvals, ledger


def test_secrets_cross_kms_boundary_and_dlp_redacts() -> None:
    vault = SecretVault(RecordingKms())
    vault.put("provider", b"secret-value")
    assert vault.reveal("provider") == b"secret-value"
    assert redact_sensitive({"token": "raw", "safe": "visible"}) == {
        "token": "[REDACTED]",
        "safe": "visible",
    }


def test_high_risk_billable_work_requires_durable_approval_and_reservation(
    tmp_path: Path,
) -> None:
    gate, approvals, _ = _gate(tmp_path)
    request = WorkRequest("request-1", "high", "compute", 5)
    with pytest.raises(GateError, match="human approval"):
        gate.authorize(request)

    approvals.decide("request-1", approved=True, approver="owner")
    restarted, _, ledger = _gate(tmp_path)
    restarted.authorize(request)
    ledger.reconcile("request-1", 40)


def test_billable_work_cannot_bypass_hard_cap_or_reconciliation(
    tmp_path: Path,
) -> None:
    gate, _, ledger = _gate(tmp_path, cap=20)
    with pytest.raises(GateError, match="hard cap"):
        gate.authorize(WorkRequest("request-2", "low", "compute", 3))
    ledger.reserve("request-3", 20)
    with pytest.raises(GateError, match="exceeds reservation"):
        ledger.reconcile("request-3", 21)
