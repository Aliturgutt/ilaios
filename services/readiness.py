"""Evidence-backed promotion-readiness drill evaluation."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from packages.contracts.ilaios_contracts import ReleaseState

REQUIRED_DRILLS = frozenset(
    {
        "security-red-team",
        "chaos-outage",
        "dr-restore",
        "load",
        "compromise-revocation",
        "supply-chain",
        "rollback",
    }
)


@dataclass(frozen=True, slots=True)
class PromotionEligibility:
    evidence_hash: str
    completed_drills: tuple[str, ...]
    eligible: bool
    release_state: ReleaseState


def evaluate_drills(results: dict[str, bool]) -> PromotionEligibility:
    missing = REQUIRED_DRILLS - results.keys()
    failed = {name for name in REQUIRED_DRILLS if not results.get(name, False)}
    if missing or failed:
        detail = ",".join(sorted(missing | failed))
        raise ValueError(f"promotion drills incomplete or failed: {detail}")
    completed = tuple(sorted(REQUIRED_DRILLS))
    payload = json.dumps({name: results[name] for name in completed}, sort_keys=True).encode()
    return PromotionEligibility(
        hashlib.sha256(payload).hexdigest(), completed, True, ReleaseState.NOT_DEPLOYED
    )
