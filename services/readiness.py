"""Verification of measured operational-drill artifacts."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import cast

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
    artifact_path: str
    evidence_hash: str
    completed_drills: tuple[str, ...]
    eligible: bool
    release_state: ReleaseState


def evaluate_drill_artifact(artifact_path: Path) -> PromotionEligibility:
    """Validate a measured artifact; caller-supplied result maps are not accepted."""
    content = artifact_path.read_bytes()
    raw: object = json.loads(content)
    if not isinstance(raw, dict):
        raise TypeError("operational drill artifact must be an object")
    artifact = cast(dict[str, object], raw)
    if artifact.get("artifact_version") != "ILAIOS_OPERATIONAL_DRILLS_V1":
        raise ValueError("operational drill artifact version is invalid")
    if artifact.get("release_state") != ReleaseState.NOT_DEPLOYED.value:
        raise ValueError("operational drills cannot promote release state")
    raw_drills = artifact.get("drills")
    if not isinstance(raw_drills, dict) or not all(
        isinstance(name, str) for name in raw_drills
    ):
        raise ValueError("operational drill records are invalid")
    drills = cast(dict[str, object], raw_drills)
    if set(drills) != REQUIRED_DRILLS:
        missing = REQUIRED_DRILLS - drills.keys()
        unexpected = drills.keys() - REQUIRED_DRILLS
        detail = ",".join(sorted(missing | unexpected))
        raise ValueError(f"operational drill set is invalid: {detail}")
    for name, raw_record in drills.items():
        if not isinstance(raw_record, dict):
            raise TypeError(f"operational drill record is invalid: {name}")
        record = cast(dict[str, object], raw_record)
        measurements = record.get("measurements")
        if record.get("passed") is not True or not isinstance(measurements, dict):
            raise ValueError(f"operational drill did not pass: {name}")
        if not measurements:
            raise ValueError(f"operational drill has no measurements: {name}")
    return PromotionEligibility(
        str(artifact_path),
        hashlib.sha256(content).hexdigest(),
        tuple(sorted(REQUIRED_DRILLS)),
        True,
        ReleaseState.NOT_DEPLOYED,
    )
