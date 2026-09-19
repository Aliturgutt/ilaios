"""Deterministic digest verification for canonical Agent final-closure receipts.

This helper validates only receipt integrity. It does not create evidence, mutate
readiness, or replace canonical Audit/Evidence, governance, runtime, or tenant
authorities.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_DIGEST_FIELD = "closure_evidence_sha256"


class AgentFinalClosureDigestError(ValueError):
    """Final closure receipt material cannot be deterministically verified."""


def canonical_agent_final_closure_bytes(receipt: Mapping[str, object]) -> bytes:
    """Serialize closure material deterministically, excluding its digest field."""

    material = {str(key): value for key, value in receipt.items() if str(key) != _DIGEST_FIELD}
    if len(material) != len(receipt) - (1 if _DIGEST_FIELD in receipt else 0):
        raise AgentFinalClosureDigestError("final closure receipt contains duplicate normalized keys")
    try:
        serialized = json.dumps(
            material,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        )
    except (TypeError, ValueError) as exc:
        raise AgentFinalClosureDigestError(
            "final closure receipt material must be canonical JSON"
        ) from exc
    return serialized.encode("utf-8")


def compute_agent_final_closure_sha256(receipt: Mapping[str, object]) -> str:
    """Return SHA-256 for deterministic closure material."""

    return hashlib.sha256(canonical_agent_final_closure_bytes(receipt)).hexdigest()


def verify_agent_final_closure_sha256(receipt: Mapping[str, object]) -> None:
    """Fail closed unless the supplied digest binds the exact closure material."""

    supplied = receipt.get(_DIGEST_FIELD)
    if not isinstance(supplied, str) or _SHA256.fullmatch(supplied) is None:
        raise AgentFinalClosureDigestError("closure_evidence_sha256 must be lowercase SHA-256")
    expected = compute_agent_final_closure_sha256(receipt)
    if supplied != expected:
        raise AgentFinalClosureDigestError(
            "closure_evidence_sha256 does not bind the exact canonical closure material"
        )
