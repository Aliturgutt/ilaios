"""Actual operational recovery drill tests for PLATFORM.P20."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from packages.contracts.ilaios_contracts import ReleaseState
from services.control_plane.migrations import LATEST_SCHEMA_VERSION
from services.operational_drills import execute_operational_drills
from services.readiness import REQUIRED_DRILLS, evaluate_drill_artifact


def test_actual_runtime_drills_create_file_backed_eligibility(tmp_path: Path) -> None:
    repository = Path(__file__).resolve().parents[1]
    eligibility = execute_operational_drills(repository, tmp_path / "drills")
    assert eligibility.eligible is True
    assert eligibility.release_state is ReleaseState.NOT_DEPLOYED
    assert set(eligibility.completed_drills) == REQUIRED_DRILLS
    assert len(eligibility.evidence_hash) == 64

    artifact_path = Path(eligibility.artifact_path)
    artifact = json.loads(artifact_path.read_text())
    drills = artifact["drills"]
    assert drills["security-red-team"]["measurements"]["blocked_count"] == 4
    assert drills["load"]["measurements"]["success_count"] == 80
    assert drills["chaos-outage"]["measurements"]["crash_observed"] is True
    assert drills["dr-restore"]["measurements"]["restored_goal_equal"] is True
    assert drills["compromise-revocation"]["measurements"][
        "denied_after_revoke_status"
    ] == 400
    assert drills["supply-chain"]["measurements"]["tamper_detected"] is True
    assert (
        drills["rollback"]["measurements"]["schema_reapplied"]
        == LATEST_SCHEMA_VERSION
    )


def test_artifact_tampering_blocks_eligibility(tmp_path: Path) -> None:
    artifact: dict[str, Any] = {
        "artifact_version": "ILAIOS_OPERATIONAL_DRILLS_V1",
        "drills": {
            name: {"passed": True, "measurements": {"measured": 1}}
            for name in REQUIRED_DRILLS
        },
        "release_state": "NOT_DEPLOYED",
    }
    artifact["drills"]["rollback"]["passed"] = False
    path = tmp_path / "tampered.json"
    path.write_text(json.dumps(artifact))
    with pytest.raises(ValueError, match="rollback"):
        evaluate_drill_artifact(path)
