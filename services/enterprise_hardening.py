"""Cross-cutting enterprise hardening gate for promoted ILAIOS factories."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Final

from services.capability_registry import CapabilityDefinition, capability
from services.evidence.store import EvidenceError, EvidenceStore


class EnterpriseHardeningError(PermissionError):
    """A promoted factory is missing required enterprise hardening evidence."""


PROMOTED_FACTORY_IDS: Final[tuple[str, ...]] = (
    "ilaios.capability.security-factory",
    "ilaios.capability.research-data",
    "ilaios.capability.creative-document",
    "ilaios.capability.commerce-growth",
    "ilaios.capability.personal-operations",
    "ilaios.capability.app-factory",
)

HARDENING_GATES: Final[tuple[str, ...]] = (
    "recovery",
    "isolation",
    "provenance",
    "observability",
    "security_negative_tests",
    "cost_boundary",
)

_BACKUP_RESTORE_GATE: Final = "backup_restore"
_RECEIPT_ACTION: Final = "enterprise-hardening.verify"
_RECEIPT_SCHEMA_VERSION: Final = 1
_SOURCE_REVISION = re.compile(r"[0-9a-f]{40}")


@dataclass(frozen=True, slots=True)
class HardeningReceipt:
    """Stable pointer to one hardening gate result in the canonical EvidenceStore."""

    gate: str
    artifact_digest: str
    record_hash: str


@dataclass(frozen=True, slots=True)
class HardeningEvidence:
    capability_id: str
    recovery_verified: bool
    isolation_verified: bool
    provenance_verified: bool
    observability_verified: bool
    security_negative_tests_verified: bool
    cost_boundary_verified: bool
    stateful_persistence: bool = False
    backup_restore_verified: bool = False
    source_revision: str = ""
    receipts: tuple[HardeningReceipt, ...] = ()


def _factory_definition(capability_id: str) -> CapabilityDefinition:
    if capability_id not in PROMOTED_FACTORY_IDS:
        raise EnterpriseHardeningError(
            "capability is outside the promoted factory hardening set"
        )

    definition = capability(capability_id)
    if definition.domain != "factory" or not definition.implementation_roots:
        raise EnterpriseHardeningError("factory requires a bound implementation root")
    return definition


def _validate_source_revision(source_revision: str) -> None:
    if _SOURCE_REVISION.fullmatch(source_revision) is None:
        raise EnterpriseHardeningError(
            "hardening evidence requires an exact lowercase 40-hex source revision"
        )


def _execution_id(capability_id: str, source_revision: str, gate: str) -> str:
    return f"enterprise-hardening:{capability_id}:{source_revision}:{gate}"


def _receipt_payload(
    definition: CapabilityDefinition,
    *,
    gate: str,
    source_revision: str,
    passed: bool,
) -> dict[str, object]:
    return {
        "schema_version": _RECEIPT_SCHEMA_VERSION,
        "capability_id": definition.capability_id,
        "implementation_roots": list(definition.implementation_roots),
        "gate": gate,
        "source_revision": source_revision,
        "passed": passed,
    }


def record_hardening_receipt(
    store: EvidenceStore,
    *,
    capability_id: str,
    gate: str,
    source_revision: str,
    passed: bool,
) -> HardeningReceipt:
    """Persist one gate result in the existing content-addressed evidence chain.

    This helper creates tamper-evident repository/runtime evidence. It does not
    promote provider-specific, compliance, or other external proof to production.
    """
    definition = _factory_definition(capability_id)
    _validate_source_revision(source_revision)
    if gate not in (*HARDENING_GATES, _BACKUP_RESTORE_GATE):
        raise EnterpriseHardeningError(f"unknown enterprise hardening gate: {gate}")

    payload = _receipt_payload(
        definition,
        gate=gate,
        source_revision=source_revision,
        passed=passed,
    )
    artifact = store.put_artifact(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )
    provenance = store.append_provenance(
        _execution_id(capability_id, source_revision, gate),
        artifact,
        _RECEIPT_ACTION,
    )
    return HardeningReceipt(gate, artifact.digest, provenance.record_hash)


def verify_promoted_factory_hardening(
    evidence: HardeningEvidence,
    *,
    store: EvidenceStore | None = None,
) -> None:
    """Fail closed unless all applicable gates have source-bound immutable receipts."""
    definition = _factory_definition(evidence.capability_id)

    required = {
        "recovery": evidence.recovery_verified,
        "isolation": evidence.isolation_verified,
        "provenance": evidence.provenance_verified,
        "observability": evidence.observability_verified,
        "security_negative_tests": evidence.security_negative_tests_verified,
        "cost_boundary": evidence.cost_boundary_verified,
    }
    missing = sorted(name for name, passed in required.items() if not passed)
    if missing:
        raise EnterpriseHardeningError(f"missing hardening gates: {missing}")

    if evidence.stateful_persistence and not evidence.backup_restore_verified:
        raise EnterpriseHardeningError(
            "stateful persistence requires backup/restore evidence"
        )

    _validate_source_revision(evidence.source_revision)
    if store is None:
        raise EnterpriseHardeningError(
            "hardening verification requires the canonical evidence store"
        )

    expected_gates = set(HARDENING_GATES)
    if evidence.stateful_persistence:
        expected_gates.add(_BACKUP_RESTORE_GATE)

    receipts_by_gate: dict[str, HardeningReceipt] = {}
    for receipt in evidence.receipts:
        if receipt.gate in receipts_by_gate:
            raise EnterpriseHardeningError(
                f"duplicate enterprise hardening receipt: {receipt.gate}"
            )
        receipts_by_gate[receipt.gate] = receipt

    missing_receipts = sorted(expected_gates - receipts_by_gate.keys())
    unexpected_receipts = sorted(receipts_by_gate.keys() - expected_gates)
    if missing_receipts:
        raise EnterpriseHardeningError(
            f"missing immutable hardening receipts: {missing_receipts}"
        )
    if unexpected_receipts:
        raise EnterpriseHardeningError(
            f"unexpected immutable hardening receipts: {unexpected_receipts}"
        )

    try:
        records = store.verify()
    except EvidenceError as exc:
        raise EnterpriseHardeningError(
            "canonical hardening evidence integrity verification failed"
        ) from exc
    records_by_hash = {record.record_hash: record for record in records}

    for gate in sorted(expected_gates):
        receipt = receipts_by_gate[gate]
        record = records_by_hash.get(receipt.record_hash)
        if record is None:
            raise EnterpriseHardeningError(
                f"hardening receipt is outside the canonical evidence chain: {gate}"
            )
        if (
            record.artifact_digest != receipt.artifact_digest
            or record.action != _RECEIPT_ACTION
            or record.execution_id
            != _execution_id(evidence.capability_id, evidence.source_revision, gate)
        ):
            raise EnterpriseHardeningError(
                f"hardening receipt provenance binding mismatch: {gate}"
            )

        try:
            payload = json.loads(
                store.get_artifact(receipt.artifact_digest).decode("utf-8")
            )
        except (EvidenceError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise EnterpriseHardeningError(
                f"hardening receipt artifact is invalid: {gate}"
            ) from exc

        expected_payload = _receipt_payload(
            definition,
            gate=gate,
            source_revision=evidence.source_revision,
            passed=True,
        )
        if payload != expected_payload:
            raise EnterpriseHardeningError(
                f"hardening receipt content binding mismatch: {gate}"
            )
